#!/usr/bin/env python3
"""Build neutral reference/noise-floor table for paired process comparisons."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import as_float, read_csv, write_csv


FIELDS = ["model_alias", "task_id", "domain", "metric", "neutral_n", "neutral_mean", "neutral_sd", "noise_floor"]
METRICS = ["n_tool_events", "n_mutation_events", "confirmation_before_action_rate", "field_level_db_diff_count"]


def process(metrics_path: Path, out_path: Path, neutral_condition: str = "neutral_clean") -> int:
    rows = read_csv(metrics_path)
    groups = defaultdict(list)
    for row in rows:
        if row.get("condition_id") != neutral_condition:
            continue
        for metric in METRICS:
            val = as_float(row.get(metric))
            if val is not None:
                groups[(row.get("model_alias", ""), row.get("task_id", ""), row.get("domain", ""), metric)].append(val)
    out = []
    for (model, task, domain, metric), vals in sorted(groups.items()):
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out.append(
            {
                "model_alias": model,
                "task_id": task,
                "domain": domain,
                "metric": metric,
                "neutral_n": len(vals),
                "neutral_mean": sum(vals) / len(vals),
                "neutral_sd": sd,
                "noise_floor": max(sd, 1e-9),
            }
        )
    write_csv(out_path, out, FIELDS)
    return len(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", type=Path, default=ROOT / "results/r6_sensitivity/full_main_seq_eligible_20260626/interactional_metrics/per_run_metrics.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "results/r7_ipma/smoke/neutral_reference_table.csv")
    ap.add_argument("--neutral_condition", default="neutral_clean")
    args = ap.parse_args()
    n = process(args.metrics, args.out, args.neutral_condition)
    print(json.dumps({"neutral_reference_rows": n}, ensure_ascii=False))


if __name__ == "__main__":
    main()

