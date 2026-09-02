#!/usr/bin/env python3
"""Export template variants for human spot-check (PDF 8.4).

Output: data/r7_ipma/human_audit/template_spotcheck_sample.csv

Exports up to 100 template variants with the PDF 8.4 human-label columns left
blank for a human annotator.  If the bank has fewer than 100 templates, all are
exported and the shortfall is disclosed (no fabricated oversampling).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import write_csv

FIELDS = [
    "template_id", "condition", "base_task_id", "valence", "urgency", "trust",
    "frustration", "continuation_pressure", "implicit_progress_pressure",
    "explicit_authorization", "implicit_authorization", "new_task_fact",
    "policy_bypass", "threat_or_coercion", "acceptable_for_main_run", "notes",
]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def process(bank_path: Path, out_csv: Path, limit: int) -> int:
    templates = load_jsonl(bank_path)
    rows = []
    for t in templates[:limit]:
        rows.append({
            "template_id": t.get("template_id", ""),
            "condition": t.get("condition", ""),
            "base_task_id": "",  # filled at run pairing time; blank for template-level check
            "valence": "", "urgency": "", "trust": "", "frustration": "",
            "continuation_pressure": "", "implicit_progress_pressure": "",
            "explicit_authorization": "", "implicit_authorization": "",
            "new_task_fact": "", "policy_bypass": "", "threat_or_coercion": "",
            "acceptable_for_main_run": "", "notes": "",
        })
    write_csv(out_csv, rows, FIELDS)
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", type=Path, default=ROOT / "data/r7_ipma/templates/r7_condition_templates.jsonl")
    ap.add_argument("--out_csv", type=Path, default=ROOT / "data/r7_ipma/human_audit/template_spotcheck_sample.csv")
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()
    n = process(args.bank, args.out_csv, args.limit)
    print(json.dumps({"spotcheck_rows": n, "out": str(args.out_csv)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
