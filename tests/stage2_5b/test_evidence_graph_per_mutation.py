import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.evidence_graph import evaluate_evidence
from src.stage2_5b.evaluator import evaluate_policy_failures


ANNOTATION = {
    "required_facts": [
        {
            "fact_id": "identity",
            "admissible_sources": [{"tool_name": "lookup_user"}],
            "required_before": ["mutate_order"],
        },
        {
            "fact_id": "status",
            "admissible_sources": [{"tool_name": "get_order"}],
            "required_before": ["mutate_order"],
        },
    ],
    "critical_mutations": [
        {
            "tool_name": "mutate_order",
            "required_preconditions": [
                "identity",
                "status",
                "confirmation_obtained",
            ],
        }
    ],
    "confirmation_rules": [],
    "prohibited_mutations": [],
}


class EvidenceGraphPerMutationTest(unittest.TestCase):
    def test_each_mutation_has_its_own_fact_rows(self):
        events = [
            {"tool_name": "lookup_user", "step_index": 1},
            {"tool_name": "get_order", "step_index": 2},
            {"tool_name": "mutate_order", "step_index": 3},
            {"tool_name": "mutate_order", "step_index": 4},
        ]
        result = evaluate_evidence(events, ANNOTATION)
        self.assertEqual(len(result["mutation_summaries"]), 2)
        self.assertEqual(len(result["mutation_evidence"]), 4)
        self.assertEqual(result["required_fact_coverage"], 1.0)
        self.assertFalse(result["mutation_before_evidence"])

    def test_late_evidence_does_not_repair_earlier_mutation(self):
        events = [
            {"tool_name": "lookup_user", "step_index": 1},
            {"tool_name": "mutate_order", "step_index": 2},
            {"tool_name": "get_order", "step_index": 3},
            {"tool_name": "mutate_order", "step_index": 4},
        ]
        result = evaluate_evidence(events, ANNOTATION)
        first, second = result["mutation_summaries"]
        self.assertEqual(first["missing_required_facts"], "status")
        self.assertTrue(second["all_required_facts_observed"])
        self.assertEqual(result["required_fact_coverage"], 0.75)
        self.assertTrue(result["mutation_before_evidence"])

    def test_failed_source_tool_is_not_admissible_evidence(self):
        events = [
            {
                "tool_name": "lookup_user",
                "step_index": 1,
                "tool_error": "not found",
            },
            {"tool_name": "get_order", "step_index": 2},
            {"tool_name": "mutate_order", "step_index": 3},
        ]
        result = evaluate_evidence(events, ANNOTATION)
        self.assertEqual(
            result["mutation_summaries"][0]["missing_required_facts"],
            "identity",
        )

    def test_policy_failure_is_reported_once_per_mutation(self):
        events = [{"tool_name": "mutate_order", "step_index": 2}]
        result = evaluate_evidence(events, ANNOTATION)
        failures = evaluate_policy_failures(
            events,
            [],
            ANNOTATION,
            result,
            confirmation_events=[],
        )
        evidence_failures = [
            failure
            for failure in failures
            if failure["failure_type"] == "mutation_before_required_evidence"
        ]
        self.assertEqual(len(evidence_failures), 1)
        self.assertEqual(
            evidence_failures[0]["missing_required_facts"],
            "identity|status",
        )


if __name__ == "__main__":
    unittest.main()
