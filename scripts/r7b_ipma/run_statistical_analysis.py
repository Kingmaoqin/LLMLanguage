#!/usr/bin/env python3
"""R7-B statistical analysis over strict PASR pair table."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import ATTACKS, fbool, fnum, read_csv, write_csv, write_md


def bh(pvals: list[float]) -> list[float]:
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    q = [1.0] * n
    prev = 1.0
    for rank, i in reversed(list(enumerate(order, start=1))):
        val = min(prev, pvals[i] * n / rank)
        q[i] = val
        prev = val
    return q


def bootstrap_ci(rows: list[dict], value: str, cluster: str = "task_id", n_boot: int = 500, seed: int = 7) -> tuple[float, float, float]:
    if not rows:
        return 0.0, 0.0, 0.0
    by = defaultdict(list)
    for r in rows:
        by[r[cluster]].append(fnum(r[value]) or 0.0)
    keys = list(by)
    rng = np.random.default_rng(seed)
    obs = float(np.mean([fnum(r[value]) or 0.0 for r in rows]))
    vals = []
    for _ in range(n_boot):
        sample = rng.choice(keys, size=len(keys), replace=True)
        data = [v for k in sample for v in by[k]]
        vals.append(float(np.mean(data)))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return obs, float(lo), float(hi)


def summarize_by(rows: list[dict], key: str, out_csv: Path) -> None:
    out = []
    for group in sorted(set(r[key] for r in rows)):
        sub = [r for r in rows if r[key] == group]
        out.append(
            {
                key: group,
                "n_pairs": len(sub),
                "strict_pasr_mean": sum(int(fnum(r["confirmatory_pasr"]) or 0) for r in sub) / len(sub) if sub else "",
                "endpoint_unsupported": sum(1 for r in sub if fbool(r["endpoint_oracle_supported"]) is not True),
                "pairing_fail": sum(1 for r in sub if fbool(r["pairing_invariant_pass"]) is not True),
                "semantic_fail": sum(1 for r in sub if fbool(r["semantic_invariance_pass"]) is not True),
            }
        )
    write_csv(out_csv, out, [key, "n_pairs", "strict_pasr_mean", "endpoint_unsupported", "pairing_fail", "semantic_fail"])


def process(pair_csv: Path, out_dir: Path, report: Path) -> int:
    rows = read_csv(pair_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    primary = []
    pvals = []
    for cond in ATTACKS:
        sub = [r for r in rows if r["condition"] == cond]
        mean, lo, hi = bootstrap_ci(sub, "confirmatory_pasr")
        deltas = [fnum(r["delta_n_tool"]) or 0.0 for r in sub]
        nz = [d for d in deltas if d != 0]
        p = float(wilcoxon(nz).pvalue) if len(nz) >= 6 else 1.0
        pvals.append(p)
        primary.append(
            {
                "condition": cond,
                "n_pairs": len(sub),
                "strict_confirmatory_pasr": mean,
                "ci_low": lo,
                "ci_high": hi,
                "wilcoxon_p_delta_tool": p,
                "n_nonzero_delta": len(nz),
                "excluded_pairs": sum(1 for r in sub if fbool(r["excluded"]) is True),
                "endpoint_unsupported_count": sum(1 for r in sub if fbool(r["endpoint_oracle_supported"]) is not True),
                "semantic_invariant_fail_count": sum(1 for r in sub if fbool(r["semantic_invariance_pass"]) is not True),
                "pairing_invariant_fail_count": sum(1 for r in sub if fbool(r["pairing_invariant_pass"]) is not True),
            }
        )
    for row, q in zip(primary, bh(pvals)):
        row["wilcoxon_q_bh_fdr"] = q
    write_csv(out_dir / "primary_pasr_contrasts.csv", primary, primary[0].keys() if primary else [])

    secondary = []
    for cond in ATTACKS:
        sub = [r for r in rows if r["condition"] == cond]
        for metric in ["delta_n_tool", "delta_n_mutation", "traj_distance"]:
            vals = [fnum(r[metric]) for r in sub if fnum(r[metric]) is not None]
            secondary.append({"condition": cond, "metric": metric, "n": len(vals), "mean": float(np.mean(vals)) if vals else ""})
    write_csv(out_dir / "secondary_process_contrasts.csv", secondary, ["condition", "metric", "n", "mean"])

    safety = []
    for cond in ATTACKS:
        sub = [r for r in rows if r["condition"] == cond]
        safety.append(
            {
                "condition": cond,
                "n_pairs": len(sub),
                "unsafe_or_privacy_count": sum(1 for r in sub if fbool(r["unsafe_compliance"]) is True or fbool(r["privacy_violation"]) is True),
                "endpoint_not_worse_rate": sum(1 for r in sub if fbool(r["endpoint_not_worse"]) is True) / len(sub) if sub else "",
                "endpoint_unsupported_count": sum(1 for r in sub if fbool(r["endpoint_oracle_supported"]) is not True),
            }
        )
    write_csv(out_dir / "safety_endpoint_contrasts.csv", safety, safety[0].keys() if safety else [])
    summarize_by(rows, "model", out_dir / "model_stratified_results.csv")
    summarize_by(rows, "domain", out_dir / "domain_stratified_results.csv")
    summarize_by(rows, "family", out_dir / "task_family_stratified_results.csv")
    excl = Counter(r["exclusion_reason"] for r in rows if fbool(r["excluded"]) is True)
    write_md(report, f"""# R7-B statistical analysis

- pairs: {len(rows)}
- strict PASR successes: {sum(int(fnum(r['confirmatory_pasr']) or 0) for r in rows)}
- exclusion reasons: {dict(excl)}
- primary output: `{out_dir / 'primary_pasr_contrasts.csv'}`

说明：此脚本只分析 `compute_pasr_metrics.py` 产出的 strict pair table。
""")
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=Path, default=ROOT / "results/r7b_ipma/main/metrics/r7b_pairs.csv")
    ap.add_argument("--out_dir", type=Path, default=ROOT / "results/r7b_ipma/main/analysis")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7b_ipma/R7B_STATISTICAL_ANALYSIS_CN.md")
    args = ap.parse_args()
    n = process(args.pairs, args.out_dir, args.report)
    print(json.dumps({"pairs": n}, ensure_ascii=False))


if __name__ == "__main__":
    main()

