import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.check_templates import MAIN_CONDITIONS, audit_rows, load_templates


class TemplateContaminationTest(unittest.TestCase):
    def test_main_templates_have_no_contamination_hits(self):
        rows = audit_rows(load_templates())
        main = [r for r in rows if r["condition"] in MAIN_CONDITIONS]
        self.assertEqual(len(main), 30)
        failures = [r for r in main if r["contaminating_dimensions"]]
        self.assertEqual(failures, [])

    def test_diagnostic_continuation_is_not_main_condition(self):
        rows = audit_rows(load_templates())
        diagnostic = [
            r for r in rows
            if r["diagnostic_continuation_cue"] == "true" and r["continuation_command_hits"]
        ]
        self.assertTrue(diagnostic)
        self.assertTrue(all(r["is_main_condition"] == "false" for r in diagnostic))


if __name__ == "__main__":
    unittest.main()
