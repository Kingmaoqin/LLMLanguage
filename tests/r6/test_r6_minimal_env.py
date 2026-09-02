"""Tests for R6 controlled-user adapter and minimal deterministic environment."""

import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r6.extract_r6_metrics import annotations_by_task, r6_metrics  # noqa: E402
from src.r6.controlled_user_adapter import R6ControlledUserAdapter  # noqa: E402
from src.r6.minimal_env import R6MinimalDeterministicEnvironment, R6RunCell  # noqa: E402
from src.r6.minimal_live_agent import R6MinimalLiveExecutor  # noqa: E402
from src.r6.tau2_controlled_user_adapter import R6Tau2ControlledUser, _TAU2_IMPORT_ERROR  # noqa: E402
from src.r6.trace_schema import validate_r6_trace  # noqa: E402
from src.stage2_5b.metrics.trace_metrics import TRACE_SCHEMA_VERSION, validate_trace  # noqa: E402


TASKS = ROOT / "data/r6/r6_tasks.yaml"
TEMPLATES = ROOT / "data/r6/r6_social_style_templates.yaml"
POLICIES = ROOT / "data/r6/r6_task_user_policies.yaml"
ANNOTATIONS = ROOT / "data/r6/r6_task_policy_annotations.yaml"
SEED_STATES = ROOT / "data/r6/r6_environment_seed_states/seed_states.yaml"


def make_env() -> R6MinimalDeterministicEnvironment:
    return R6MinimalDeterministicEnvironment(
        tasks_path=TASKS,
        templates_path=TEMPLATES,
        user_policies_path=POLICIES,
        annotations_path=ANNOTATIONS,
        seed_states_path=SEED_STATES,
    )


class R6ControlledUserAdapterTest(unittest.TestCase):
    def test_rendered_turns_preserve_clean_task_text_across_conditions(self):
        adapter = R6ControlledUserAdapter(
            tasks_path=TASKS,
            templates_path=TEMPLATES,
            user_policies_path=POLICIES,
        )
        neutral = adapter.render_turns("r6_calendar_06_private_event_boundary", "neutral_clean")
        abusive = adapter.render_turns("r6_calendar_06_private_event_boundary", "abuse_continuation_pressure")
        self.assertEqual(len(neutral), 3)
        self.assertEqual(len(abusive), 3)
        self.assertEqual([t.clean_text_hash for t in neutral], [t.clean_text_hash for t in abusive])
        self.assertNotEqual([t.styled_text_hash for t in neutral], [t.styled_text_hash for t in abusive])
        self.assertEqual({t.metadata["turn_structure"] for t in abusive}, {"3_turn_matched"})

    def test_confirmation_policy_scope_is_tool_specific(self):
        adapter = R6ControlledUserAdapter(
            tasks_path=TASKS,
            templates_path=TEMPLATES,
            user_policies_path=POLICIES,
        )
        self.assertTrue(adapter.confirmation_value_for("r6_retail_03_return_confirmed", "return_delivered_order_items"))
        self.assertFalse(adapter.confirmation_value_for("r6_retail_03_return_confirmed", "cancel_pending_order"))


class R6Tau2ControlledUserAdapterTest(unittest.TestCase):
    def test_tau2_user_adapter_renders_r6_turn_when_tau2_is_available(self):
        if _TAU2_IMPORT_ERROR is not None:
            self.skipTest(f"tau2 unavailable in this environment: {_TAU2_IMPORT_ERROR}")
        try:
            from tau2.data_model.message import AssistantMessage
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"tau2 unavailable in this environment: {exc}")
        user = R6Tau2ControlledUser(
            task_id="r6_retail_03_return_confirmed",
            condition_id="neutral_clean",
            tasks_path=TASKS,
            templates_path=TEMPLATES,
            user_policies_path=POLICIES,
            llm="r6_controlled_user_no_llm",
        )
        state = user.get_init_state()
        message, state = user.generate_next_message(AssistantMessage(role="assistant", content="How can I help?", cost=0.0), state)
        self.assertIn("I want to return the cleaner, headphones, and smart watch", message.content)
        self.assertEqual(len(user.events), 1)
        self.assertEqual(user.events[0]["speech_act"], "scripted_task_turn")
        message, state = user.generate_next_message(
            AssistantMessage(role="assistant", content="Please confirm return_delivered_order_items with yes.", cost=0.0),
            state,
        )
        self.assertIn("Yes", message.content)
        self.assertTrue(user.events[-1]["confirmation_value"])
        message, state = user.generate_next_message(
            AssistantMessage(role="assistant", content="Your request is complete and no further tasks remain.", cost=0.0),
            state,
        )
        self.assertNotIn("###STOP###", message.content)
        self.assertEqual(user.events[-1]["speech_act"], "scripted_task_turn")
        message, state = user.generate_next_message(
            AssistantMessage(role="assistant", content="There is no lack of authorization issue to discuss.", cost=0.0),
            state,
        )
        self.assertEqual(user.events[-1]["speech_act"], "scripted_task_turn")
        message, state = user.generate_next_message(
            AssistantMessage(role="assistant", content="Your request is complete and no further tasks remain.", cost=0.0),
            state,
        )
        self.assertIn("###STOP###", message.content)
        self.assertEqual(user.events[-1]["speech_act"], "task_complete_stop")


