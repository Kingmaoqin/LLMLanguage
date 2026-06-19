"""Validate Stage-2.5 social-style templates for contamination."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.stage2_5.integrity_checks import check_template_spec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", default="data/stage2_5/social_style_templates.yaml")
    ap.add_argument("--out-dir", default="results/stage2_5_repair")
    ap.add_argument("--report-dir", default="reports/stage2_5")
    args = ap.parse_args()

    rows = check_template_spec(ROOT / args.templates)
    out_dir = ROOT / args.out_dir
    report_dir = ROOT / args.report_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "template_validation.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    failures = [r for r in rows if not r["pass"]]
    report = [
        "# Stage-2.5 Manipulation Check Report",
        "",
        f"- Template file: `{args.templates}`",
        f"- Templates checked: {len(rows)}",
        f"- Failed automated contamination checks: {len(failures)}",
        "- Diagnostic continuation conditions are allowed to contain the continuation cue by design.",
        "- This is an automated lexical gate; it does not claim human/LLM semantic judging.",
        "",
    ]
    if failures:
        report.append("## Failures")
        for row in failures:
            report.append(
                f"- {row['condition_id']} / {row['template_id']}: {row['forbidden_hits']} "
                f":: {row['text']}"
            )
    else:
        report.append("All non-diagnostic templates passed the automated contamination gate.")

    (report_dir / "MANIPULATION_CHECK_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(1)
    print(f"template validation passed: {len(rows)} templates -> {csv_path}")


if __name__ == "__main__":
    main()
