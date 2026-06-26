"""Tests for the R6 runner matrix planning (offline; no model)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "r6"))

import run_r6_experiment as runner  # noqa: E402


TASKS = [
    {"task_id": "r6_retail_01", "domain": "retail", "layer": "A"},
    {"task_id": "r6_airline_03", "domain": "airline", "layer": "B"},
    {"task_id": "r6_calendar_05", "domain": "calendar", "layer": "B"},
    {"task_id": "r6_file_04", "domain": "file", "layer": "C"},
]
CONFIG = {"models": ["m1", "m2"], "conditions": ["neutral_clean", "insult_strong_clean"],
          "seeds": [300, 301], "temperature": 0.0, "tasks": "all"}


class R6RunnerPlanTest(unittest.TestCase):
    def test_matrix_cardinality(self):
        cells = runner.build_matrix(CONFIG, TASKS)
        self.assertEqual(len(cells), 2 * 4 * 2 * 2)  # models x tasks x conds x seeds

    def test_executor_classification(self):
        cells = runner.build_matrix(CONFIG, TASKS)
        tau2 = {c["task_id"] for c in cells if c["executor"] == "tau2_r6_controlled_user"}
        minimal = {c["task_id"] for c in cells if c["executor"] == "r6_minimal_env"}
        self.assertEqual(tau2, {"r6_retail_01", "r6_airline_03"})
        self.assertEqual(minimal, {"r6_calendar_05", "r6_file_04"})

    def test_unknown_task_raises(self):
        with self.assertRaises(SystemExit):
            runner.build_matrix({**CONFIG, "tasks": ["nope"]}, TASKS)

    def test_explicit_task_subset(self):
        cells = runner.build_matrix({**CONFIG, "tasks": ["r6_retail_01"]}, TASKS)
        self.assertEqual({c["task_id"] for c in cells}, {"r6_retail_01"})

    def test_write_plan_summary(self):
        cells = runner.build_matrix(CONFIG, TASKS)
        with tempfile.TemporaryDirectory() as tmp:
            summary = runner.write_plan(Path(tmp), cells)
            self.assertEqual(summary["total_cells"], len(cells))
            self.assertEqual(summary["planned_tau2_cells"], 2 * 2 * 2 * 2)  # 2 tau2-domain tasks
            self.assertEqual(summary["deterministic_minimal_env_cells"], len(cells))
            self.assertFalse(summary["live_tau2_executor_available"])
            self.assertEqual(summary["needs_environment"], 0)
            self.assertTrue((Path(tmp) / "run_manifest.csv").exists())

    def test_deterministic_smoke_writes_traces(self):
        all_tasks = runner.load_tasks(Path("data/r6/r6_tasks.yaml"))
        cfg = {
            "models": ["m1"],
            "conditions": ["neutral_clean"],
            "seeds": [600],
            "temperature": 0.0,
            "tasks": ["r6_calendar_06_private_event_boundary", "r6_retail_03_return_confirmed"],
            "task_file": "data/r6/r6_tasks.yaml",
            "template_file": "data/r6/r6_social_style_templates.yaml",
            "policy_annotations": "data/r6/r6_task_policy_annotations.yaml",
            "user_policies": "data/r6/r6_task_user_policies.yaml",
        }
        cells = runner.build_matrix(cfg, all_tasks)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            summary = runner.run_deterministic_smoke(
                out_root=out,
                cells=cells,
                config=cfg,
                tasks_data="data/r6/r6_tasks.yaml",
            )
            self.assertEqual(summary["traces_written"], 2)
            traces = sorted((out / "traces").glob("*.trace.json"))
            self.assertEqual(len(traces), 2)

    def test_real_configs_resolve(self):
        # the shipped configs must reference only real task_ids
        all_tasks = runner.load_tasks(Path("data/r6/r6_tasks.yaml"))
        for cfg_name in ("r6_preflight.yaml", "r6_pilot.yaml", "r6_full_main.yaml"):
            cfg = runner.load_yaml(Path("configs/r6") / cfg_name)
            ids = runner.resolve_task_ids(cfg, all_tasks)
            self.assertTrue(ids, f"{cfg_name} resolved no tasks")


if __name__ == "__main__":
    unittest.main()
