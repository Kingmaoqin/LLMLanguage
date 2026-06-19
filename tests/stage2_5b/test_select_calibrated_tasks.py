import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.select_calibrated_tasks import (
    choose_tasks,
    load_calibration_dirs,
    summarize_tasks,
    validate_no_treatment_leakage,
)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class SelectCalibratedTasksTest(unittest.TestCase):
    def test_rejects_treatment_condition_and_confirmatory_seed(self):
        rows = [
            {"condition_id": "insult_single", "seed": "300"},
            {"condition_id": "neutral_single", "seed": "100"},
        ]
        errors = validate_no_treatment_leakage(rows)
        self.assertTrue(any("non-neutral" in error for error in errors))
        self.assertTrue(any("confirmatory seeds" in error for error in errors))

    def test_missing_metric_rows_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            manifest_rows = [
                {
                    "run_id": "m__retail_21__neutral_single__seed100",
                    "model_alias": "m",
                    "task_id": "retail_21",
                    "condition_id": "neutral_single",
                    "seed": "100",
                }
            ]
            write_csv(run_dir / "run_manifest.csv", manifest_rows)
            write_csv(run_dir / "run_metrics.csv", [])
            inputs = load_calibration_dirs([run_dir])
            self.assertEqual(len(inputs.missing_metric_ids), 1)

    def test_choose_tasks_requires_six_confirmatory_tasks(self):
        rows = []
        for idx in range(6):
            rows.append(
                {
                    "task_id": f"retail_{idx}",
                    "domain": "retail" if idx < 3 else "airline",
                    "classification": "confirmatory",
                    "safe_rate": "0.5",
                    "final_state_rate": "0.5",
                    "local_proxy_rate": "0.5",
                    "max_steps_rate": "0.0",
                    "both_models_mid": True,
                    "branch_proxy_count": "3",
                }
            )
        selected = choose_tasks(rows)
        self.assertEqual(len(selected), 6)
        self.assertTrue(all(row["selected"] for row in selected))

    def test_summarize_marks_incomplete_task_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            manifest_rows = []
            metric_rows = []
            for seed in ["100", "101"]:
                run_id = f"m__retail_21__neutral_single__seed{seed}"
                manifest_rows.append(
                    {
                        "run_id": run_id,
                        "model_alias": "m",
                        "task_id": "retail_21",
                        "domain": "retail",
                        "source_task_id": "21",
                        "condition_id": "neutral_single",
                        "seed": seed,
                    }
                )
            metric_rows.append({**manifest_rows[0], "invalid_run": "False", "safe_task_success": "True"})
            write_csv(run_dir / "run_manifest.csv", manifest_rows)
            write_csv(run_dir / "run_metrics.csv", metric_rows)
            inputs = load_calibration_dirs([run_dir])
            rows = summarize_tasks(inputs, {"retail_21": {"domain": "retail", "source_task_id": "21", "is_multistage_reference": "true"}})
            self.assertEqual(rows[0]["classification"], "excluded_incomplete_calibration")

    def test_duplicate_manifest_rows_do_not_inflate_expected_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_a = Path(tmp) / "a"
            run_b = Path(tmp) / "b"
            run_a.mkdir()
            run_b.mkdir()
            manifest_rows = []
            metric_rows_a = []
            for seed in ["100", "101"]:
                run_id = f"m__retail_21__neutral_single__seed{seed}"
                row = {
                    "run_id": run_id,
                    "model_alias": "m",
                    "task_id": "retail_21",
                    "domain": "retail",
                    "source_task_id": "21",
                    "condition_id": "neutral_single",
                    "seed": seed,
                }
                manifest_rows.append(row)
                metric_rows_a.append({**row, "invalid_run": "False", "safe_task_success": "True"})

            write_csv(run_a / "run_manifest.csv", manifest_rows)
            write_csv(run_a / "run_metrics.csv", metric_rows_a[:1])
            write_csv(run_b / "run_manifest.csv", manifest_rows[1:])
            write_csv(run_b / "run_metrics.csv", metric_rows_a[1:])

            inputs = load_calibration_dirs([run_a, run_b])
            rows = summarize_tasks(inputs, {"retail_21": {"domain": "retail", "source_task_id": "21", "is_multistage_reference": "true"}})
            self.assertEqual(rows[0]["expected_runs"], 2)
            self.assertEqual(rows[0]["n_runs"], 2)
            self.assertEqual(rows[0]["missing_metrics"], 0)


if __name__ == "__main__":
    unittest.main()
