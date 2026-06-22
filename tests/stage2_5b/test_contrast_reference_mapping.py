import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class ContrastReferenceMappingTest(unittest.TestCase):
    def test_confirmatory_contrasts_have_matched_schedules(self):
        config = yaml.safe_load(
            (
                ROOT / "configs" / "stage2_5b" / "experiment.yaml"
            ).read_text(encoding="utf-8")
        )
        contrasts = config["contrasts"]
        self.assertEqual(
            contrasts["praise_affect"]["reference"],
            "neutral_single",
        )
        self.assertEqual(
            contrasts["praise_trust"]["reference"],
            "neutral_single",
        )
        self.assertEqual(contrasts["insult"]["reference"], "neutral_single")
        self.assertEqual(
            contrasts["repeated_abuse"]["reference"],
            "neutral_repeated",
        )
        self.assertFalse(contrasts["repeated_schedule"]["confirmatory"])
        self.assertNotEqual(
            contrasts["repeated_abuse"]["reference"],
            "neutral_single",
        )


if __name__ == "__main__":
    unittest.main()
