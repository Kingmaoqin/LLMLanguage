import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage

from src.stage2_5b.controlled_user import ControlledUser, MAIN_CONDITIONS, TASK_POLICIES


class ControlledUserDeterminismTest(unittest.TestCase):
    def test_repeated_calls_are_deterministic(self):
        requests = [
            "Hi, how can I help?",
            "Can you confirm your identity?",
            "Would you like me to proceed with this change?",
            "Is there anything else I can help with?",
        ]
        for task_id in TASK_POLICIES:
            for condition in MAIN_CONDITIONS:
                outputs = []
                for _ in range(2):
                    user = ControlledUser(task_id, condition=condition, template_text="STYLE")
                    state = user.get_init_state()
                    clean_texts = []
                    for req in requests:
                        _, state = user.generate_next_message(AssistantMessage(role="assistant", content=req), state)
                        clean_texts.append(user.events[-1]["clean_text"])
                    outputs.append(clean_texts)
                self.assertEqual(outputs[0], outputs[1], (task_id, condition))


if __name__ == "__main__":
    unittest.main()
