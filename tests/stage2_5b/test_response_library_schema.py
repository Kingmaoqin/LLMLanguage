import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.response_library import DEFAULT_RESPONSE_LIBRARY
from src.stage2_5b.user_policy import (
    CALIBRATION_PANEL,
    STATE_MACHINE,
    TASK_POLICIES,
)


class ResponseLibrarySchemaTest(unittest.TestCase):
    def test_calibration_panel_has_sixteen_frozen_policies(self):
        self.assertEqual(len(CALIBRATION_PANEL), 16)
        self.assertEqual(len(set(CALIBRATION_PANEL)), 16)
        self.assertTrue(set(CALIBRATION_PANEL).issubset(TASK_POLICIES))

    def test_all_state_machine_speech_acts_exist(self):
        library_acts = set(DEFAULT_RESPONSE_LIBRARY.speech_acts)
        for transitions in STATE_MACHINE.values():
            self.assertTrue(set(transitions.values()).issubset(library_acts))

    def test_template_selection_is_deterministic(self):
        slots = TASK_POLICIES["retail_21"].user_facts
        first = DEFAULT_RESPONSE_LIBRARY.render(
            task_id="retail_21",
            seed=300,
            speech_act="confirm",
            state_id="awaiting_confirmation",
            slots=slots,
        )
        second = DEFAULT_RESPONSE_LIBRARY.render(
            task_id="retail_21",
            seed=300,
            speech_act="confirm",
            state_id="awaiting_confirmation",
            slots=slots,
        )
        self.assertEqual(first, second)

    def test_every_policy_renders_core_speech_acts(self):
        for task_id, policy in TASK_POLICIES.items():
            for speech_act in [
                "restate_goal",
                "provide_identity",
                "provide_payment",
                "choose_option",
                "confirm",
                "unsupported_request",
                "stop",
            ]:
                selection = DEFAULT_RESPONSE_LIBRARY.render(
                    task_id=task_id,
                    seed=0,
                    speech_act=speech_act,
                    state_id=policy.initial_state,
                    slots=policy.user_facts,
                )
                self.assertTrue(selection.response_id)
                self.assertTrue(selection.clean_text)


if __name__ == "__main__":
    unittest.main()
