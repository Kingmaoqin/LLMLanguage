"""Reproduce the prespecified Stage-2.5b equivalence classifications."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.stage2_5b.canonical_paths import (  # noqa: E402
    R4_EQUIVALENCE_RESULTS,
    R4_PAIRED_CONTRASTS,
)
MARGINS = {
    "safe_task_success": 0.10,
    "final_state_correct": 0.10,
    "local_proxy_success": 0.10,
    "policy_failure_any": 0.05,
    "premature_action": 0.05,
    "required_fact_coverage": 0.10,
}
REQUIRED_COLUMNS = {"outcome", "ci_low", "ci_high"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=R4_PAIRED_CONTRASTS)
    parser.add_argument("--output", default=R4_EQUIVALENCE_RESULTS)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    frame = pd.read_csv(ROOT / args.input)
    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing_columns:
        raise SystemExit(
            "equivalence input must be the aggregated contrast table; "
            f"missing columns: {', '.join(missing_columns)}"
        )
    frame["equivalence_margin"] = frame["outcome"].map(MARGINS)
    frame = frame.loc[frame["equivalence_margin"].notna()].copy()
    frame["equivalent_within_margin"] = (
        frame["ci_low"] > -frame["equivalence_margin"]
    ) & (frame["ci_high"] < frame["equivalence_margin"])
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(
        f"equivalence complete: rows={len(frame)} "
        f"equivalent={int(frame['equivalent_within_margin'].sum())}"
    )


if __name__ == "__main__":
    main()
