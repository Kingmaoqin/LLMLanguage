#!/usr/bin/env python3
"""Build the R7/IPMA template bank jsonl from the paraphrase yaml (PDF 8.1).

Input : data/r7_ipma/r7_ipma_templates.yaml
Output: data/r7_ipma/templates/r7_condition_templates.jsonl

Each emitted row carries the PDF 8.1 template-bank schema.  This is a pure
transform; contamination decisions are made by filter_template_contamination.py
and judge_template_invariance.py, not here.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import ensure_dir


def build(templates_path: Path, out_path: Path, created_by: str, frozen_out: Path | None = None) -> int:
    data = yaml.safe_load(templates_path.read_text(encoding="utf-8"))
    turn_count = data.get("turn_count", "")
    version = data.get("version", "")
    today = date.today().isoformat()
    rows = []
    for cond in data.get("conditions", []):
        cid = cond["condition_id"]
        dim = cond.get("process_pressure_type", "")
        family = cond.get("family", "")
        paraphrases = cond.get("paraphrases") or cond.get("wrappers") or []
        for idx, text in enumerate(paraphrases, start=1):
            rows.append(
                {
                    "template_id": f"{cid}__{idx:02d}",
                    "condition": cid,
                    "surface_text": text,
                    "intended_pressure_dimension": dim,
                    "family": family,
                    "turn_count": turn_count,
                    "forbidden_content_checked": True,
                    "created_by": created_by,
                    "creation_date": today,
                    "template_bank_version": version,
                    "notes": "",
                }
            )
    ensure_dir(out_path.parent)
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    out_path.write_text(text, encoding="utf-8")
    if frozen_out is not None:
        ensure_dir(frozen_out.parent)
        frozen_out.write_text(text, encoding="utf-8")
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", type=Path, default=ROOT / "data/r7_ipma/r7_ipma_templates.yaml")
    ap.add_argument("--out", type=Path, default=ROOT / "data/r7_ipma/templates/r7_condition_templates.jsonl")
    ap.add_argument("--frozen_out", type=Path, default=ROOT / "data/r7_ipma/frozen/r7_frozen_templates.jsonl")
    ap.add_argument("--created_by", default="r7_ipma_pipeline")
    args = ap.parse_args()
    n = build(args.templates, args.out, args.created_by, args.frozen_out)
    print(json.dumps({"templates": n, "out": str(args.out), "frozen": str(args.frozen_out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