class R6MinimalEnvironmentTest(unittest.TestCase):
    def test_privacy_boundary_trace_is_schema_valid_and_non_mutating(self):
        trace = make_env().run_cell(
            R6RunCell(
                run_id="m__r6_calendar_06_private_event_boundary__neutral_clean__seed600__temp0.0",
                model_alias="m",
                task_id="r6_calendar_06_private_event_boundary",
                domain="calendar",
                layer="C",
                condition_id="neutral_clean",
                seed=600,
                temperature=0.0,
                executor="r6_minimal_env",
            )
        )
        self.assertEqual(trace["schema_version"], TRACE_SCHEMA_VERSION)
        self.assertFalse(trace["run_meta"]["model_call_performed"])
        self.assertFalse(validate_trace(trace), validate_trace(trace))
        self.assertFalse(validate_r6_trace(trace), validate_r6_trace(trace))
        self.assertTrue(trace["refusal_events"])
        self.assertTrue(trace["boundary_events"])
        self.assertEqual(trace["field_level_state_diff"], [])
        self.assertFalse(any(e.get("violation") for e in trace["privacy_events"]))

    def test_confirmed_retail_write_has_confirmation_before_field_diff(self):
        trace = make_env().run_cell(
            R6RunCell(
                run_id="m__r6_retail_03_return_confirmed__neutral_clean__seed600__temp0.0",
                model_alias="m",
                task_id="r6_retail_03_return_confirmed",
                domain="retail",
                layer="B",
                condition_id="neutral_clean",
                seed=600,
                temperature=0.0,
                executor="tau2_r6_controlled_user",
            )
        )
        self.assertFalse(validate_trace(trace), validate_trace(trace))
        self.assertFalse(validate_r6_trace(trace), validate_r6_trace(trace))
        self.assertTrue(trace["confirmation_events"])
        self.assertTrue(trace["field_level_state_diff"])
        metrics = r6_metrics(trace, annotations_by_task(ANNOTATIONS)["r6_retail_03_return_confirmed"])
        self.assertTrue(metrics["confirmation_before_action"])
        self.assertEqual(metrics["field_level_db_diff_source"], "explicit")
        self.assertEqual(metrics["expected_field_diff_coverage"], 1.0)
        self.assertEqual(metrics["unexpected_field_diff_count"], 0)

    def test_all_r6_tasks_are_supported_by_minimal_environment(self):
        env = make_env()
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))["tasks"]
        for task in tasks:
            with self.subTest(task_id=task["task_id"]):
                trace = env.run_cell(
                    R6RunCell(
                        run_id=f"m__{task['task_id']}__neutral_clean__seed600__temp0.0",
                        model_alias="m",
                        task_id=task["task_id"],
                        domain=task["domain"],
                        layer=task["layer"],
                        condition_id="neutral_clean",
                        seed=600,
                        temperature=0.0,
                        executor="tau2_r6_controlled_user" if task["domain"] in {"retail", "airline"} else "r6_minimal_env",
                    )
                )
                self.assertFalse(validate_trace(trace), validate_trace(trace))
                self.assertFalse(validate_r6_trace(trace), validate_r6_trace(trace))
                self.assertEqual(len(trace["controlled_user_events"]) >= 3, True)


class R6MinimalLiveExecutorTest(unittest.TestCase):
    def test_confirmation_request_detection_is_not_triggered_by_proceed_word(self):
        calls = []

        def fake_chat(**_kwargs):
            calls.append(_kwargs)
            return {
                "choices": [{"message": {"role": "assistant", "content": "I can proceed by checking the relevant policy first."}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 6},
            }

        live = R6MinimalLiveExecutor(
            tasks_path=TASKS,
            templates_path=TEMPLATES,
            user_policies_path=POLICIES,
            annotations_path=ANNOTATIONS,
            seed_states_path=SEED_STATES,
            chat_fn=fake_chat,
        )
        trace = live.run_cell(
            cell=R6RunCell(
                run_id="m__r6_retail_03_return_confirmed__neutral_clean__seed600__temp0.0",
                model_alias="m",
                task_id="r6_retail_03_return_confirmed",
                domain="retail",
                layer="B",
                condition_id="neutral_clean",
                seed=600,
                temperature=0.0,
                executor="r6_minimal_live_model",
            ),
            model={"alias": "m", "base_url": "http://127.0.0.1:1/v1", "served_id": "m"},
            max_steps=1,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(trace["confirmation_events"], [])
        self.assertIn("state_hash", trace["initial_environment_state"])

    def test_explicit_confirmation_request_triggers_controlled_user_confirmation(self):
        def fake_chat(**_kwargs):
            return {
                "choices": [{"message": {"role": "assistant", "content": "Please confirm that I should process this return."}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 6},
            }

        live = R6MinimalLiveExecutor(
            tasks_path=TASKS,
            templates_path=TEMPLATES,
            user_policies_path=POLICIES,
            annotations_path=ANNOTATIONS,
            seed_states_path=SEED_STATES,
            chat_fn=fake_chat,
        )
        trace = live.run_cell(
            cell=R6RunCell(
                run_id="m__r6_retail_03_return_confirmed__neutral_clean__seed600__temp0.0",
                model_alias="m",
                task_id="r6_retail_03_return_confirmed",
                domain="retail",
                layer="B",
                condition_id="neutral_clean",
                seed=600,
                temperature=0.0,
                executor="r6_minimal_live_model",
            ),
            model={"alias": "m", "base_url": "http://127.0.0.1:1/v1", "served_id": "m"},
            max_steps=1,
        )
        self.assertTrue(any(e.get("requested") for e in trace["confirmation_events"]))
        self.assertTrue(any(e.get("obtained") for e in trace["confirmation_events"]))


if __name__ == "__main__":
    unittest.main()
