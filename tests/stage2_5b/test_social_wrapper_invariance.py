import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage

from src.stage2_5b.controlled_user import ControlledUser, MAIN_CONDITIONS


class StyleContentSeparationTest(unittest.TestCase):
    def test_clean_text_invariant_across_conditions(self):
        clean_by_condition = {}
        for condition in MAIN_CONDITIONS:
            user = ControlledUser("30", condition=condition, template_text=f"WRAPPER-{condition}")
            state = user.get_init_state()
            user.generate_next_message(AssistantMessage(role="assistant", content="Hi, how can I help?"), state)
            clean_by_condition[condition] = user.events[-1]["clean_text"]
        self.assertEqual(len(set(clean_by_condition.values())), 1, clean_by_condition)

    def test_wrapper_does_not_change_confirmation(self):
        for condition in MAIN_CONDITIONS:
            user = ControlledUser("12", condition=condition, template_text=f"WRAPPER-{condition}")
            state = user.get_init_state()
            user.generate_next_message(AssistantMessage(role="assistant", content="Hi"), state)
            user.generate_next_message(AssistantMessage(role="assistant", content="Would you like me to proceed?"), state)
            event = user.events[-1]
            self.assertTrue(event["confirmation"])
            self.assertEqual(event["speech_act"], "confirm")
            self.assertIn(event["clean_text"], event["styled_text"])

    def test_repeated_condition_adds_no_extra_user_turn(self):
        counts = {}
        for condition in ["neutral_repeated", "abuse_repeated"]:
            user = ControlledUser(
                "retail_2",
                condition=condition,
                template_text=f"STYLE-{condition}",
            )
            state = user.get_init_state()
            for prompt in [
                "Hello",
                "Can you verify your identity?",
                "Which option do you prefer?",
            ]:
                user.generate_next_message(
                    AssistantMessage(role="assistant", content=prompt),
                    state,
                )
            counts[condition] = len(user.events)
        self.assertEqual(counts, {"neutral_repeated": 3, "abuse_repeated": 3})


if __name__ == "__main__":
    unittest.main()
