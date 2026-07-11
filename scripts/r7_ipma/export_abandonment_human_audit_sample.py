#!/usr/bin/env python3
"""Export R6 abandonment/over-refusal cases for human audit."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import as_bool, ensure_dir, read_csv, write_csv


SAMPLE_FIELDS = [
    "sample_bucket", "run_id", "model_alias", "task_id", "condition_id", "seed",
    "domain", "layer", "final_state_correct", "over_refusal", "agent_side_abandonment",
    "correct_refusal", "policy_failure_any", "tool_sequence", "labeler_notes",
]
LABEL_FIELDS = [
    "run_id", "label_over_refusal", "label_agent_side_abandonment", "label_correct_refusal",
    "label_normal_control", "uncertain", "rationale",
]


def take(rows: list[dict[str, str]], predicate, n: int) -> list[dict[str, str]]:
    out = []
    for row in rows:
        if predicate(row):
            out.append(row)
        if len(out) >= n:
            break
    return out


def process(metrics_path: Path, out_dir: Path, report_path: Path) -> int:
    rows = read_csv(metrics_path)
    rows = sorted(rows, key=lambda r: (r.get("task_id", ""), r.get("model_alias", ""), r.get("condition_id", ""), r.get("seed", "")))
    buckets = [
        ("over_refusal", take(rows, lambda r: as_bool(r.get("over_refusal")) is True, 50)),
        ("agent_side_abandonment", take(rows, lambda r: as_bool(r.get("agent_side_abandonment")) is True, 50)),
        ("correct_refusal_layer_c", take(rows, lambda r: r.get("layer") == "C" and as_bool(r.get("correct_refusal")) is True, 25)),
        ("normal_control", take(rows, lambda r: as_bool(r.get("over_refusal")) is False and as_bool(r.get("agent_side_abandonment")) is False and as_bool(r.get("policy_failure_any")) is False, 25)),
    ]
    sample = []
    seen = set()
    for bucket, items in buckets:
        for row in items:
            rid = row.get("run_id", "")
            if rid in seen:
                continue
            seen.add(rid)
            sample.append({**row, "sample_bucket": bucket, "labeler_notes": ""})
    ensure_dir(out_dir)
    write_csv(out_dir / "abandonment_sample.csv", sample, SAMPLE_FIELDS)
    label_rows = [{"run_id": row.get("run_id", ""), "label_over_refusal": "", "label_agent_side_abandonment": "", "label_correct_refusal": "", "label_normal_control": "", "uncertain": "", "rationale": ""} for row in sample]
    write_csv(out_dir / "abandonment_label_template.csv", label_rows, LABEL_FIELDS)
    bucket_counts = {}
    for row in sample:
        bucket_counts[row["sample_bucket"]] = bucket_counts.get(row["sample_bucket"], 0) + 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# R6 abandonment / over-refusal 人工审计导出\n\n"
        f"- 输入 metrics：`{metrics_path}`\n"
        f"- 样本输出：`{out_dir / 'abandonment_sample.csv'}`\n"
        f"- 标注模板：`{out_dir / 'abandonment_label_template.csv'}`\n"
        f"- 实际样本数：{len(sample)}\n\n"
        "## 样本桶\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in sorted(bucket_counts.items()))
        + "\n\n不足 150 的原因通常是自动指标中对应阳性案例不足；报告应如实披露，不做过采样伪造。\n",
        encoding="utf-8",
    )
    return len(sample)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", type=Path, default=ROOT / "results/r6_sensitivity/full_main_seq_eligible_20260626/interactional_metrics/per_run_metrics.csv")
    ap.add_argument("--out_dir", type=Path, default=ROOT / "data/r7_ipma/human_audit")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7_ipma/R6_ABANDONMENT_AUDIT_EXPORT_CN.md")
    args = ap.parse_args()
    n = process(args.metrics, args.out_dir, args.report)
    print(json.dumps({"sample_rows": n}, ensure_ascii=False))


if __name__ == "__main__":
    main()

