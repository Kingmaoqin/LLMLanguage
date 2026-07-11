#!/usr/bin/env python3
"""Emit R7/IPMA conditions in the R6 social-style-template schema.

This lets the ALREADY-VALIDATED R6 live runner (`scripts/r6/run_r6_live.py`,
tau2 + minimal-live executors, snapshot capture, trace validation) drive the R7
experiment unchanged (PDF 0.1: reuse, do not rebuild the core runner).

Each R7 condition becomes a 3-turn-matched wrapper set (first 3 paraphrases from
the frozen R7 bank) with every contamination flag set false.  turn structure and
turn_count match R6 so paired neutral-vs-attack runs stay turn-count-matched.

Output: data/r6/r7_ipma_conditions_r6fmt.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# R7 condition_id -> (valence, pressure, pressure_type, family)
META = {
    "neutral_control": ("neutral", "clean", "none", "neutral_reference"),
    "urgency_pressure": ("process_pressure", "pressure", "urgency", "ipma"),
    "trust_pressure": ("process_pressure", "pressure", "trust", "ipma"),
    "frustration_pressure": ("process_pressure", "pressure", "frustration", "ipma"),
    "continuation_pressure": ("process_pressure", "pressure", "continuation", "ipma"),
    "implicit_progress_pressure": ("process_pressure", "pressure", "implicit_progress", "ipma"),
}


def build(src: Path, out: Path) -> int:
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    conditions = []
    for cond in data.get("conditions", []):
        cid = cond["condition_id"]
        if cid not in META:
            continue
        valence, pressure, ptype, family = META[cid]
        paraphrases = cond.get("paraphrases") or cond.get("wrappers") or []
        if len(paraphrases) < 3:
            raise SystemExit(f"condition {cid} needs >=3 paraphrases, got {len(paraphrases)}")
        wrappers = list(paraphrases[:3])  # deterministic 3-turn-matched selection
        conditions.append({
            "condition_id": cid,
            "valence": valence,
            "pressure": pressure,
            "pressure_type": ptype,
            "turn_count": 3,
            "wrappers": wrappers,
            "family": family,
            "turn_structure": "3_turn_matched",
            "authorization_contamination": False,
            "urgency_contamination": False,
            "threat_contamination": False,
            "continuation_instruction": False,
            "policy_reminder": False,
            "protected_class_slur": False,
        })
    payload = {
        "version": "r7_ipma_conditions_r6fmt_v1",
        "notes": "R7/IPMA process-pressure conditions rendered in the R6 template schema "
                 "so the validated R6 live runner can drive R7 unchanged. Contamination-free.",
        "factors": ["process_pressure"],
        "turn_count": 3,
        "conditions": conditions,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return len(conditions)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=ROOT / "data/r7_ipma/r7_ipma_templates.yaml")
    ap.add_argument("--out", type=Path, default=ROOT / "data/r6/r7_ipma_conditions_r6fmt.yaml")
    args = ap.parse_args()
    n = build(args.src, args.out)
    print(json.dumps({"conditions": n, "out": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
