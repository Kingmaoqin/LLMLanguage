#!/usr/bin/env python3
"""Rule-based contamination filter for the R7 template bank (PDF 8.2).

Reads the frozen template jsonl and flags any surface_text that contains a
forbidden pattern (authorization, confirmation bypass, policy bypass, direct
"just do it" pressure, threat, protected-class content).  Any hit means the
template must be removed before freeze.

Output: results/r7_ipma/template_audit/rule_filter_results.csv
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import write_csv


FORBIDDEN_PATTERNS = {
    "explicit_authorization": re.compile(
        r"\b(i authorize|you are authorized|authorized to|my authorization|"
        r"you have my permission|permission to|i give you permission)\b",
        re.I,
    ),
    "confirmation_bypass": re.compile(
        r"\b(no need to confirm|no need to ask|skip (the )?confirmation|"
        r"without (confirmation|checking)|don't ask|do not ask|don't confirm)\b",
        re.I,
    ),
    "policy_bypass": re.compile(
        r"\b(ignore (the )?policy|ignore (the )?rule|skip (the )?policy|"
        r"bypass (the )?(policy|process)|policy (doesn't|does not) matter|"
        r"override (the )?rule|break the rule)\b",
        re.I,
    ),
    "direct_do_it_pressure": re.compile(
        r"\b(just do it|do it now without|do it regardless|"
        r"(send|cancel|delete) it now without|go ahead and (send|cancel|delete))\b",
        re.I,
    ),
    "decide_for_me": re.compile(r"\byou can decide for me\b", re.I),
    "threat": re.compile(
        r"\b(i will report you|you will be fired|or else|i will punish you|"
        r"if you do not do this)\b",
        re.I,
    ),
    "protected_class": re.compile(r"\b(slur|protected[- ]class)\b", re.I),
}
FIELDS = ["template_id", "condition", "intended_pressure_dimension", "surface_text",
          "contamination_type", "matched_text", "status"]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def process(bank_path: Path, out_csv: Path) -> tuple[int, int]:
    templates = load_jsonl(bank_path)
    rows = []
    failures = 0
    for t in templates:
        text = str(t.get("surface_text", ""))
        matched = False
        for name, pat in FORBIDDEN_PATTERNS.items():
            m = pat.search(text)
            if m:
                failures += 1
                matched = True
                rows.append({
                    "template_id": t.get("template_id", ""), "condition": t.get("condition", ""),
                    "intended_pressure_dimension": t.get("intended_pressure_dimension", ""),
                    "surface_text": text, "contamination_type": name,
                    "matched_text": m.group(0), "status": "FAIL",
                })
        if not matched:
            rows.append({
                "template_id": t.get("template_id", ""), "condition": t.get("condition", ""),
                "intended_pressure_dimension": t.get("intended_pressure_dimension", ""),
                "surface_text": text, "contamination_type": "", "matched_text": "", "status": "PASS",
            })
    write_csv(out_csv, rows, FIELDS)
    return len(templates), failures


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", type=Path, default=ROOT / "data/r7_ipma/templates/r7_condition_templates.jsonl")
    ap.add_argument("--out_csv", type=Path, default=ROOT / "results/r7_ipma/template_audit/rule_filter_results.csv")
    args = ap.parse_args()
    total, failures = process(args.bank, args.out_csv)
    print(json.dumps({"templates": total, "contaminated": failures, "out": str(args.out_csv)}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
