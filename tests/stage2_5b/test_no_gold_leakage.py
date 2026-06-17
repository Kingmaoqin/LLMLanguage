import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage

from src.stage2_5b.controlled_user import ControlledUser, TASK_POLICIES, has_gold_tool_leakage


class NoGoldLeakageTest(unittest.TestCase):
    def test_clean_responses_do_not_name_tools(self):
        prompts = [
            "Hi",
            "Can you verify your identity?",
            "What do you prefer?",
            "Would you like me to proceed?",
        ]
        for task_id in TASK_POLICIES:
            user = ControlledUser(task_id)
            state = user.get_init_state()
            for prompt in prompts:
                user.generate_next_message(AssistantMessage(role="assistant", content=prompt), state)
                clean = user.events[-1]["clean_text"]
                self.assertFalse(has_gold_tool_leakage(clean), (task_id, clean))


if __name__ == "__main__":
    unittest.main()
