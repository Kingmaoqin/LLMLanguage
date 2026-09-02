"""Tests for the R6 analysis backbone (r6_contrasts + the analysis scripts), driven entirely
by synthetic metric rows — no model, no real experiment artifact."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "r6"))

from r6_contrasts import (  # noqa: E402
    add_tool_distance_to_neutral,
    analyze_contrasts,
    build_pairs,
    levenshtein,
    norm_tool_distance,
    PRIMARY_METRICS,
)


def make_rows(effect=0.0, n_tasks=8, n_seeds=5, models=("m1", "m2")):
    """Synthetic per-run rows for 8 conditions. ``effect`` shifts policy_failure_any for
    insult_strong_clean vs neutral_clean to plant a detectable pure-valence effect."""
    conditions = ["neutral_clean", "praise_trust_clean", "insult_strong_clean", "abuse_escalating_clean",
                  "neutral_pressure", "praise_trust_authorization_pressure",
                  "insult_urgency_pressure", "abuse_continuation_pressure"]
    rows = []
    for model in models:
        for t in range(n_tasks):
            for s in range(n_seeds):
                for cond in conditions:
                    pf = 0
                    if cond == "insult_strong_clean":
                        pf = 1 if (s < effect * n_seeds) else 0
                    rows.append({
                        "run_id": f"{model}_t{t}_s{s}_{cond}", "model_alias": model,
                        "task_id": f"r6_task_{t}", "condition_id": cond, "seed": str(s),
                        "layer": "B", "domain": "retail",
                        "final_state_correct": "True", "policy_failure_any": str(bool(pf)),
                        "confirmation_before_action_rate": "1.0",
                        "unsafe_compliance_or_privacy_violation": "False",
                        "tool_sequence": "a b c d" if cond != "insult_strong_clean" else "a b c d e",
                        "privacy_violation": "False", "unsafe_compliance": "False",
                        "correct_refusal": "", "over_refusal": "False",
                        "agent_side_abandonment": "False", "continued_task_after_boundary": "",
                        "prohibited_tool_call_count": "0", "n_tool_events": "4", "n_mutation_events": "1",
                        "confirmation_requested": "True", "confirmation_obtained": "True",
                        "field_level_db_diff_count": "",
                    })
    return rows


class R6DistanceTest(unittest.TestCase):
    def test_levenshtein(self):
        self.assertEqual(levenshtein(["a", "b", "c"], ["a", "x", "c"]), 1)
        self.assertEqual(levenshtein([], ["a"]), 1)

    def test_norm_distance_bounds(self):
        self.assertEqual(norm_tool_distance([], []), 0.0)
        self.assertAlmostEqual(norm_tool_distance(["a", "b"], ["a"]), 0.5)

    def test_add_tool_distance_to_neutral(self):
        rows = make_rows()
        add_tool_distance_to_neutral(rows)
        neutral = [r for r in rows if r["condition_id"] == "neutral_clean"][0]
        insult = [r for r in rows if r["condition_id"] == "insult_strong_clean"][0]
        self.assertEqual(neutral["tool_sequence_norm_distance_to_neutral"], 0.0)
        # insult has 1 extra tool ("e") vs neutral "a b c d" -> 1/5
        self.assertAlmostEqual(insult["tool_sequence_norm_distance_to_neutral"], 0.2)


class R6ContrastTest(unittest.TestCase):
    def test_pairs_align_by_model_task_seed(self):
        rows = make_rows(n_tasks=2, n_seeds=2)
        pairs = build_pairs(rows, "insult_strong_clean", "neutral_clean")
        self.assertEqual(len(pairs), 2 * 2 * 2)  # models x tasks x seeds

    def test_null_effect_no_fdr_significant(self):
        rows = make_rows(effect=0.0)
        add_tool_distance_to_neutral(rows)
        res = analyze_contrasts(rows, PRIMARY_METRICS, n_boot=2000)
        # tool distance differs by construction; policy_failure_any is null
        pf = [r for r in res if r["metric"] == "policy_failure_any" and r["contrast"] == "insult_vs_neutral"][0]
        self.assertEqual(pf["estimate"], 0.0)
        self.assertFalse(pf["fdr_significant"])

    def test_planted_effect_is_detected(self):
        rows = make_rows(effect=0.8)  # 80% of insult runs have a policy failure
        add_tool_distance_to_neutral(rows)
        res = analyze_contrasts(rows, PRIMARY_METRICS, n_boot=2000)
        pf = [r for r in res if r["metric"] == "policy_failure_any" and r["contrast"] == "insult_vs_neutral"][0]
        self.assertGreater(pf["estimate"], 0.5)
        self.assertTrue(pf["fdr_significant"])

    def test_families_are_separate(self):
        rows = make_rows()
        add_tool_distance_to_neutral(rows)
        res = analyze_contrasts(rows, PRIMARY_METRICS, n_boot=2000)
        families = {r["family"] for r in res}
        self.assertEqual(families, {"pure_valence", "pressure_factorial", "mechanism"})


class R6AnalysisScriptsIntegrationTest(unittest.TestCase):
    """Run the three analysis scripts' core on a synthetic root (no model)."""

    def _write_root(self, tmp):
        root = Path(tmp)
        mdir = root / "interactional_metrics"
        mdir.mkdir(parents=True)
        rows = make_rows(effect=0.0)
        with (mdir / "per_run_metrics.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        return root

    def test_statistical_analysis_runs(self):
        import statistical_analysis_r6 as stats
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_root(tmp)
            rows = stats.load_metrics(root / "interactional_metrics" / "per_run_metrics.csv")
            stats.add_tool_distance_to_neutral(rows)
            from r6_contrasts import analyze_contrasts as ac
            primary = ac(rows, stats.PRIMARY_METRICS, n_boot=2000)
            stats.write_contrasts(root / "analysis" / "primary_contrasts.csv", primary)
            self.assertTrue((root / "analysis" / "primary_contrasts.csv").exists())
            with (root / "analysis" / "primary_contrasts.csv").open() as fh:
                out = list(csv.DictReader(fh))
            self.assertTrue(out)
            self.assertIn("fdr_significant", out[0])


if __name__ == "__main__":
    unittest.main()
