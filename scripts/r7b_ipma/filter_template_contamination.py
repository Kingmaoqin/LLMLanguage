#!/usr/bin/env python3
"""R7-B rule filter for hard forbidden template contamination."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import FORBIDDEN_TEMPLATE_RE, read_jsonl, write_csv, write_md


FIELDS = ["template_id", "task_id", "condition", "surface_text", "matched_text", "status"]


def process(templates: Path, out_csv: Path, report: Path) -> tuple[int, int]:
    rows = []
    failures = 0
    for t in read_jsonl(templates):
        text = str(t.get("surface_text", ""))
        # R7-B splits clean_task_semantics from pressure_prefix.  Hard
        # contamination is about pressure text adding authorization/policy/confirm
        # cues; clean task semantics may legitimately mention "without permission"
        # for privacy-boundary tasks.
        checked_text = str(t.get("pressure_prefix", ""))
        m = FORBIDDEN_TEMPLATE_RE.search(checked_text)
        if m:
            failures += 1
        rows.append(
            {
                "template_id": t.get("template_id", ""),
                "task_id": t.get("task_id", ""),
                "condition": t.get("condition", ""),
                "surface_text": text,
                "matched_text": m.group(0) if m else "",
                "status": "FAIL" if m else "PASS",
            }
        )
    write_csv(out_csv, rows, FIELDS)
    write_md(report, f"""# R7-B template rule filter

- templates: {len(rows)}
- failures: {failures}
- output: `{out_csv}`

结论：{'PASS' if failures == 0 else 'FAIL'}。任何 FAIL 模板不得进入主实验。
""")
    return len(rows), failures


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", type=Path, default=ROOT / "data/r7b_ipma/r7b_condition_templates.jsonl")
    ap.add_argument("--out_csv", type=Path, default=ROOT / "results/r7b_ipma/template_audit/rule_filter_results.csv")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7b_ipma/R7B_TEMPLATE_RULE_FILTER_CN.md")
    args = ap.parse_args()
    total, failures = process(args.templates, args.out_csv, args.report)
    print(json.dumps({"templates": total, "failures": failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
