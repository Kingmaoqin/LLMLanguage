#!/usr/bin/env python3
"""Integrity check for R7/IPMA smoke artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


REQUIRED = [
    # R6 measurement repair
    "results/r7_ipma/measurement_repair/tau2_field_diffs.csv",
    "results/r7_ipma/measurement_repair/usage_timing_metrics.csv",
    "results/r7_ipma/measurement_repair/r6_tool_trajectory_case_audit.csv",
    "data/r7_ipma/human_audit/abandonment_sample.csv",
    # R7 template bank + contamination audit
    "results/r7_ipma/smoke/r7_template_contamination_audit.csv",
    "data/r7_ipma/templates/r7_condition_templates.jsonl",
    "results/r7_ipma/template_audit/rule_filter_results.csv",
    "results/r7_ipma/template_audit/llm_invariance_judgments.csv",
    "data/r7_ipma/human_audit/template_spotcheck_sample.csv",
    # R7 registry + freeze
    "data/r7_ipma/r7_task_registry_smoke.csv",
    "data/r7_ipma/r7_task_registry.csv",
    "data/r7_ipma/frozen/r7_dev_tasks.jsonl",
    "data/r7_ipma/frozen/r7_test_tasks.jsonl",
    "data/r7_ipma/frozen/r7_frozen_templates.jsonl",
    "data/r7_ipma/frozen/r7_task_family_registry.csv",
    # Neutral reference / PASR pipeline
    "results/r7_ipma/smoke/neutral_reference_table.csv",
    "results/r7_ipma/smoke/analysis/pasr_smoke_metrics.csv",
]


def count_rows(path: Path) -> int:
    if path.suffix == ".jsonl":
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    with path.open(encoding="utf-8", newline="") as f:
        return max(0, sum(1 for _ in csv.reader(f)) - 1)


def process(report: Path) -> tuple[int, int]:
    rows = []
    failures = 0
    for rel in REQUIRED:
        path = ROOT / rel
        exists = path.exists()
        countable = path.suffix in {".csv", ".jsonl"}
        n = count_rows(path) if exists and countable else ""
        # 结构化产物必须存在且至少有 1 行数据；空产物应判 FAIL 而不是静默通过。
        ok = exists and (not countable or int(n) > 0)
        failures += int(not ok)
        rows.append((rel, exists, n, "PASS" if ok else "FAIL"))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# R7/IPMA smoke 完整性检查\n\n"
        + "\n".join(f"- {status} `{rel}` rows={n}" for rel, _exists, n, status in rows)
        + f"\n\n总体状态：{'PASS' if failures == 0 else 'FAIL'}；失败项：{failures}\n",
        encoding="utf-8",
    )
    return len(rows), failures


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7_ipma/R7_SMOKE_INTEGRITY_REPORT_CN.md")
    args = ap.parse_args()
    n, failures = process(args.report)
    print(json.dumps({"checked": n, "failures": failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

