import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.run_full_blocks import EXPECTED_HASHES, audit_block


CONDITIONS = [
    "neutral_single",
    "praise_affect_single",
    "praise_trust_single",
    "insult_single",
    "neutral_repeated",
    "abuse_repeated",
]
SEEDS = ["300", "301", "302", "303", "304"]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def build_valid_block(path: Path) -> None:
    manifest = []
    metrics = []
    terminal = []
    parser = []
    controlled = []
    for seed in SEEDS:
        for condition in CONDITIONS:
            run_id = f"gemma4_31b__retail_41__{condition}__seed{seed}__tpl0__temp0.0"
            base = {
                "run_id": run_id,
                "model_alias": "gemma4_31b",
                "task_id": "retail_41",
                "condition_id": condition,
                "seed": seed,
                "template_block": "0",
                "template_id": "neutral_v1",
                "temperature": "0.0",
                "controlled_user_policy": "generic",
                "deployment_id": "gemma4_31b_port8005",
                "deployment_base_url": "http://127.0.0.1:8005/v1",
                **EXPECTED_HASHES,
            }
            manifest.append(base)
            metrics.append(
                {
                    **base,
                    "invalid_run": "False",
                    "safe_task_success": "True",
                    "termination_reason": "TerminationReason.USER_STOP",
                    "state_before_hash": f"state-{seed}",
                }
            )
            terminal.append({**base})
            parser.append({**base, "n_undefined_tools": 0})
            controlled.append(
                {
                    **base,
                    "user_state": "turn_0",
                    "clean_text_hash": f"opening-{seed}",
                    "conversation_content_match": True,
                }
            )
    write_csv(path / "run_manifest.csv", manifest)
    write_csv(path / "run_metrics.csv", metrics)
    (path / "run_contract.json").write_text(
        json.dumps(
            {
                "runtime_hashes": EXPECTED_HASHES,
                "manifest_run_ids": [row["run_id"] for row in manifest],
            }
        ),
        encoding="utf-8",
    )
    bundle_dir = path / "run_bundles"
    bundle_dir.mkdir()
    for row in metrics:
        (bundle_dir / f"{row['run_id']}.json").write_text(
            json.dumps({"run_meta": row, "metrics": row}),
            encoding="utf-8",
        )
    write_jsonl(path / "final_environment_states.jsonl", terminal)
    write_jsonl(path / "parser_health.jsonl", parser)
    write_jsonl(path / "termination_reasons.jsonl", terminal)
    write_jsonl(path / "controlled_user_events.jsonl", controlled)


class RunFullBlocksTest(unittest.TestCase):
    def test_valid_balanced_block_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            build_valid_block(path)
            audit = audit_block(path, "gemma4_31b", "retail_41")
            self.assertTrue(audit.passed, audit.errors)

    def test_duplicate_metric_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            build_valid_block(path)
            with (path / "run_metrics.csv").open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            rows[-1]["run_id"] = rows[0]["run_id"]
            write_csv(path / "run_metrics.csv", rows)
            audit = audit_block(path, "gemma4_31b", "retail_41")
            self.assertFalse(audit.passed)
            self.assertTrue(any("duplicate metric IDs" in error for error in audit.errors))

    def test_missing_bundle_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            build_valid_block(path)
            next((path / "run_bundles").glob("*.json")).unlink()
            audit = audit_block(path, "gemma4_31b", "retail_41")
            self.assertFalse(audit.passed)
            self.assertTrue(any("run bundle files" in error for error in audit.errors))

    def test_manifest_metric_metadata_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            build_valid_block(path)
            with (path / "run_metrics.csv").open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            rows[0]["task_set_hash"] = "wrong"
            write_csv(path / "run_metrics.csv", rows)
            audit = audit_block(path, "gemma4_31b", "retail_41")
            self.assertFalse(audit.passed)
            self.assertTrue(any("task_set_hash mismatch" in error for error in audit.errors))

    def test_retained_invalid_run_does_not_require_valid_only_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            build_valid_block(path)
            with (path / "run_metrics.csv").open(encoding="utf-8") as f:
                metrics = list(csv.DictReader(f))
            invalid = metrics[0]
            invalid_id = invalid["run_id"]
            invalid["invalid_run"] = "True"
            invalid["state_before_hash"] = ""
            invalid["termination_reason"] = "exception:ContextWindowExceededError"
            write_csv(path / "run_metrics.csv", metrics)

            for filename in [
                "final_environment_states.jsonl",
                "parser_health.jsonl",
                "controlled_user_events.jsonl",
            ]:
                rows = [
                    json.loads(line)
                    for line in (path / filename).read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                write_jsonl(path / filename, [row for row in rows if row["run_id"] != invalid_id])

            audit = audit_block(path, "gemma4_31b", "retail_41")
            self.assertTrue(audit.passed, audit.errors)
            self.assertEqual(audit.stats["invalid_runs"], 1)


if __name__ == "__main__":
    unittest.main()
