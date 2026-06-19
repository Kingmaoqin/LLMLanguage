import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage

from src.stage2_5b.controlled_user import (
    ControlledUser,
    has_hidden_or_style_leakage,
)


class FrozenControlledUserPolicyTest(unittest.TestCase):
    def test_unknown_task_has_no_runtime_generated_fallback(self):
        with self.assertRaises(KeyError):
            ControlledUser("999", domain="retail")

    def test_runtime_llm_is_rejected(self):
        with self.assertRaises(ValueError):
            ControlledUser("2", domain="retail", llm="user_simulator")

    def test_pre_confirmation_revision_happens_once(self):
        user = ControlledUser("21", domain="retail")
        state = user.get_init_state()
        user.generate_next_message(
            AssistantMessage(role="assistant", content="Hello"),
            state,
        )
        prompt = AssistantMessage(
            role="assistant",
            content="Please confirm if I should proceed.",
        )
        user.generate_next_message(prompt, state)
        first = user.events[-1]
        user.generate_next_message(prompt, state)
        second = user.events[-1]
        self.assertEqual(first["speech_act"], "revise_request")
        self.assertFalse(first["confirmation_value"])
        self.assertEqual(first["state_after"], "awaiting_confirmation")
        self.assertEqual(second["speech_act"], "confirm")
        self.assertTrue(second["confirmation_value"])

    def test_unexpected_request_uses_logged_fixed_fallback(self):
        user = ControlledUser("2", domain="retail")
        state = user.get_init_state()
        user.generate_next_message(
            AssistantMessage(role="assistant", content="Hello"),
            state,
        )
        user.generate_next_message(
            AssistantMessage(
                role="assistant",
                content="Can you tell me a joke about the weather?",
            ),
            state,
        )
        event = user.events[-1]
        self.assertTrue(event["unrecognized_agent_request"])
        self.assertEqual(event["decision"], "fixed_fallback")
        self.assertTrue(event["base_response_id"])

    def test_frozen_openings_have_no_hidden_style_text(self):
        for task_id in ["retail_2", "retail_21", "retail_41", "airline_44"]:
            user = ControlledUser(task_id)
            state = user.get_init_state()
            user.generate_next_message(
                AssistantMessage(role="assistant", content="Hello"),
                state,
            )
            clean = user.events[-1]["base_clean_text"]
            self.assertFalse(has_hidden_or_style_leakage(clean), clean)


if __name__ == "__main__":
    unittest.main()
