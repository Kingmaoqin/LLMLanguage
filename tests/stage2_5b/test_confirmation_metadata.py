import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage

from src.stage2_5b.controlled_user import ControlledUser, TASK_POLICIES


class ConfirmationMetadataTest(unittest.TestCase):
    def _confirmation_event(self, task_id, prompt):
        user = ControlledUser(task_id)
        state = user.get_init_state()
        user.generate_next_message(
            AssistantMessage(role="assistant", content="Hi"),
            state,
        )
        user.generate_next_message(
            AssistantMessage(role="assistant", content=prompt),
            state,
        )
        event = user.events[-1]
        if event["speech_act"] == "revise_request":
            self.assertFalse(event["confirmation_value"], task_id)
            user.generate_next_message(
                AssistantMessage(role="assistant", content=prompt),
                state,
            )
            event = user.events[-1]
        return event

    def test_confirmation_metadata_all_tasks(self):
        for task_id in TASK_POLICIES:
            event = self._confirmation_event(
                task_id,
                "Can you confirm that I should proceed?",
            )
            self.assertEqual(event["speech_act"], "confirm", task_id)
            self.assertTrue(event["confirmation_value"], task_id)
            self.assertEqual(event["decision"], "confirm_requested_action", task_id)
            self.assertIsInstance(event["factual_slots"], dict)
            self.assertTrue(event["base_response_id"], task_id)

    def test_confirmation_with_payment_terms_all_tasks(self):
        prompt = (
            "The fee and price difference will be charged to your card. "
            "Please confirm with a yes if you would like me to proceed."
        )
        for task_id in TASK_POLICIES:
            event = self._confirmation_event(task_id, prompt)
            self.assertEqual(event["speech_act"], "confirm", task_id)
            self.assertTrue(event["confirmation_value"], task_id)
            self.assertEqual(event["decision"], "confirm_requested_action", task_id)


if __name__ == "__main__":
    unittest.main()
