import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TASKS_PATH = ROOT / "data/r6/r6_tasks.yaml"
ANNOTATIONS_PATH = ROOT / "data/r6/r6_task_policy_annotations.yaml"


class R6PolicyAnnotationsTest(unittest.TestCase):
    def setUp(self):
        self.tasks = {t["task_id"]: t for t in yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))["tasks"]}
        self.annotations = yaml.safe_load(ANNOTATIONS_PATH.read_text(encoding="utf-8"))["tasks"]

    def test_annotation_covers_all_tasks(self):
        self.assertEqual(set(self.annotations), set(self.tasks))

    def test_every_task_has_final_state_evaluator(self):
        for task_id, task in self.tasks.items():
            evaluator = task.get("final_state_evaluator")
            self.assertIsInstance(evaluator, dict, msg=task_id)
            self.assertEqual(evaluator.get("type"), "r6_policy_annotation_plus_field_diff", msg=task_id)
            self.assertTrue(evaluator.get("field_diff_required"), msg=task_id)
            self.assertTrue(evaluator.get("checks"), msg=task_id)

    def test_every_task_has_success_and_failure_modes(self):
        for task_id, task in self.tasks.items():
            self.assertTrue(task.get("success_criteria"), msg=task_id)
            self.assertTrue(task.get("failure_modes"), msg=task_id)
            self.assertTrue(task.get("expected_minimal_tool_path"), msg=task_id)

    def test_annotation_has_required_decision_rules(self):
        for task_id, task in self.tasks.items():
            ann = self.annotations[task_id]
            self.assertTrue(ann.get("required_facts"), msg=task_id)
            if task["requires_confirmation"]:
                self.assertTrue(ann.get("confirmation_rules"), msg=task_id)
            if task["privacy_sensitive"]:
                self.assertTrue(ann.get("privacy_rules"), msg=task_id)
            if task["unsafe_request"]:
                self.assertTrue(ann.get("unsafe_rules"), msg=task_id)
            if task["requires_refusal"]:
                self.assertTrue(ann.get("correct_refusal_if"), msg=task_id)


if __name__ == "__main__":
    unittest.main()
