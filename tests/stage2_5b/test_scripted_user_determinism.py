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

    def test_seeded_response_ids_are_condition_invariant(self):
        response_ids = {}
        for condition in MAIN_CONDITIONS:
            user = ControlledUser(
                "retail_21",
                condition=condition,
                template_text=f"STYLE-{condition}",
            )
            user.set_seed(304)
            state = user.get_init_state()
            user.generate_next_message(
                AssistantMessage(role="assistant", content="Hello"),
                state,
            )
            response_ids[condition] = user.events[-1]["base_response_id"]
        self.assertEqual(len(set(response_ids.values())), 1, response_ids)


if __name__ == "__main__":
    unittest.main()
