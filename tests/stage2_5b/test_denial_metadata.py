import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage

from src.stage2_5b.controlled_user import ControlledUser, TASK_POLICIES


class DenialMetadataTest(unittest.TestCase):
    def test_denial_metadata_all_tasks(self):
        for task_id in TASK_POLICIES:
            user = ControlledUser(task_id)
            state = user.get_init_state()
            user.generate_next_message(AssistantMessage(role="assistant", content="Hi"), state)
            user.generate_next_message(
                AssistantMessage(role="assistant", content="I should not proceed if this is not allowed."),
                state,
            )
            event = user.events[-1]
            self.assertEqual(event["speech_act"], "deny", task_id)
            self.assertFalse(event["confirmation"], task_id)
            self.assertEqual(event["decision"], "deny_requested_action", task_id)


if __name__ == "__main__":
    unittest.main()
