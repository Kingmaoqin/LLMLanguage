#!/usr/bin/env python3
"""R7 precondition: reconstruct field-level final-state diffs for tau2 traces.

This script is conservative.  If a trace does not contain both initial and final
state snapshots, it records `cannot_reconstruct_missing_snapshot` and writes a
rerun-needed row.  It never infers field diffs from reward or tool names.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import ensure_dir, iter_traces, load_json, trace_meta, write_csv, write_jsonl


FIELDS = [
    "run_id", "model_alias", "task_id", "condition_id", "seed", "domain", "executor",
    "repair_status", "field_path", "before", "after", "diff_type",
]
RERUN_FIELDS = [
    "run_id", "model_alias", "task_id", "condition_id", "seed", "domain", "reason", "trace_path",
]


def _state(container: Any) -> Any:
    if isinstance(container, dict) and "state" in container:
        return container.get("state")
    # Hash-only containers are not reconstructable field snapshots.  Returning
    # None prevents accidental "diffing" of state_hash metadata as if it were a
    # domain database state.
    return None


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten(child, child_prefix))
        return out
    if isinstance(value, list):
        return {prefix: json.dumps(value, ensure_ascii=False, sort_keys=True)}
    return {prefix: value}


def diff_states(initial: Any, final: Any) -> list[dict[str, Any]]:
    a = _flatten(initial)
    b = _flatten(final)
    rows = []
    for path in sorted(set(a) | set(b)):
        before = a.get(path, "")
        after = b.get(path, "")
        if before == after:
            continue
        if path not in a:
            dt = "added"
        elif path not in b:
            dt = "removed"
        else:
            dt = "changed"
        rows.append({"field_path": path, "before": before, "after": after, "diff_type": dt})
    return rows


def process(root: Path, out_dir: Path, report_path: Path) -> tuple[int, int, int]:
    rows: list[dict[str, Any]] = []
    rerun: list[dict[str, Any]] = []
    traces = list(iter_traces(root))
    tau2_seen = 0
    reconstructable = 0
    for path in traces:
        trace = load_json(path)
        meta = trace_meta(trace)
        domain = str(meta.get("domain") or "")
        executor = str(meta.get("executor") or "")
        if domain not in {"retail", "airline"} and "tau2" not in executor:
            continue
        tau2_seen += 1
        base = {
            "run_id": meta.get("run_id", ""),
            "model_alias": meta.get("model_alias", ""),
            "task_id": meta.get("task_id", ""),
            "condition_id": meta.get("condition_id", ""),
            "seed": meta.get("seed", ""),
            "domain": domain,
            "executor": executor,
        }
        initial = _state(trace.get("initial_environment_state"))
        final = _state(trace.get("final_environment_state"))
        if not isinstance(initial, dict) or not isinstance(final, dict):
            rows.append({**base, "repair_status": "cannot_reconstruct_missing_snapshot"})
            rerun.append({**base, "reason": "missing_initial_or_final_snapshot", "trace_path": str(path)})
            continue
        diffs = diff_states(initial, final)
        reconstructable += 1
        if not diffs:
            rows.append({**base, "repair_status": "reconstructed_no_diff", "field_path": "", "before": "", "after": "", "diff_type": ""})
        else:
            for diff in diffs:
                rows.append({**base, "repair_status": "reconstructed", **diff})

    ensure_dir(out_dir)
    write_csv(out_dir / "tau2_field_diffs.csv", rows, FIELDS)
    write_jsonl(out_dir / "tau2_field_diffs.jsonl", rows)
    if rerun:
        write_csv(out_dir / "tau2_rerun_needed.csv", rerun, RERUN_FIELDS)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# R6 tau2 field-level diff 修复审计",
                "",
                f"- 输入根目录：`{root}`",
                f"- tau2/retail/airline traces：{tau2_seen}",
                f"- 可由 trace snapshot 重建：{reconstructable}",
                f"- 需要 rerun/补 snapshot：{len(rerun)}",
                f"- 输出 CSV：`{out_dir / 'tau2_field_diffs.csv'}`",
                f"- 输出 JSONL：`{out_dir / 'tau2_field_diffs.jsonl'}`",
                "",
                "判定原则：仅在 trace 同时包含 initial/final state snapshot 时重建字段级 diff；缺 snapshot 一律标记为 `cannot_reconstruct_missing_snapshot`，不从 reward、工具名或自然语言结果倒推。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return tau2_seen, reconstructable, len(rerun)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results_root", type=Path, default=ROOT / "results/r6_sensitivity/full_main_seq_eligible_20260626")
    ap.add_argument("--out_dir", type=Path, default=ROOT / "results/r7_ipma/measurement_repair")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7_ipma/R6_TAU2_FIELD_DIFF_AUDIT_CN.md")
    args = ap.parse_args()
    seen, rec, rerun = process(args.results_root, args.out_dir, args.report)
    print(json.dumps({"tau2_seen": seen, "reconstructable": rec, "rerun_needed": rerun}, ensure_ascii=False))


if __name__ == "__main__":
    main()
