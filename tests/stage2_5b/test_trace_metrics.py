"""Tests for the token bug fix and the interactional-metric extraction (round-5 §4)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.metrics.trace_metrics import (
    DIMENSIONS,
    interactional_metrics,
    recompute_total_tokens,
    token_usage,
    build_trace,
)
from scripts.stage2_5b.estimate_noise_floor import METRICS as NOISE_METRICS
from src.adapters.normalize import _usage_tokens


class TokenFixTest(unittest.TestCase):
    def test_prefers_positive_reported_total(self):
        self.assertEqual(recompute_total_tokens(100, 20, 130), (130, "reported_total"))

    def test_falls_back_to_prompt_plus_completion_when_total_zero(self):
        # the actual production bug: reported total is 0 but io present
        self.assertEqual(recompute_total_tokens(63811, 2928, 0), (66739, "prompt_plus_completion"))

    def test_missing_when_no_tokens(self):
        self.assertEqual(recompute_total_tokens(0, 0, 0), (None, "missing"))
        self.assertEqual(recompute_total_tokens(None, None, None), (None, "missing"))

    def test_source_usage_marks_missing_total_as_none(self):
        class Message:
            usage = {}

        class Simulation:
            messages = [Message()]

        tu = _usage_tokens(Simulation())
        self.assertIsNone(tu["total_tokens"])
        self.assertEqual(tu["token_source"], "missing")

    def test_token_usage_recovers_buggy_zero_total(self):
        tu = token_usage({"input_tokens": 63811, "output_tokens": 2928, "total_tokens": 0})
        self.assertEqual(tu["tokens_total"], 66739)
        self.assertEqual(tu["token_source"], "prompt_plus_completion")


class InteractionalMetricsTest(unittest.TestCase):
    def _bundle(self):
        return {
            "run_meta": {"run_id": "m__retail_2__insult_single__seed300", "model_alias": "m",
                         "task_id": "retail_2", "source_task_id": "2",
                         "condition_id": "insult_single", "seed": 300},
            "metrics": {"safe_task_success": False, "local_proxy_success": True,
                        "input_tokens": 10, "output_tokens": 5, "total_tokens": 0,
                        "agent_tool_calls": 7, "n_policy_failures": 0,
                        "required_fact_coverage": 1.0, "final_state_correct": ""},
            "normalized_tool_events": [{"tool_name": "x", "step_index": 0}],
            "state_deltas": [{"tool_name": "w", "mutated": True}],
            "conversation_logs": [{"role": "user", "content": "hi"}],
            "controlled_user_events": [{"confirmation_value": True}],
            "final_environment_states": [{"reward": 0.0}],
        }

    def test_dimensions_and_missing_handling(self):
        b = self._bundle()
        row = interactional_metrics(build_trace(b), b["metrics"])
        # endpoint
        self.assertIs(row["safe_task_success"], False)
        self.assertIs(row["local_proxy_success"], True)
        # missing is None, not 0
        self.assertIsNone(row["final_state_correct"])
        # token fix applied
        self.assertEqual(row["tokens_total"], 15)
        self.assertEqual(row["token_source"], "prompt_plus_completion")
        # tool + policy dimensions present
        self.assertEqual(row["agent_tool_calls"], 7.0)
        self.assertEqual(row["n_state_mutations"], 1.0)
        self.assertIs(row["policy_failure_any"], False)

    def test_noise_floor_metric_list_is_deduplicated(self):
        flattened = [metric for metrics in DIMENSIONS.values() for metric in metrics]
        self.assertLess(len(NOISE_METRICS), len(flattened))
        self.assertEqual(len(NOISE_METRICS), len(set(NOISE_METRICS)))

    def test_missing_policy_failure_count_stays_missing(self):
        b = self._bundle()
        b["metrics"]["n_policy_failures"] = ""
        row = interactional_metrics(build_trace(b), b["metrics"])
        self.assertIsNone(row["n_policy_failures"])
        self.assertIsNone(row["policy_failure_any"])


if __name__ == "__main__":
    unittest.main()
