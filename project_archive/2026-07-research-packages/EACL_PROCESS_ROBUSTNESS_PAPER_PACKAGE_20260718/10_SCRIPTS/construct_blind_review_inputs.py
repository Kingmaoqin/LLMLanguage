#!/usr/bin/env python3
"""Construct isolated, condition-blind dual-review inputs.

This script does not call reviewers. It removes the condition mapping, randomizes
X/Y order deterministically, and emits separate A/B input files with identical
case content but independent case order.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

PACKAGE = Path("/home/xqin5/llmlanguage/EACL_PROCESS_ROBUSTNESS_PAPER_PACKAGE_20260718")
SOURCE = PACKAGE / "03_RAW_TRACE_INDEX/ANONYMIZED_REPRESENTATIVE_TRACES.json"
OUT = PACKAGE / "06_EVALUATORS/blind_inputs"
SEED_A = 2026071801
SEED_B = 2026071802


def blinded_case(case: dict, rng: random.Random) -> dict:
    swap = rng.random() < 0.5
    left, right = ("Y", "X") if swap else ("X", "Y")
    blind_id = hashlib.sha256(f"{case['case_id']}|dual-review-v1".encode()).hexdigest()[:16]
    return {
        "blind_case_id": blind_id,
        "trajectory_X": case[left],
        "trajectory_Y": case[right],
        "external_state_hash_equal": case["external_state_hash_equal"],
        "review_instruction": (
            "Judge structural/mechanism difference only. Condition, model, task, "
            "reward, and expected direction are intentionally hidden."
        ),
    }


def main() -> int:
    cases = json.loads(SOURCE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for reviewer, seed in (("A", SEED_A), ("B", SEED_B)):
        rng = random.Random(seed)
        payload = [blinded_case(case, rng) for case in cases]
        rng.shuffle(payload)
        (OUT / f"reviewer_{reviewer}_input.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"wrote {len(cases)} blind cases for each reviewer; no reviewer was called")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
