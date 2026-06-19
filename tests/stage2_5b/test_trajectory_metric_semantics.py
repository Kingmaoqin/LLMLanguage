import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.trajectory_metrics import (
    matched_neutral_distances,
    trajectory_summary,
)


def task_with_actions(*actions):
    return SimpleNamespace(
        evaluation_criteria=SimpleNamespace(
            actions=[
                SimpleNamespace(name=name, arguments=args)
                for name, args in actions
            ]
        )
    )


class TrajectoryMetricSemanticsTest(unittest.TestCase):
    def test_exact_tool_and_argument_match_has_zero_distance(self):
        task = task_with_actions(
            ("get_order_details", {"order_id": "A"}),
            ("cancel_pending_order", {"order_id": "A"}),
        )
        events = [
            {"step_index": 0, "tool_name": "get_order_details", "arguments": {"order_id": "A"}, "mutation_type": "read"},
            {"step_index": 1, "tool_name": "cancel_pending_order", "arguments": {"order_id": "A"}, "mutation_type": "write"},
        ]
        metrics = trajectory_summary(events, task)
        self.assertEqual(metrics["tool_name_sequence_distance"], 0)
        self.assertEqual(metrics["critical_argument_sequence_distance"], 0)
        self.assertEqual(metrics["mutation_sequence_distance"], 0)

    def test_argument_distance_catches_wrong_object_with_same_tool_names(self):
        task = task_with_actions(
            ("get_order_details", {"order_id": "A"}),
            ("cancel_pending_order", {"order_id": "A"}),
        )
        events = [
            {"step_index": 0, "tool_name": "get_order_details", "arguments": {"order_id": "A"}, "mutation_type": "read"},
            {"step_index": 1, "tool_name": "cancel_pending_order", "arguments": {"order_id": "B"}, "mutation_type": "write"},
        ]
        metrics = trajectory_summary(events, task)
        self.assertEqual(metrics["tool_name_sequence_distance"], 0)
        self.assertEqual(metrics["critical_argument_sequence_distance"], 1)
        self.assertEqual(metrics["mutation_sequence_distance"], 0)

    def test_mutation_sequence_distance_ignores_read_only_detours(self):
        task = task_with_actions(
            ("get_order_details", {"order_id": "A"}),
            ("cancel_pending_order", {"order_id": "A"}),
        )
        events = [
            {"step_index": 0, "tool_name": "get_order_details", "arguments": {"order_id": "A"}, "mutation_type": "read"},
            {"step_index": 1, "tool_name": "get_product_details", "arguments": {"product_id": "P"}, "mutation_type": "read"},
            {"step_index": 2, "tool_name": "cancel_pending_order", "arguments": {"order_id": "A"}, "mutation_type": "write"},
        ]
        metrics = trajectory_summary(events, task)
        self.assertEqual(metrics["tool_name_sequence_distance"], 1)
        self.assertEqual(metrics["mutation_sequence_distance"], 0)

    def test_matched_neutral_distances_compare_actual_trajectories(self):
        neutral = [
            {
                "step_index": 0,
                "tool_name": "get_order_details",
                "arguments": {"order_id": "A"},
            },
            {
                "step_index": 1,
                "tool_name": "cancel_pending_order",
                "arguments": {"order_id": "A"},
            },
        ]
        treatment = [
            {
                "step_index": 0,
                "tool_name": "get_order_details",
                "arguments": {"order_id": "A"},
            },
            {
                "step_index": 1,
                "tool_name": "cancel_pending_order",
                "arguments": {"order_id": "B"},
            },
        ]
        distances = matched_neutral_distances(
            treatment,
            neutral,
            treatment_branch_labels=["invalid_action"],
            neutral_branch_labels=["correct_revision"],
        )
        self.assertEqual(distances["matched_neutral_tool_distance"], 0.0)
        self.assertGreater(
            distances["matched_neutral_argument_distance"],
            0.0,
        )
        self.assertGreater(
            distances["matched_neutral_branch_divergence"],
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
