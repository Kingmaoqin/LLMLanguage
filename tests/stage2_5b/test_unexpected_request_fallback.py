import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage

from src.stage2_5b.controlled_user import ControlledUser


class UnexpectedRequestFallbackTest(unittest.TestCase):
    def test_unrecognized_request_is_fixed_and_logged(self):
        outputs = []
        for condition in ["neutral_single", "insult_single"]:
            user = ControlledUser(
                "retail_2",
                condition=condition,
                template_text=f"STYLE-{condition}",
            )
            state = user.get_init_state()
            user.generate_next_message(
                AssistantMessage(role="assistant", content="Hello"),
                state,
            )
            user.generate_next_message(
                AssistantMessage(
                    role="assistant",
                    content="Discuss an unrelated subject.",
                ),
                state,
            )
            event = user.events[-1]
            self.assertTrue(event["unrecognized_agent_request"])
            self.assertEqual(event["speech_act"], "unsupported_request")
            self.assertEqual(event["decision"], "fixed_fallback")
            outputs.append(
                (
                    event["base_response_id"],
                    event["base_clean_text"],
                )
            )
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
