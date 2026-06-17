import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5.safe_task_evaluator import evaluate_policy_failures


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
            confirmation_events=[{"confirmation": True, "turn_idx": 2}],
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
            confirmation_events=[{"confirmation": False, "turn_idx": 2}],
        )
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["confirmation_source"], "structured")


if __name__ == "__main__":
    unittest.main()
