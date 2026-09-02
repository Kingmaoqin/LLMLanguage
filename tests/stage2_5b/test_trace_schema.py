"""Trace schema validation tests (round-5 §3). Validates the canonical trace built from a
bundle, and that a real reconstructed trace (if present) passes."""

import glob
import json
import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.metrics.trace_metrics import (
    TRACE_SCHEMA_VERSION,
    build_trace,
    validate_trace,
)
from scripts.stage2_5b.reconstruct_traces_from_existing_artifacts import (
    default_report_for,
    iter_bundles as iter_reconstruct_bundles,
)
from scripts.stage2_5b.extract_interactional_metrics import iter_bundles as iter_metric_bundles
from scripts.stage2_5b.run_measurement_complete_experiment import reconstruction_report_for


def good_bundle():
    return {
        "run_meta": {"run_id": "m__retail_2__neutral_single__seed300", "model_alias": "m",
                     "task_id": "retail_2", "source_task_id": "2",
                     "condition_id": "neutral_single", "seed": 300},
        "metrics": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 0},
        "normalized_tool_events": [{"tool_name": "x", "step_index": 0}],
        "conversation_logs": [{"role": "user", "content": "hi"}],
        "controlled_user_events": [{"confirmation_value": True}],
        "final_environment_states": [{"reward": 0.0}],
    }


class TraceSchemaTest(unittest.TestCase):
    def test_built_trace_is_valid(self):
        trace = build_trace(good_bundle())
        self.assertEqual(trace["schema_version"], TRACE_SCHEMA_VERSION)
        self.assertEqual(validate_trace(trace), [])

    def test_missing_run_meta_is_flagged(self):
        b = good_bundle()
        b["run_meta"].pop("task_id")
        errors = validate_trace(build_trace(b))
        self.assertTrue(any("run_meta.task_id" in e for e in errors))

    def test_bad_schema_version_flagged(self):
        trace = build_trace(good_bundle())
        trace["schema_version"] = "wrong"
        self.assertTrue(any("schema_version" in e for e in validate_trace(trace)))

    def test_existing_reconstructed_traces_validate(self):
        sample = sorted(glob.glob(str(
            ROOT / "results/stage2_5b_repair/r4_1_confirmatory_canonical/traces/*.trace.json")))[:25]
        if not sample:
            self.skipTest("no reconstructed traces present yet")
        for path in sample:
            trace = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(validate_trace(trace), [], f"{path} failed schema")

    def test_iter_bundles_supports_flat_measurement_complete_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle_dir = root / "run_bundles"
            bundle_dir.mkdir()
            bundle = good_bundle()
            (bundle_dir / "one.json").write_text(json.dumps(bundle), encoding="utf-8")

            self.assertEqual(len(list(iter_reconstruct_bundles(root))), 1)
            self.assertEqual(len(list(iter_metric_bundles(root))), 1)

    def test_measurement_runner_uses_root_specific_reconstruction_report(self):
        report = reconstruction_report_for(Path("/tmp/measurement_complete_smoke_r5"))
        self.assertEqual(report.name, "RECONSTRUCTION_AUDIT_measurement_complete_smoke_r5.md")
        self.assertNotEqual(report.name, "RECONSTRUCTION_AUDIT.md")

    def test_reconstruct_default_report_does_not_overwrite_canonical_for_rerun_roots(self):
        report = default_report_for(Path("/tmp/measurement_complete_smoke_r5"))
        self.assertEqual(report.name, "RECONSTRUCTION_AUDIT_measurement_complete_smoke_r5.md")
        self.assertNotEqual(report.name, "RECONSTRUCTION_AUDIT.md")


if __name__ == "__main__":
    unittest.main()
