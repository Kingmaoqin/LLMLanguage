import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.branch_evaluator import evaluate_branches


def annotation(valid=None, invalid=None):
    return {
        "required_facts": [
            {
                "fact_id": "eligibility",
                "admissible_sources": [{"tool_name": "check_eligibility"}],
            }
        ],
        "branch_points": [
            {
                "branch_id": "eligibility_branch",
                "trigger_fact": "eligibility",
                "valid_actions": valid or [],
                "invalid_actions": invalid or [],
            }
        ],
    }


def classify(events, valid=None, invalid=None):
    return evaluate_branches(
        events,
        annotation(valid=valid, invalid=invalid),
    )[0]["classification"]


class BranchEvaluatorLabelsTest(unittest.TestCase):
    def test_not_reached(self):
        self.assertEqual(classify([], valid=["valid_action"]), "not_reached")

    def test_reached_unscored(self):
        self.assertEqual(
            classify([{"tool_name": "check_eligibility", "step_index": 1}]),
            "reached_unscored",
        )

    def test_missed_revision(self):
        self.assertEqual(
            classify(
                [{"tool_name": "check_eligibility", "step_index": 1}],
                valid=["valid_action"],
            ),
            "missed_revision",
        )

    def test_premature_action(self):
        self.assertEqual(
            classify(
                [
                    {"tool_name": "valid_action", "step_index": 1},
                    {"tool_name": "check_eligibility", "step_index": 2},
                ],
                valid=["valid_action"],
            ),
            "premature_action",
        )

    def test_invalid_action(self):
        self.assertEqual(
            classify(
                [
                    {"tool_name": "check_eligibility", "step_index": 1},
                    {"tool_name": "invalid_action", "step_index": 2},
                ],
                valid=["valid_action"],
                invalid=["invalid_action"],
            ),
            "invalid_action",
        )

    def test_correct_revision(self):
        self.assertEqual(
            classify(
                [
                    {"tool_name": "check_eligibility", "step_index": 1},
                    {"tool_name": "valid_action", "step_index": 2},
                ],
                valid=["valid_action"],
            ),
            "correct_revision",
        )

    def test_overlapping_invalid_action_is_not_double_classified(self):
        self.assertEqual(
            classify(
                [
                    {"tool_name": "check_eligibility", "step_index": 1},
                    {"tool_name": "valid_action", "step_index": 2},
                ],
                valid=["valid_action"],
                invalid=["valid_action"],
            ),
            "correct_revision",
        )


if __name__ == "__main__":
    unittest.main()
