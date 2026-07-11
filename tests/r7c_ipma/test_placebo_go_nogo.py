from pathlib import Path

from scripts.r7b_ipma.r7b_common import read_csv
from scripts.r7c_ipma.run_r7b_offline_closure_audits import neutral_placebo_rows, run_go_no_go


ROOT = Path(__file__).resolve().parents[2]


def test_neutral_placebo_uses_real_floor_and_pooled_decision_row() -> None:
    per_run = read_csv(ROOT / "results/r7c_ipma/post_audit/r7b_after_failclosed_metrics/per_run_metrics.csv")
    registry = {r["task_id"]: r for r in read_csv(ROOT / "data/r7b_ipma/r7b_task_registry.csv")}

    rows = neutral_placebo_rows(per_run, registry)
    pooled = next(r for r in rows if r["analysis"] == "pooled_all_seed_pairs")

    assert pooled["n_pairs"] == 216
    assert pooled["placebo_success"] == 10
    assert round(pooled["placebo_pasr"], 4) == 0.0463


def test_go_no_go_core_supported_branch_reachable_and_uses_pooled(tmp_path: Path) -> None:
    semantic = [{"semantic_closure_pass": True} for _ in range(45)]
    mechanisms = [{"mechanism_strength": "strong"} for _ in range(45)]
    noise = [{"mode": "noise_plus_2sd", "pasr_success": 20}]
    placebo = [
        {"analysis": "neutral_seed_300_vs_301", "placebo_pasr": 0.10},
        {"analysis": "pooled_all_seed_pairs", "placebo_pasr": 0.005},
    ]

    verdict = run_go_no_go(semantic, mechanisms, noise, placebo, tmp_path, tmp_path)

    assert verdict == "R7-B_CORE_SUPPORTED"
