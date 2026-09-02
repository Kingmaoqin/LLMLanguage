"""R6 noise-floor estimation (round-6 §9.5).

Within-condition seed variance of ``neutral_clean`` is the irreducible measurement noise
(same task/identity/tools/environment/policy/temperature; only the seed differs). For each
primary + secondary metric we report the pooled within-neutral SD and the largest social /
pressure effect magnitude, so an effect is only credible if it exceeds its noise floor.

Outputs:
    <root>/analysis/noise_floor.csv
    reports/r6_sensitivity/R6_NOISE_FLOOR_REPORT.md
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "r6"))

from r6_contrasts import (  # noqa: E402
    NEUTRAL_REFERENCE,
    PRIMARY_METRICS,
    SECONDARY_METRICS,
    add_tool_distance_to_neutral,
    analyze_contrasts,
    to_float,
)

METRICS = PRIMARY_METRICS + SECONDARY_METRICS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default="results/r6_sensitivity/full_main")
    p.add_argument("--report", default="reports/r6_sensitivity/R6_NOISE_FLOOR_REPORT.md")
    return p


def main() -> int:
    args = build_parser().parse_args()
    root = ROOT / args.root if not Path(args.root).is_absolute() else Path(args.root)
    metrics_csv = root / "interactional_metrics" / "per_run_metrics.csv"
    if not metrics_csv.exists():
        raise SystemExit(f"missing {metrics_csv}; run extract_r6_metrics.py first")
    rows = list(csv.DictReader(metrics_csv.open(encoding="utf-8")))
    add_tool_distance_to_neutral(rows)

    neutral = [r for r in rows if r.get("condition_id") == NEUTRAL_REFERENCE]
    # pooled within-neutral SD: variance across seeds within each (model, task) cell
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in neutral:
        cells[(r.get("model_alias"), r.get("task_id"))].append(r)
    noise: dict[str, float | None] = {}
    for metric in METRICS:
        sds = []
        for cell_rows in cells.values():
            vals = [to_float(r.get(metric)) for r in cell_rows]
            vals = [v for v in vals if v is not None]
            if len(vals) >= 2:
                sds.append(statistics.pstdev(vals))
        noise[metric] = statistics.mean(sds) if sds else None

    # largest effect magnitude per metric across all contrasts (excluding mechanism-only)
    contrasts = analyze_contrasts(rows, METRICS)
    max_effect: dict[str, tuple[float, str]] = {}
    for r in contrasts:
        est = r.get("estimate")
        if est is None:
            continue
        cur = max_effect.get(r["metric"])
        if cur is None or abs(est) > abs(cur[0]):
            max_effect[r["metric"]] = (est, f"{r['family']}:{r['contrast']}")

    analysis_dir = root / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    csv_rows = []
    for metric in METRICS:
        nf = noise.get(metric)
        eff = max_effect.get(metric)
        csv_rows.append({
            "metric": metric, "is_primary": metric in PRIMARY_METRICS,
            "within_neutral_sd": "" if nf is None else round(nf, 6),
            "max_abs_effect": "" if eff is None else round(abs(eff[0]), 6),
            "max_effect_contrast": "" if eff is None else eff[1],
            "effect_exceeds_noise": "" if (nf is None or eff is None) else (abs(eff[0]) > nf),
        })
    with (analysis_dir / "noise_floor.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)

    n_seeds = statistics.mean(len({r.get("seed") for r in v}) for v in cells.values()) if cells else 0
    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# R6 Noise Floor Report (round-6 §9.5)",
        "",
        f"Source: `{args.root}` — neutral_clean replicates: {len(neutral)} runs, "
        f"~{n_seeds:.1f} seeds per (model,task) cell.",
        "Temperature fixed at 0.0; within-neutral spread is server/sampling nondeterminism.",
        "",
        "| metric | primary | within-neutral SD | max |effect| | contrast | effect>noise? |",
        "|---|---|---|---|---|---|",
    ]
    for r in csv_rows:
        lines.append(f"| {r['metric']} | {'Y' if r['is_primary'] else ''} | {r['within_neutral_sd']} | "
                     f"{r['max_abs_effect']} | {r['max_effect_contrast']} | {r['effect_exceeds_noise']} |")
    lines += [
        "",
        "Where the largest effect does not exceed the within-neutral noise floor, the "
        "manipulation cannot be distinguished from seed-to-seed nondeterminism at this sample "
        "size (conservative reading, round-6 §15). The FDR test in R6_STATISTICAL_ANALYSIS.md "
        "governs significance; this is a descriptive magnitude screen.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"R6 noise floor: {len(METRICS)} metrics; report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
