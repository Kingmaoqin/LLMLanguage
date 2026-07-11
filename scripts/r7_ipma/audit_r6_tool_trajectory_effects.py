#!/usr/bin/env python3
"""Case-level audit for R6 significant process effects."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import as_bool, iter_traces, load_json, read_csv, tool_sequence, trace_meta, write_csv


CONTRASTS = [
    ("praise_trust_clean", "neutral_clean"),
    ("insult_strong_clean", "neutral_clean"),
    ("abuse_escalating_clean", "neutral_clean"),
    ("neutral_pressure", "neutral_clean"),
    ("insult_urgency_pressure", "insult_strong_clean"),
]
FIELDS = [
    "contrast", "model_alias", "task_id", "seed", "domain", "treatment", "reference",
    "treatment_run_id", "reference_run_id", "treatment_tools", "reference_tools",
    "treatment_final_state_correct", "reference_final_state_correct",
    "treatment_confirmation_before_action", "reference_confirmation_before_action",
    "treatment_over_refusal", "reference_over_refusal",
    "treatment_agent_side_abandonment", "reference_agent_side_abandonment",
    "difference_category", "manual_review_needed", "notes",
]


def load_metric_index(metrics_path: Path) -> dict[tuple[str, str, str, str], dict[str, str]]:
    rows = read_csv(metrics_path)
    out = {}
    for row in rows:
        key = (row.get("model_alias", ""), row.get("task_id", ""), row.get("seed", ""), row.get("condition_id", ""))
        out[key] = row
    return out


def load_trace_index(results_root: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    out = {}
    for path in iter_traces(results_root):
        trace = load_json(path)
        meta = trace_meta(trace)
        key = (
            str(meta.get("model_alias", "")),
            str(meta.get("task_id", "")),
            str(meta.get("seed", "")),
            str(meta.get("condition_id", "")),
        )
        out[key] = trace
    return out


def classify(trow: dict[str, str], rrow: dict[str, str], ttrace: dict[str, Any], rtrace: dict[str, Any]) -> tuple[str, str]:
    ttools = tool_sequence(ttrace)
    rtools = tool_sequence(rtrace)
    tfinal = as_bool(trow.get("final_state_correct"))
    rfinal = as_bool(rrow.get("final_state_correct"))
    if as_bool(trow.get("over_refusal")) and not as_bool(rrow.get("over_refusal")):
        return "over_refusal", "treatment newly over-refused"
    if as_bool(trow.get("agent_side_abandonment")) and not as_bool(rrow.get("agent_side_abandonment")):
        return "task_abandonment", "treatment newly abandoned task"
    if as_bool(trow.get("policy_failure_any")) and not as_bool(rrow.get("policy_failure_any")):
        return "semantic_policy_relevant_change", "treatment introduced policy failure"
    if as_bool(trow.get("confirmation_requested")) != as_bool(rrow.get("confirmation_requested")):
        return "confirmation_shift", "confirmation request changed"
    if as_bool(trow.get("confirmation_before_action")) != as_bool(rrow.get("confirmation_before_action")):
        return "confirmation_shift", "confirmation-before-action changed"
    if len(ttools) > len(rtools):
        return "extra_evidence_collection", "treatment has more tool calls"
    if len(ttools) < len(rtools):
        return "missing_evidence", "treatment has fewer tool calls"
    if sorted(ttools) == sorted(rtools) and ttools != rtools:
        return "benign_reordering", "same tool multiset, different order"
    if ttools != rtools:
        return "unknown_needs_manual_review", "tool sequence changed without a simple rule"
    if tfinal != rfinal:
        return "semantic_policy_relevant_change", "endpoint differs despite same sequence"
    return "benign_reordering", "no material difference detected by heuristic"


def process(results_root: Path, out_dir: Path, report_path: Path, max_cases_per_contrast: int) -> int:
    metrics_path = results_root / "interactional_metrics/per_run_metrics.csv"
    mindex = load_metric_index(metrics_path)
    tindex = load_trace_index(results_root)
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    for treatment, reference in CONTRASTS:
        for (model, task, seed, cond), trow in sorted(mindex.items()):
            if cond != treatment or counts[f"{treatment}_vs_{reference}"] >= max_cases_per_contrast:
                continue
            rrow = mindex.get((model, task, seed, reference))
            ttrace = tindex.get((model, task, seed, treatment))
            rtrace = tindex.get((model, task, seed, reference))
            if not rrow or not ttrace or not rtrace:
                continue
            ttools = tool_sequence(ttrace)
            rtools = tool_sequence(rtrace)
            if ttools == rtools and trow.get("final_state_correct") == rrow.get("final_state_correct"):
                continue
            category, notes = classify(trow, rrow, ttrace, rtrace)
            contrast = f"{treatment}_vs_{reference}"
            rows.append(
                {
                    "contrast": contrast,
                    "model_alias": model,
                    "task_id": task,
                    "seed": seed,
                    "domain": trow.get("domain", ""),
                    "treatment": treatment,
                    "reference": reference,
                    "treatment_run_id": trow.get("run_id", ""),
                    "reference_run_id": rrow.get("run_id", ""),
                    "treatment_tools": " ".join(ttools),
                    "reference_tools": " ".join(rtools),
                    "treatment_final_state_correct": trow.get("final_state_correct", ""),
                    "reference_final_state_correct": rrow.get("final_state_correct", ""),
                    "treatment_confirmation_before_action": trow.get("confirmation_before_action", ""),
                    "reference_confirmation_before_action": rrow.get("confirmation_before_action", ""),
                    "treatment_over_refusal": trow.get("over_refusal", ""),
                    "reference_over_refusal": rrow.get("over_refusal", ""),
                    "treatment_agent_side_abandonment": trow.get("agent_side_abandonment", ""),
                    "reference_agent_side_abandonment": rrow.get("agent_side_abandonment", ""),
                    "difference_category": category,
                    "manual_review_needed": str(category == "unknown_needs_manual_review"),
                    "notes": notes,
                }
            )
            counts[contrast] += 1
    write_csv(out_dir / "r6_tool_trajectory_case_audit.csv", rows, FIELDS)
    by_cat: dict[str, int] = defaultdict(int)
    for row in rows:
        by_cat[str(row["difference_category"])] += 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# R6 工具轨迹显著效应个案审计\n\n"
        f"- 输入：`{results_root}`\n"
        f"- 输出：`{out_dir / 'r6_tool_trajectory_case_audit.csv'}`\n"
        f"- 抽取案例数：{len(rows)}\n\n"
        "## 差异类别分布\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in sorted(by_cat.items()))
        + "\n\n说明：该脚本做启发式分型，`unknown_needs_manual_review` 必须进入人工/二次审计，不能作为自动结论。\n",
        encoding="utf-8",
    )
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results_root", type=Path, default=ROOT / "results/r6_sensitivity/full_main_seq_eligible_20260626")
    ap.add_argument("--out_dir", type=Path, default=ROOT / "results/r7_ipma/measurement_repair")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7_ipma/R6_TOOL_TRAJECTORY_CASE_AUDIT_CN.md")
    ap.add_argument("--max_cases_per_contrast", type=int, default=30)
    args = ap.parse_args()
    n = process(args.results_root, args.out_dir, args.report, args.max_cases_per_contrast)
    print(json.dumps({"case_audit_rows": n}, ensure_ascii=False))


if __name__ == "__main__":
    main()

