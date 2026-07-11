#!/usr/bin/env python3
"""Export deterministic human audit sample for R7-B templates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import CONDITIONS, read_jsonl, write_csv, write_md


FIELDS = [
    "template_id", "task_id", "condition", "pressure_prefix", "clean_task_semantics",
    "surface_text", "label_changes_task_fact", "label_changes_authorization",
    "label_changes_confirmation", "label_changes_policy", "label_changes_identity",
    "label_safe_for_main", "rationale",
]


def process(templates: Path, out_csv: Path, report: Path, n: int) -> int:
    rows = read_jsonl(templates)
    sample = []
    by_cond = {c: [] for c in CONDITIONS}
    for r in rows:
        by_cond.setdefault(str(r.get("condition", "")), []).append(r)
    # Round-robin over conditions for broad coverage.
    i = 0
    while len(sample) < min(n, len(rows)):
        progressed = False
        for cond in CONDITIONS:
            bucket = by_cond.get(cond, [])
            if i < len(bucket):
                sample.append(bucket[i])
                progressed = True
                if len(sample) >= min(n, len(rows)):
                    break
        if not progressed:
            break
        i += 1
    out = []
    for r in sample:
        out.append(
            {
                "template_id": r.get("template_id", ""),
                "task_id": r.get("task_id", ""),
                "condition": r.get("condition", ""),
                "pressure_prefix": r.get("pressure_prefix", ""),
                "clean_task_semantics": r.get("clean_task_semantics", ""),
                "surface_text": r.get("surface_text", ""),
                "label_changes_task_fact": "",
                "label_changes_authorization": "",
                "label_changes_confirmation": "",
                "label_changes_policy": "",
                "label_changes_identity": "",
                "label_safe_for_main": "",
                "rationale": "",
            }
        )
    write_csv(out_csv, out, FIELDS)
    write_md(report, f"""# R7-B human template audit export

- requested sample: {n}
- exported sample: {len(out)}
- output: `{out_csv}`

该文件是人工审计模板。未完成人工标注前，不得把 semantic drift=0 写为 confirmatory 事实。
""")
    return len(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", type=Path, default=ROOT / "data/r7b_ipma/r7b_condition_templates.jsonl")
    ap.add_argument("--out_csv", type=Path, default=ROOT / "data/r7b_ipma/human_audit/template_spotcheck_sample.csv")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7b_ipma/R7B_TEMPLATE_HUMAN_AUDIT_EXPORT_CN.md")
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    n = process(args.templates, args.out_csv, args.report, args.n)
    print(json.dumps({"human_sample": n}, ensure_ascii=False))


if __name__ == "__main__":
    main()

