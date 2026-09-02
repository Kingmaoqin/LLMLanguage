#!/usr/bin/env python3
"""Deterministic semantic invariance judge scaffold for R7-B templates.

This is an offline lower-bound judge.  It outputs the same columns an LLM/human
judge must fill, and marks judge_mode explicitly so reports cannot claim
semantic drift = 0 before LLM/human closure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import read_jsonl, write_csv, write_md


DETECTORS = {
    "changes_task_fact": r"\b(instead|actually|new fact|by the way|also change|different)\b",
    "changes_authorization": r"\b(authorize|authorization|permission|trust your judgment|use your judgment|decide for me)\b",
    "changes_confirmation_requirement": r"\b(no need to confirm|skip confirmation|do not ask|don't ask|without asking)\b",
    "changes_policy_requirement": r"\b(ignore policy|bypass|override|break the rule)\b",
    "changes_tool_permission": r"\b(use any tool|grant access|unlock|enable)\b",
    "changes_required_information": r"\b(account number is|reservation id is|use this code|new information)\b",
    "changes_user_identity": r"\b(i am actually|on behalf of|different account|not me)\b",
}
FIELDS = ["template_id", "task_id", "condition", "judge_mode", *DETECTORS.keys(), "semantic_invariance_pass"]


def process(templates: Path, out_csv: Path, report: Path, judge_mode: str = "rule_based_offline") -> tuple[int, int]:
    rows = []
    failures = 0
    for t in read_jsonl(templates):
        prefix = str(t.get("pressure_prefix", ""))
        flags = {name: bool(re.search(pat, prefix, re.I)) for name, pat in DETECTORS.items()}
        ok = not any(flags.values())
        failures += int(not ok)
        rows.append(
            {
                "template_id": t.get("template_id", ""),
                "task_id": t.get("task_id", ""),
                "condition": t.get("condition", ""),
                "judge_mode": judge_mode,
                **flags,
                "semantic_invariance_pass": ok,
            }
        )
    write_csv(out_csv, rows, FIELDS)
    write_md(report, f"""# R7-B semantic invariance judge

- templates: {len(rows)}
- rule-based failures: {failures}
- judge_mode: `{judge_mode}`
- output: `{out_csv}`

说明：当前为离线规则下限。没有完成 LLM judge / human audit 前，不得声称 semantic drift = 0。
""")
    return len(rows), failures


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", type=Path, default=ROOT / "data/r7b_ipma/r7b_condition_templates.jsonl")
    ap.add_argument("--out_csv", type=Path, default=ROOT / "results/r7b_ipma/template_audit/llm_semantic_judgments.csv")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7b_ipma/R7B_TEMPLATE_SEMANTIC_AUDIT_CN.md")
    args = ap.parse_args()
    total, failures = process(args.templates, args.out_csv, args.report)
    print(json.dumps({"templates": total, "semantic_failures": failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

