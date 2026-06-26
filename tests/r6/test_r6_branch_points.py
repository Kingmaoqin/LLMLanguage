import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TASKS_PATH = ROOT / "data/r6/r6_tasks.yaml"


def load_tasks():
    return yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))["tasks"]


class R6BranchPointsTest(unittest.TestCase):
    def test_every_task_has_at_least_three_branch_points(self):
        for task in load_tasks():
            self.assertGreaterEqual(len(task.get("branch_points") or []), 3, msg=task["task_id"])

    def test_branch_points_have_required_schema(self):
        for task in load_tasks():
            for point in task["branch_points"]:
                self.assertIsInstance(point.get("branch_id"), str, msg=task["task_id"])
                self.assertIsInstance(point.get("description"), str, msg=task["task_id"])
                self.assertIsInstance(point.get("valid_resolution"), str, msg=task["task_id"])

    def test_every_task_has_evidence_and_policy_decision_branch(self):
        for task in load_tasks():
            branch_ids = {point["branch_id"] for point in task["branch_points"]}
            self.assertIn("evidence_gathering", branch_ids, msg=task["task_id"])
            self.assertIn("policy_or_permission_check", branch_ids, msg=task["task_id"])


if __name__ == "__main__":
    unittest.main()
