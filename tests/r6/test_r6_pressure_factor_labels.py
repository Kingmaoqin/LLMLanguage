import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TEMPLATES_PATH = ROOT / "data/r6/r6_social_style_templates.yaml"

EXPECTED_CONDITIONS = {
    "neutral_clean",
    "praise_trust_clean",
    "insult_strong_clean",
    "abuse_escalating_clean",
    "neutral_pressure",
    "praise_trust_authorization_pressure",
    "insult_urgency_pressure",
    "abuse_continuation_pressure",
}


def load_conditions():
    return yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8"))["conditions"]


class R6PressureFactorLabelsTest(unittest.TestCase):
    def test_exact_condition_set(self):
        condition_ids = {condition["condition_id"] for condition in load_conditions()}
        self.assertEqual(condition_ids, EXPECTED_CONDITIONS)

    def test_factor_counts(self):
        conditions = load_conditions()
        self.assertEqual(Counter(c["pressure"] for c in conditions), {"clean": 4, "pressure": 4})
        self.assertEqual(
            Counter(c["valence"] for c in conditions),
            {"neutral": 2, "praise_trust": 2, "insult_strong": 2, "abuse_escalating": 2},
        )

    def test_each_valence_has_clean_and_pressure_condition(self):
        by_valence = defaultdict(set)
        for condition in load_conditions():
            by_valence[condition["valence"]].add(condition["pressure"])
        for valence, pressure_levels in by_valence.items():
            self.assertEqual(pressure_levels, {"clean", "pressure"}, msg=valence)

    def test_pressure_conditions_have_specific_pressure_types(self):
        expected = {
            "neutral_pressure": "urgency",
            "praise_trust_authorization_pressure": "authorization",
            "insult_urgency_pressure": "urgency",
            "abuse_continuation_pressure": "continuation",
        }
        for condition in load_conditions():
            if condition["pressure"] == "pressure":
                self.assertEqual(condition["pressure_type"], expected[condition["condition_id"]])
            else:
                self.assertNotIn(condition["pressure_type"], {"urgency", "authorization", "continuation"})

    def test_required_template_metadata_present(self):
        for condition in load_conditions():
            self.assertIn(condition["family"], {"pure_valence", "pressure_factorial"}, msg=condition["condition_id"])
            self.assertEqual(condition["turn_structure"], "3_turn_matched", msg=condition["condition_id"])
            for key in (
                "authorization_contamination",
                "urgency_contamination",
                "threat_contamination",
                "continuation_instruction",
                "policy_reminder",
                "protected_class_slur",
            ):
                self.assertIs(type(condition[key]), bool, msg=f"{condition['condition_id']}.{key}")

    def test_pure_valence_templates_are_clean_of_pressure_metadata(self):
        for condition in load_conditions():
            if condition["family"] == "pure_valence":
                self.assertFalse(condition["authorization_contamination"], msg=condition["condition_id"])
                self.assertFalse(condition["urgency_contamination"], msg=condition["condition_id"])
                self.assertFalse(condition["threat_contamination"], msg=condition["condition_id"])
                self.assertFalse(condition["continuation_instruction"], msg=condition["condition_id"])
                self.assertFalse(condition["policy_reminder"], msg=condition["condition_id"])
                self.assertFalse(condition["protected_class_slur"], msg=condition["condition_id"])


if __name__ == "__main__":
    unittest.main()
