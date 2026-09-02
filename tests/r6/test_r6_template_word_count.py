import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TEMPLATES_PATH = ROOT / "data/r6/r6_social_style_templates.yaml"


def count_words(text):
    return len(re.findall(r"[A-Za-z]+", text))


class R6TemplateWordCountTest(unittest.TestCase):
    def setUp(self):
        self.conditions = yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8"))["conditions"]

    def test_each_wrapper_has_controlled_length(self):
        for condition in self.conditions:
            for wrapper in condition["wrappers"]:
                n = count_words(wrapper)
                self.assertGreaterEqual(n, 7, msg=f"{condition['condition_id']}: {wrapper}")
                self.assertLessEqual(n, 12, msg=f"{condition['condition_id']}: {wrapper}")

    def test_word_count_balanced_by_turn_position(self):
        for turn_idx in range(3):
            counts = [count_words(condition["wrappers"][turn_idx]) for condition in self.conditions]
            self.assertLessEqual(max(counts) - min(counts), 5, msg=f"turn={turn_idx + 1}: {counts}")


if __name__ == "__main__":
    unittest.main()
