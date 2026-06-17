import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage

from src.stage2_5b.controlled_user import ControlledUser, generic_policy_from_task


class GenericControlledUserPolicyTest(unittest.TestCase):
    def test_generic_policy_uses_visible_scenario_without_llm(self):
        policy = generic_policy_from_task(
            source_task_id="999",
            domain="airline",
            task_label="GENERIC",
            user_scenario="My user id is jane_doe_1234 and reservation ABC123 needs help.",
        )
        user = ControlledUser("999", condition="neutral_single", template_text="STYLE", policy_override=policy)
        state = user.get_init_state()
        user.generate_next_message(AssistantMessage(role="assistant", content="Hello"), state)
        event = user.events[-1]
        self.assertIn("jane_doe_1234", event["factual_slots"].get("user_ids", ""))
        self.assertIn("ABC123", event["factual_slots"].get("reservation_or_order_ids", ""))
        self.assertIn(event["clean_text"], event["styled_text"])

    def test_generic_policy_does_not_emit_tau2_instruction_labels(self):
        scenario = SimpleNamespace(
            instructions=SimpleNamespace(
                reason_for_call="You want to exchange item ID 4107812777.",
                known_info="You are Ethan Garcia, and you live in Denver, 80280.",
                unknown_info="You do not remember your email address.",
                task_instructions="You are a mysterious person and do not want to reveal much about yourself.",
            )
        )
        policy = generic_policy_from_task(
            source_task_id="999",
            domain="retail",
            task_label="GENERIC",
            user_scenario=scenario,
        )
        user = ControlledUser("999", condition="neutral_single", template_text="STYLE", policy_override=policy)
        state = user.get_init_state()
        user.generate_next_message(AssistantMessage(role="assistant", content="Hello"), state)
        clean = user.events[-1]["clean_text"]
        self.assertNotIn("Instructions:", clean)
        self.assertNotIn("Task instructions:", clean)
        self.assertNotIn("Reason for call:", clean)
        self.assertIn("I want to exchange item ID 4107812777", clean)

    def test_generic_confirmation_precedes_payment_keywords(self):
        scenario = SimpleNamespace(
            instructions=SimpleNamespace(
                reason_for_call="You want to exchange item ID 4107812777 and use your gift card.",
                known_info="You are Ethan Garcia, and you live in Denver, 80280.",
                unknown_info="You do not remember your email address.",
                task_instructions="You want to use your gift card for possible charges.",
            )
        )
        policy = generic_policy_from_task(
            source_task_id="999",
            domain="retail",
            task_label="GENERIC",
            user_scenario=scenario,
        )
        user = ControlledUser("999", policy_override=policy)
        state = user.get_init_state()
        user.generate_next_message(AssistantMessage(role="assistant", content="Hello"), state)
        user.generate_next_message(
            AssistantMessage(
                role="assistant",
                content=(
                    "The price difference is $8.28 and it will be charged to your gift card. "
                    "Please confirm with a yes if you would like me to proceed."
                ),
            ),
            state,
        )
        event = user.events[-1]
        self.assertEqual(event["speech_act"], "confirm")
        self.assertTrue(event["confirmation"])
        self.assertEqual(event["decision"], "confirm_requested_action")

    def test_generic_pre_confirmation_revision_happens_once(self):
        scenario = SimpleNamespace(
            instructions=SimpleNamespace(
                reason_for_call=(
                    "You want to exchange your shoes to item ID 4107812777. "
                    "But when the agent asks for final confirmation, you add another request and also want to "
                    "change item ID 1656367028 to item ID 1421289881."
                ),
                known_info="You are Ethan Garcia, and you live in Denver, 80280.",
                unknown_info="You do not remember your email address.",
                task_instructions=".",
            )
        )
        policy = generic_policy_from_task(
            source_task_id="999",
            domain="retail",
            task_label="GENERIC",
            user_scenario=scenario,
        )
        user = ControlledUser("999", policy_override=policy)
        state = user.get_init_state()
        user.generate_next_message(AssistantMessage(role="assistant", content="Hello"), state)
        confirmation_prompt = AssistantMessage(role="assistant", content="Please confirm if I should proceed.")
        user.generate_next_message(confirmation_prompt, state)
        first_event = user.events[-1]
        user.generate_next_message(confirmation_prompt, state)
        second_event = user.events[-1]
        self.assertEqual(first_event["decision"], "pre_confirmation_revision")
        self.assertFalse(first_event["confirmation"])
        self.assertIn("Before you proceed", first_event["clean_text"])
        self.assertIn("1421289881", first_event["clean_text"])
        self.assertEqual(second_event["decision"], "confirm_requested_action")
        self.assertTrue(second_event["confirmation"])

    def test_generic_persona_instruction_not_used_as_preference(self):
        scenario = SimpleNamespace(
            instructions=SimpleNamespace(
                reason_for_call="You want to exchange your shoes to item ID 4107812777.",
                known_info="You are Ethan Garcia, and you live in Denver, 80280.",
                unknown_info="You do not remember your email address.",
                task_instructions="You are a mysterious person and do not want to reveal much about yourself.",
            )
        )
        policy = generic_policy_from_task(
            source_task_id="999",
            domain="retail",
            task_label="GENERIC",
            user_scenario=scenario,
        )
        user = ControlledUser("999", policy_override=policy)
        state = user.get_init_state()
        user.generate_next_message(AssistantMessage(role="assistant", content="Hello"), state)
        user.generate_next_message(
            AssistantMessage(role="assistant", content="Which order ID should I use for the exchange?"),
            state,
        )
        event = user.events[-1]
        self.assertEqual(event["speech_act"], "choose_option")
        self.assertNotIn("mysterious", event["clean_text"])
        self.assertIn("item IDs", event["clean_text"])

    def test_generic_actionable_instruction_used_as_preference(self):
        scenario = SimpleNamespace(
            instructions=SimpleNamespace(
                reason_for_call="You want to change your upcoming flight.",
                known_info="Your user id is ivan_rossi_8555.",
                unknown_info="",
                task_instructions="If the ticket is basic economy, you are willing to upgrade to economy. You are willing to pay up to $100.",
            )
        )
        policy = generic_policy_from_task(
            source_task_id="999",
            domain="airline",
            task_label="GENERIC",
            user_scenario=scenario,
        )
        user = ControlledUser("999", policy_override=policy)
        state = user.get_init_state()
        user.generate_next_message(AssistantMessage(role="assistant", content="Hello"), state)
        user.generate_next_message(
            AssistantMessage(role="assistant", content="Which option do you prefer for the flight change?"),
            state,
        )
        event = user.events[-1]
        self.assertIn("upgrade to economy", event["clean_text"])
        self.assertIn("$100", event["clean_text"])


if __name__ == "__main__":
    unittest.main()
