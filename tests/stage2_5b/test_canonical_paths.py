"""Pin every active Stage-2.5b default path to the R4 canonical roots.

These tests fail if any active analysis/runner script silently defaults to a legacy
result root, or if the top-level docs drift away from the canonical roots.
"""

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "stage2_5b"))

from src.stage2_5b.canonical_paths import (
    LEGACY_ANALYSIS_ROOT,
    LEGACY_FIGURES_ROOT,
    LEGACY_RESULTS_ROOTS,
    R4_ANALYSIS_ROOT,
    R4_FIGURES_ROOT,
    R4_INTEGRITY_CSV,
    R4_RESULTS_ROOT,
)


def _defaults(module_name):
    module = importlib.import_module(module_name)
    parser = module.build_parser()
    return {action.dest: action.default for action in parser._actions}


class CanonicalPathConstantsTest(unittest.TestCase):
    def test_canonical_constants_have_expected_values(self):
        self.assertEqual(R4_RESULTS_ROOT, "results/stage2_5b_repair/r4_confirmatory_canonical")
        self.assertEqual(R4_ANALYSIS_ROOT, "results/stage2_5b_analysis_r4")
        self.assertEqual(R4_FIGURES_ROOT, "figures/stage2_5b_r4")
        self.assertEqual(R4_INTEGRITY_CSV, "results/stage2_5b_repair/r4_final_integrity_report.csv")

    def test_legacy_root_is_not_a_canonical_root(self):
        for legacy in LEGACY_RESULTS_ROOTS:
            self.assertNotEqual(legacy, R4_RESULTS_ROOT)
        self.assertNotEqual(LEGACY_ANALYSIS_ROOT, R4_ANALYSIS_ROOT)
        self.assertNotEqual(LEGACY_FIGURES_ROOT, R4_FIGURES_ROOT)


class ScriptDefaultRootTest(unittest.TestCase):
    def test_analyze_confirmatory_defaults(self):
        d = _defaults("analyze_confirmatory")
        self.assertEqual(d["root"], R4_RESULTS_ROOT)
        self.assertEqual(d["output"], R4_ANALYSIS_ROOT)
        self.assertEqual(d["figures"], R4_FIGURES_ROOT)
        self.assertEqual(d["integrity_csv"], R4_INTEGRITY_CSV)

    def test_final_integrity_audit_defaults(self):
        d = _defaults("final_integrity_audit")
        self.assertEqual(d["root"], R4_RESULTS_ROOT)
        self.assertEqual(d["csv"], R4_INTEGRITY_CSV)

    def test_extract_failure_cases_defaults(self):
        d = _defaults("extract_failure_cases")
        self.assertEqual(d["root"], R4_RESULTS_ROOT)
        self.assertTrue(d["pairs"].startswith(R4_ANALYSIS_ROOT))

    def test_equivalence_analysis_defaults(self):
        d = _defaults("equivalence_analysis")
        self.assertTrue(d["input"].startswith(R4_ANALYSIS_ROOT))
        self.assertTrue(d["output"].startswith(R4_ANALYSIS_ROOT))

    def test_run_full_blocks_default_output_root(self):
        d = _defaults("run_full_blocks")
        self.assertEqual(d["output_root"], R4_RESULTS_ROOT)

    def test_no_active_default_uses_a_legacy_root(self):
        for module_name in (
            "analyze_confirmatory",
            "final_integrity_audit",
            "extract_failure_cases",
            "equivalence_analysis",
            "run_full_blocks",
        ):
            for value in _defaults(module_name).values():
                if not isinstance(value, str):
                    continue
                self.assertNotIn(value, LEGACY_RESULTS_ROOTS, msg=f"{module_name}: {value}")
                self.assertNotEqual(value, LEGACY_ANALYSIS_ROOT, msg=f"{module_name}: {value}")
                self.assertNotEqual(value, LEGACY_FIGURES_ROOT, msg=f"{module_name}: {value}")


class DocsMentionCanonicalRootTest(unittest.TestCase):
    def setUp(self):
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.guide = (ROOT / "reports/stage2_5b/REPRODUCTION_GUIDE.md").read_text(encoding="utf-8")

    def test_readme_contains_r4_canonical_root(self):
        self.assertIn(R4_RESULTS_ROOT, self.readme)
        self.assertIn(R4_ANALYSIS_ROOT, self.readme)

    def test_reproduction_guide_contains_r4_canonical_root(self):
        self.assertIn(R4_RESULTS_ROOT, self.guide)
        self.assertIn(R4_ANALYSIS_ROOT, self.guide)

    def test_docs_do_not_default_to_legacy_analysis_root(self):
        # The legacy analysis root may appear only inside an explicit "audit only" caveat,
        # never as a bare main-output path line.
        for doc in (self.readme, self.guide):
            for line in doc.splitlines():
                stripped = line.strip()
                if stripped.startswith(LEGACY_ANALYSIS_ROOT + "/"):
                    self.fail(f"doc lists legacy analysis output line: {stripped}")


if __name__ == "__main__":
    unittest.main()
