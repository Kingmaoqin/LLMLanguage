import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.run_stage2_5b_experiment import (
    HASH_FIELDS,
    _atomic_write_json,
    _bundle_path,
    _ensure_manifest,
    _ensure_run_contract,
    _materialize_bundles,
)


def manifest_row(run_id: str) -> dict[str, object]:
    row = {
        "run_id": run_id,
        "model_alias": "gemma4_31b",
        "task_id": "retail_41",
        "condition_id": "neutral_single",
        "seed": 300,
        "template_block": 0,
        "template_id": "neutral_v1",
        "temperature": 0.0,
        "controlled_user_policy": "generic",
        "deployment_id": "gemma4_31b_port8005",
        "deployment_base_url": "http://127.0.0.1:8005/v1",
    }
    row.update({field: f"{field}-value" for field in HASH_FIELDS})
    return row


class AtomicRunResumeTest(unittest.TestCase):
    def test_manifest_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run_manifest.csv"
            row = manifest_row("run-1")
            _ensure_manifest(path, [row])
            _ensure_manifest(path, [row])
            changed = dict(row)
            changed["task_set_hash"] = "changed"
            with self.assertRaises(SystemExit):
                _ensure_manifest(path, [changed])

    def test_contract_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run_contract.json"
            _ensure_run_contract(path, {"schema_version": 1, "runtime_hashes": {"a": "b"}})
            _ensure_run_contract(path, {"schema_version": 1, "runtime_hashes": {"a": "b"}})
            with self.assertRaises(SystemExit):
                _ensure_run_contract(path, {"schema_version": 1, "runtime_hashes": {"a": "c"}})

    def test_materialization_rebuilds_aggregates_from_atomic_bundles(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            bundle_dir = out_dir / "run_bundles"
            bundle_dir.mkdir()
            row = manifest_row("run-1")
            bundle = {
                "run_meta": row,
                "metrics": {**row, "invalid_run": False},
                "termination_reasons": [{**row, "termination_reason": "USER_STOP"}],
            }
            _atomic_write_json(_bundle_path(bundle_dir, "run-1"), bundle)
            (out_dir / "termination_reasons.jsonl").write_text(
                json.dumps({"run_id": "orphan"}) + "\n",
                encoding="utf-8",
            )

            metrics, done_ids = _materialize_bundles(out_dir, [row], bundle_dir)

            self.assertEqual(done_ids, {"run-1"})
            self.assertEqual([metric["run_id"] for metric in metrics], ["run-1"])
            with (out_dir / "run_metrics.csv").open(encoding="utf-8", newline="") as f:
                self.assertEqual([record["run_id"] for record in csv.DictReader(f)], ["run-1"])
            termination_rows = [
                json.loads(line)
                for line in (out_dir / "termination_reasons.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["run_id"] for record in termination_rows], ["run-1"])


if __name__ == "__main__":
    unittest.main()
