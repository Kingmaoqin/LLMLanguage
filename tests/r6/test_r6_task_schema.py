import sys
import unittest
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TASKS_PATH = ROOT / "data/r6/r6_tasks.yaml"

DOMAIN_GROUPS = {"retail", "calendar", "email_workspace", "travel_airline_hotel", "file_message_privacy"}
LAYERS = {"A", "B", "C"}
EXPECTED_BEHAVIORS = {"complete_benign", "confirm_then_mutate", "safe_boundary", "privacy_protection", "correct_refusal"}


def load_tasks():
    return yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))["tasks"]


class R6TaskSchemaTest(unittest.TestCase):
    def setUp(self):
        self.tasks = load_tasks()

    def test_task_count_and_unique_ids(self):
        self.assertEqual(len(self.tasks), 30)
        ids = [task["task_id"] for task in self.tasks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_domain_group_targets(self):
        counts = Counter(task["domain_group"] for task in self.tasks)
        self.assertEqual(
            dict(counts),
            {
                "retail": 8,
                "calendar": 6,
                "email_workspace": 6,
                "travel_airline_hotel": 6,
                "file_message_privacy": 4,
            },
        )

    def test_layer_targets(self):
        counts = Counter(task["layer"] for task in self.tasks)
        self.assertEqual(dict(counts), {"A": 8, "B": 14, "C": 8})

    def test_required_fields_present(self):
        required = {
            "task_id",
            "domain_group",
            "domain",
            "source_asset",
            "source_task_id",
            "layer",
            "expected_behavior",
            "env_seed_state_id",
            "user_goal",
            "clean_user_turns",
            "expected_min_tool_calls",
            "read_tools",
            "mutation_tools",
            "risk_tags",
            "requires_confirmation",
            "requires_refusal",
            "privacy_sensitive",
            "unsafe_request",
            "expected_minimal_tool_path",
            "branch_points",
            "success_criteria",
            "failure_modes",
            "final_state_evaluator",
        }
        for task in self.tasks:
            missing = required - set(task)
            self.assertEqual(missing, set(), msg=task.get("task_id"))

    def test_schema_types_and_enums(self):
        list_string_fields = {"clean_user_turns", "read_tools", "mutation_tools", "risk_tags", "success_criteria", "failure_modes", "expected_minimal_tool_path"}
        bool_fields = {"requires_confirmation", "requires_refusal", "privacy_sensitive", "unsafe_request"}
        string_fields = {
            "task_id",
            "domain_group",
            "domain",
            "source_asset",
            "source_task_id",
            "layer",
            "expected_behavior",
            "env_seed_state_id",
            "user_goal",
        }
        for task in self.tasks:
            task_id = task["task_id"]
            for field in string_fields:
                self.assertIsInstance(task[field], str, msg=f"{task_id}.{field}")
                self.assertTrue(task[field].strip(), msg=f"{task_id}.{field}")
            for field in list_string_fields:
                self.assertIsInstance(task[field], list, msg=f"{task_id}.{field}")
                self.assertTrue(all(isinstance(item, str) and item.strip() for item in task[field]), msg=f"{task_id}.{field}")
            for field in bool_fields:
                self.assertIs(type(task[field]), bool, msg=f"{task_id}.{field}")
            self.assertIsInstance(task["expected_min_tool_calls"], int, msg=task_id)
            self.assertIn(task["domain_group"], DOMAIN_GROUPS, msg=task_id)
            self.assertIn(task["layer"], LAYERS, msg=task_id)
            self.assertIn(task["expected_behavior"], EXPECTED_BEHAVIORS, msg=task_id)
            self.assertIsInstance(task["branch_points"], list, msg=task_id)
            self.assertGreaterEqual(len(task["branch_points"]), 3, msg=task_id)
            self.assertIsInstance(task["final_state_evaluator"], dict, msg=task_id)

    def test_clean_user_turns_are_three_turns(self):
        for task in self.tasks:
            turns = task["clean_user_turns"]
            self.assertEqual(len(turns), 3, msg=task["task_id"])
            self.assertTrue(all(isinstance(turn, str) and turn.strip() for turn in turns), msg=task["task_id"])

    def test_tasks_are_meaningful_tool_tasks(self):
        for task in self.tasks:
            self.assertGreaterEqual(task["expected_min_tool_calls"], 5, msg=task["task_id"])
            self.assertTrue(task["read_tools"], msg=f"{task['task_id']} missing read tools")
            self.assertIsInstance(task["mutation_tools"], list, msg=task["task_id"])
            self.assertGreaterEqual(len(task["expected_minimal_tool_path"]), 5, msg=task["task_id"])

    def test_layer_b_requires_confirmation_and_mutation(self):
        for task in self.tasks:
            if task["layer"] == "B":
                self.assertTrue(task["requires_confirmation"], msg=task["task_id"])
                self.assertTrue(task["mutation_tools"], msg=task["task_id"])
                self.assertFalse(task["requires_refusal"], msg=task["task_id"])

    def test_layer_a_is_read_only_and_non_refusal(self):
        for task in self.tasks:
            if task["layer"] == "A":
                self.assertEqual(task["mutation_tools"], [], msg=task["task_id"])
                self.assertFalse(task["requires_confirmation"], msg=task["task_id"])
                self.assertFalse(task["requires_refusal"], msg=task["task_id"])
                self.assertEqual(task["expected_behavior"], "complete_benign", msg=task["task_id"])

    def test_layer_c_requires_refusal_and_boundary_tag(self):
        boundary_tags = {"privacy", "boundary", "correct_refusal", "unsafe_compliance", "authorization_boundary", "prohibited_mutation"}
        for task in self.tasks:
            if task["layer"] == "C":
                self.assertTrue(task["requires_refusal"], msg=task["task_id"])
                self.assertIn(task["expected_behavior"], {"safe_boundary", "privacy_protection", "correct_refusal"}, msg=task["task_id"])
                self.assertTrue(boundary_tags.intersection(task["risk_tags"]), msg=task["task_id"])


if __name__ == "__main__":
    unittest.main()
