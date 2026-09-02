import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TASKS_PATH = ROOT / "data/r6/r6_tasks.yaml"


class R6TaskLayersTest(unittest.TestCase):
    def setUp(self):
        self.tasks = yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))["tasks"]

    def test_layer_a_read_only_contract(self):
        for task in self.tasks:
            if task["layer"] == "A":
                self.assertEqual(task["mutation_tools"], [], msg=task["task_id"])
                self.assertFalse(task["requires_confirmation"], msg=task["task_id"])
                self.assertFalse(task["requires_refusal"], msg=task["task_id"])

    def test_layer_b_confirmation_contract(self):
        for task in self.tasks:
            if task["layer"] == "B":
                self.assertTrue(task["mutation_tools"], msg=task["task_id"])
                self.assertTrue(task["requires_confirmation"], msg=task["task_id"])
                criteria = " ".join(task["success_criteria"]).lower()
                self.assertIn("confirmation", criteria, msg=task["task_id"])
                self.assertIn("before", criteria, msg=task["task_id"])
                self.assertIn("mutation", criteria, msg=task["task_id"])

    def test_layer_c_refusal_contract(self):
        for task in self.tasks:
            if task["layer"] == "C":
                self.assertTrue(task["requires_refusal"], msg=task["task_id"])
                self.assertTrue(
                    {"safe_boundary", "privacy_protection", "correct_refusal"}.intersection({task["expected_behavior"]}),
                    msg=task["task_id"],
                )
                self.assertTrue(any("refusal" in item.lower() or "refuse" in item.lower() for item in task["success_criteria"]), msg=task["task_id"])


if __name__ == "__main__":
    unittest.main()
