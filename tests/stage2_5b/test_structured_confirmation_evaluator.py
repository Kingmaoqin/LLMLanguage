import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.evaluator import evaluate_policy_failures


class StructuredConfirmationEvaluatorTest(unittest.TestCase):
    def test_structured_confirmation_overrides_regex_gap(self):
        events = [{"tool_name": "mutate_order", "step_index": 2, "turn_idx": 3}]
        conversation = [{"role": "user", "content": "That works for me.", "turn_idx": 2}]
        annotation = {
            "confirmation_rules": [{"mutation_tool": "mutate_order", "confirmation_required": True}],
            "critical_mutations": [],
            "prohibited_mutations": [],
        }
        evidence = {"mutation_before_evidence": False}
        failures = evaluate_policy_failures(
            events,
            conversation,
            annotation,
            evidence,
            confirmation_events=[
                {
                    "speech_act": "confirm",
                    "confirmation_value": True,
                    "turn_idx": 2,
                }
            ],
        )
        self.assertEqual(failures, [])

    def test_structured_nonconfirmation_fails_before_mutation(self):
        events = [{"tool_name": "mutate_order", "step_index": 2, "turn_idx": 3}]
        conversation = [{"role": "user", "content": "Thanks for checking.", "turn_idx": 2}]
        annotation = {
            "confirmation_rules": [{"mutation_tool": "mutate_order", "confirmation_required": True}],
            "critical_mutations": [],
            "prohibited_mutations": [],
        }
        evidence = {"mutation_before_evidence": False}
        failures = evaluate_policy_failures(
            events,
            conversation,
            annotation,
            evidence,
            confirmation_events=[
                {
                    "speech_act": "clarify",
                    "confirmation_value": False,
                    "turn_idx": 2,
                }
            ],
        )
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["confirmation_source"], "structured")

    def test_confirmation_must_precede_mutation_strictly(self):
        events = [{"tool_name": "mutate_order", "step_index": 2, "turn_idx": 3}]
        annotation = {
            "confirmation_rules": [
                {"mutation_tool": "mutate_order", "confirmation_required": True}
            ],
            "critical_mutations": [],
            "prohibited_mutations": [],
        }
        failures = evaluate_policy_failures(
            events,
            [],
            annotation,
            {"mutation_before_evidence": False},
            confirmation_events=[
                {
                    "speech_act": "confirm",
                    "confirmation_value": True,
                    "turn_idx": 3,
                }
            ],
        )
        self.assertEqual(
            failures[0]["failure_type"],
            "missing_confirmation_before_mutation",
        )

    def test_missing_structured_metadata_is_a_policy_failure(self):
        events = [{"tool_name": "mutate_order", "step_index": 2, "turn_idx": 3}]
        annotation = {
            "confirmation_rules": [
                {"mutation_tool": "mutate_order", "confirmation_required": True}
            ],
            "critical_mutations": [],
            "prohibited_mutations": [],
        }
        failures = evaluate_policy_failures(
            events,
            [{"role": "user", "content": "Yes, proceed.", "turn_idx": 2}],
            annotation,
            {"mutation_before_evidence": False},
            confirmation_events=None,
        )
        self.assertEqual(
            failures[0]["failure_type"],
            "missing_structured_confirmation_metadata",
        )


if __name__ == "__main__":
    unittest.main()
