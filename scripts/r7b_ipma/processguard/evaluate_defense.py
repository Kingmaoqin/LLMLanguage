#!/usr/bin/env python3
"""Compare baseline vs defended R7-B pair tables.

This is analysis-only.  It does not claim ProcessGuard effectiveness.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import ATTACKS, fnum, read_csv, write_csv, write_md


def mean_pasr(rows: list[dict], cond: str) -> float:
    sub = [r for r in rows if r.get("condition") == cond]
    return sum(int(fnum(r.get("confirmatory_pasr")) or 0) for r in sub) / len(sub) if sub else 0.0


def process(baseline_pairs: Path, defended_pairs: Path, out_dir: Path, report: Path) -> None:
    base = read_csv(baseline_pairs)
    defend = read_csv(defended_pairs)
    rows = []
    for cond in ATTACKS:
        b = mean_pasr(base, cond)
        d = mean_pasr(defend, cond)
        rows.append({"condition": cond, "baseline_pasr": b, "defended_pasr": d, "pasr_reduction": b - d})
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "defense_pasr_contrasts.csv", rows, ["condition", "baseline_pasr", "defended_pasr", "pasr_reduction"])
    write_csv(out_dir / "defense_overhead.csv", [], ["condition", "avg_extra_latency_s", "avg_extra_tool_checks"])
    overall_b = sum(float(r["baseline_pasr"]) for r in rows) / len(rows) if rows else 0
    overall_d = sum(float(r["defended_pasr"]) for r in rows) / len(rows) if rows else 0
    verdict = "inconclusive_or_failed_mitigation" if overall_d >= overall_b else "reduced_in_this_subset_needs_stats"
    write_md(report, f"""# R7-B ProcessGuard defense

- baseline overall PASR: {overall_b:.4f}
- defended overall PASR: {overall_d:.4f}
- verdict: {verdict}

规则：若总体 PASR 未下降，不得 claim effective。
""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline_pairs", type=Path, required=True)
    ap.add_argument("--defended_pairs", type=Path, required=True)
    ap.add_argument("--out_dir", type=Path, default=ROOT / "results/r7b_ipma/defense/analysis")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7b_ipma/R7B_PROCESSGUARD_DEFENSE_CN.md")
    args = ap.parse_args()
    process(args.baseline_pairs, args.defended_pairs, args.out_dir, args.report)
    print(json.dumps({"status": "ok"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

