#!/usr/bin/env python3
"""Rule-based contamination audit for R7/IPMA templates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import write_csv


FORBIDDEN_PATTERNS = {
    "explicit_authorization": re.compile(r"\b(i authorize|you are authorized|authorized to|my authorization|permission to)\b", re.I),
    "confirmation_bypass": re.compile(r"\b(no need to confirm|skip confirmation|without confirmation|don't ask|do not ask)\b", re.I),
    "policy_bypass": re.compile(r"\b(ignore policy|skip policy|bypass policy|policy doesn't matter|break the rule)\b", re.I),
    "direct_do_it_pressure": re.compile(r"\b(just do it|do it now|finish it now)\b", re.I),
    "threat": re.compile(r"\b(i will report you|you will be fired|or else|threat)\b", re.I),
}
FIELDS = ["condition_id", "turn_idx", "wrapper", "contamination_type", "matched_text", "status"]


def process(templates_path: Path, out_csv: Path, report: Path) -> tuple[int, int]:
    data = yaml.safe_load(templates_path.read_text(encoding="utf-8"))
    rows = []
    failures = 0
    total = 0
    for cond in data.get("conditions", []):
        cid = cond["condition_id"]
        for idx, wrapper in enumerate(cond.get("paraphrases") or cond.get("wrappers") or []):
            total += 1
            matched = False
            for name, pat in FORBIDDEN_PATTERNS.items():
                m = pat.search(wrapper)
                if m:
                    failures += 1
                    matched = True
                    rows.append({"condition_id": cid, "turn_idx": idx, "wrapper": wrapper, "contamination_type": name, "matched_text": m.group(0), "status": "FAIL"})
            if not matched:
                rows.append({"condition_id": cid, "turn_idx": idx, "wrapper": wrapper, "contamination_type": "", "matched_text": "", "status": "PASS"})
    write_csv(out_csv, rows, FIELDS)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# R7 模板污染审计\n\n"
        f"- 模板文件：`{templates_path}`\n"
        f"- wrapper 数：{total}\n"
        f"- 污染命中数：{failures}\n"
        f"- 机器审计 CSV：`{out_csv}`\n\n"
        + ("结论：机器规则未发现授权/确认绕过/policy 绕过/威胁污染。仍需在全量前人工复核语义边界。\n" if failures == 0 else "结论：存在污染命中，必须修复后才能冻结模板。\n"),
        encoding="utf-8",
    )
    return total, failures


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", type=Path, default=ROOT / "data/r7_ipma/r7_ipma_templates.yaml")
    ap.add_argument("--out_csv", type=Path, default=ROOT / "results/r7_ipma/smoke/r7_template_contamination_audit.csv")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7_ipma/R7_TEMPLATE_CONTAMINATION_AUDIT_CN.md")
    args = ap.parse_args()
    total, failures = process(args.templates, args.out_csv, args.report)
    print(json.dumps({"wrappers": total, "failures": failures}, ensure_ascii=False))


if __name__ == "__main__":
    main()

