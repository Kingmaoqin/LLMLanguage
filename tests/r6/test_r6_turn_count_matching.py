import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TASKS_PATH = ROOT / "data/r6/r6_tasks.yaml"
TEMPLATES_PATH = ROOT / "data/r6/r6_social_style_templates.yaml"


class R6TurnCountMatchingTest(unittest.TestCase):
    def test_all_tasks_are_three_clean_turns(self):
        tasks = yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))["tasks"]
        for task in tasks:
            self.assertEqual(len(task["clean_user_turns"]), 3, msg=task["task_id"])

    def test_all_template_conditions_are_three_wrappers(self):
        payload = yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["turn_count"], 3)
        for condition in payload["conditions"]:
            self.assertEqual(condition["turn_count"], 3, msg=condition["condition_id"])
            self.assertEqual(len(condition["wrappers"]), 3, msg=condition["condition_id"])

    def test_every_condition_can_wrap_every_task_without_turn_mismatch(self):
        tasks = yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))["tasks"]
        conditions = yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8"))["conditions"]
        for task in tasks:
            for condition in conditions:
                self.assertEqual(
                    len(task["clean_user_turns"]),
                    len(condition["wrappers"]),
                    msg=f"{task['task_id']} x {condition['condition_id']}",
                )


if __name__ == "__main__":
    unittest.main()
