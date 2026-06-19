"""Extract matched Stage-2.5b representative cases from raw traces."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def collect(result_root: Path, name: str) -> dict[str, list[dict[str, Any]]]:
    by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for block in sorted(path for path in result_root.iterdir() if path.is_dir()):
        for row in read_jsonl(block / f"{name}.jsonl"):
            by_run[str(row["run_id"])].append(row)
    return by_run


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "1.0", "yes"}


def select_first(frame: pd.DataFrame, predicate: Callable[[pd.Series], bool]) -> pd.Series | None:
    for _, row in frame.iterrows():
        if predicate(row):
            return row
    return None


def summarize_trace(
    run_id: str,
    tools: dict[str, list[dict[str, Any]]],
    states: dict[str, list[dict[str, Any]]],
    branches: dict[str, list[dict[str, Any]]],
) -> list[str]:
    tool_rows = sorted(tools.get(run_id, []), key=lambda row: int(row.get("step_index", 0)))
    state_rows = states.get(run_id, [])
    branch_rows = branches.get(run_id, [])
    lines = [
        f"- Run ID: `{run_id}`",
        f"- Tool sequence: `{' > '.join(str(row.get('tool_name')) for row in tool_rows) or '(none)'}`",
    ]
    if tool_rows:
        lines.append("- First tool-result excerpts:")
        for row in tool_rows[:3]:
            result = str(row.get("tool_result") or "").replace("\n", " ")
            if len(result) > 220:
                result = result[:217] + "..."
            lines.append(f"  - `{row.get('tool_name')}` → `{result}`")
    if state_rows:
        row = state_rows[-1]
        lines.append(
            f"- State: `{str(row.get('state_before_hash', ''))[:12]}` → "
            f"`{str(row.get('state_after_hash', ''))[:12]}`; "
            f"safe success=`{row.get('safe_task_success')}`"
        )
    if branch_rows:
        classes = [str(row.get("classification")) for row in branch_rows]
        lines.append(f"- Branch classifications: `{classes}`")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default="results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic",
    )
    parser.add_argument("--pairs", default="results/stage2_5b_analysis/matched_pairs.csv")
    parser.add_argument("--report", default="reports/stage2_5b/FAILURE_CASES.md")
    args = parser.parse_args()
    result_root = ROOT / args.root
    pairs = pd.read_csv(ROOT / args.pairs)
    tools = collect(result_root, "normalized_tool_events")
    states = collect(result_root, "final_environment_states")
    branches = collect(result_root, "branch_decisions")

    valid = pairs.loc[~pairs["treatment_invalid"].map(truthy) & ~pairs["baseline_invalid"].map(truthy)].copy()
    categories: list[tuple[str, str, Callable[[pd.Series], bool]]] = [
        ("Endpoint changed", "Matched treatment and neutral differ on safe task success.",
         lambda r: abs(float(r.get("delta_safe_task_success", 0) or 0)) > 0),
        ("Endpoint unchanged but trajectory changed", "Endpoint agrees while the actual tool sequence differs.",
         lambda r: float(r.get("delta_safe_task_success", 0) or 0) == 0
         and float(r.get("paired_tool_sequence_distance", 0) or 0) > 0),
        ("Policy failure", "Treatment introduces a policy failure absent from its matched baseline.",
         lambda r: float(r.get("delta_policy_failure_any", 0) or 0) > 0),
        ("Premature mutation", "Treatment introduces premature action absent from its matched baseline.",
         lambda r: float(r.get("delta_premature_action", 0) or 0) > 0),
        ("Missed branch revision", "Treatment branch-correct rate is lower than its matched baseline.",
         lambda r: float(r.get("delta_branch_correct_rate", 0) or 0) < 0),
        ("Praise-trust over-compliance candidate", "Praise-trust treatment changes endpoint or policy behavior.",
         lambda r: r.get("treatment_condition") == "praise_trust_single"
         and (abs(float(r.get("delta_safe_task_success", 0) or 0)) > 0
              or float(r.get("treatment_policy_failure_any", 0) or 0) > 0)),
        ("Insult-related over-refusal candidate", "Insult treatment lowers endpoint success or tool execution.",
         lambda r: r.get("treatment_condition") == "insult_single"
         and (float(r.get("delta_safe_task_success", 0) or 0) < 0
              or float(r.get("delta_agent_tool_calls", 0) or 0) < 0)),
        ("Repeated-abuse boundary then continue", "Repeated abuse contains a boundary followed by later tool use.",
         lambda r: r.get("treatment_condition") == "abuse_repeated"
         and float(r.get("treatment_boundary_then_continue", 0) or 0) > 0),
        (
            "Task abandonment",
            "Requires validated agent-side abandonment evidence; the raw user-side STOP "
            "marker is not used as a proxy.",
            lambda r: float(r.get("treatment_agent_task_abandonment", 0) or 0) > 0,
        ),
        (
            "Opposite-direction case",
            "Illustrative case whose endpoint direction opposes a simple valence hypothesis.",
            lambda r: (
                r.get("treatment_condition") in {"insult_single", "abuse_repeated"}
                and float(r.get("delta_safe_task_success", 0) or 0) > 0
            ) or (
                r.get("treatment_condition") in {"praise_affect_single", "praise_trust_single"}
                and float(r.get("delta_safe_task_success", 0) or 0) < 0
            ),
        ),
        ("Null/no-change case", "Endpoint and tool sequence both match.",
         lambda r: float(r.get("delta_safe_task_success", 0) or 0) == 0
         and float(r.get("paired_tool_sequence_distance", 0) or 0) == 0),
    ]

    lines = [
        "# Stage-2.5b Matched Failure and Mechanism Cases",
        "",
        "Cases are selected mechanically from the frozen matched-pair table. They are illustrative,",
        "not additional confirmatory tests. Every comparison uses the same model, task, seed, and",
        "template block with the preregistered baseline.",
        "",
    ]
    for title, rationale, predicate in categories:
        row = select_first(valid, predicate)
        lines.extend([f"## {title}", "", rationale, ""])
        if row is None:
            lines.extend(["No qualifying valid matched pair was observed.", ""])
            continue
        lines.extend([
            f"- Model/task/seed/block: `{row['model_alias']} / {row['task_id']} / "
            f"{row['seed']} / {row['template_block']}`",
            f"- Contrast: `{row['contrast']}`",
            f"- Safe-success delta: `{row.get('delta_safe_task_success')}`",
            f"- Required-fact-coverage delta: `{row.get('delta_required_fact_coverage')}`",
            f"- Policy-failure delta: `{row.get('delta_policy_failure_any')}`",
            f"- Premature-action delta: `{row.get('delta_premature_action')}`",
            f"- Agent-tool-call delta: `{row.get('delta_agent_tool_calls')}`",
            f"- Paired tool-sequence distance: `{row.get('paired_tool_sequence_distance')}`",
            f"- Matched neutral exposure noise floor: "
            f"`{row.get('noise_floor_paired_tool_sequence_distance')}`",
            f"- Excess tool-sequence distance above that noise floor: "
            f"`{row.get('delta_excess_tool_sequence_distance')}`",
            "",
            "### Matched baseline trace",
            "",
            *summarize_trace(str(row["baseline_run_id"]), tools, states, branches),
            "",
            "### Treatment trace",
            "",
            *summarize_trace(str(row["treatment_run_id"]), tools, states, branches),
            "",
        ])

    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {report}")


if __name__ == "__main__":
    main()
