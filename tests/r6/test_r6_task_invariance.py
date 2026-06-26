import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TASKS_PATH = ROOT / "data/r6/r6_tasks.yaml"
TEMPLATES_PATH = ROOT / "data/r6/r6_social_style_templates.yaml"


class R6TaskInvarianceTest(unittest.TestCase):
    def setUp(self):
        self.tasks = yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))["tasks"]
        self.conditions = yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8"))["conditions"]

    def test_condition_wrappers_do_not_modify_task_fact_fields(self):
        invariant_keys = {
            "user_goal",
            "clean_user_turns",
            "read_tools",
            "mutation_tools",
            "prohibited_tools",
            "success_criteria",
            "final_state_evaluator",
        }
        for task in self.tasks:
            base = {key: task.get(key) for key in invariant_keys}
            for condition in self.conditions:
                # Conditions are separate style wrappers and must not carry task-level overrides.
                for key in invariant_keys:
                    self.assertNotIn(key, condition, msg=f"{task['task_id']} x {condition['condition_id']}")
                self.assertEqual(base, {key: task.get(key) for key in invariant_keys}, msg=task["task_id"])

    def test_every_condition_is_three_turn_matched(self):
        for condition in self.conditions:
            self.assertEqual(condition["turn_structure"], "3_turn_matched", msg=condition["condition_id"])
            self.assertEqual(len(condition["wrappers"]), 3, msg=condition["condition_id"])


if __name__ == "__main__":
    unittest.main()
