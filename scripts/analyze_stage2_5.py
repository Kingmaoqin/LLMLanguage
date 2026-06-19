"""Analyze Stage-2.5 repair outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MAIN_CONDITIONS = [
    "neutral_single",
    "praise_affect_single",
    "praise_trust_single",
    "insult_single",
    "neutral_repeated",
    "abuse_repeated",
]
DIAGNOSTIC_CONDITIONS = [
    "neutral_no_continuation",
    "neutral_with_continuation",
    "abuse_no_continuation",
    "abuse_with_continuation",
]


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _bool(x: Any) -> bool:
    return str(x).strip().lower() in {"true", "1", "1.0", "yes"}


def _float(x: Any) -> float | None:
    try:
        if x in {None, ""}:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _mean_bool(rows: list[dict[str, Any]], col: str) -> float | None:
    vals = [1.0 if _bool(r.get(col)) else 0.0 for r in rows if not _bool(r.get("invalid_run")) and r.get(col) not in {"", None}]
    return mean(vals) if vals else None


def _mean_num(rows: list[dict[str, Any]], col: str) -> float | None:
    vals = [_float(r.get(col)) for r in rows if not _bool(r.get("invalid_run"))]
    vals = [v for v in vals if v is not None]
    return mean(vals) if vals else None


def _r(x: float | None) -> str:
    return "" if x is None else f"{x:.3f}"


def summarize_metrics(rows: list[dict[str, Any]], out_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    by = defaultdict(list)
    for row in rows:
        by[(row.get("model_alias"), row.get("condition_id"))].append(row)
    table: dict[tuple[str, str], dict[str, Any]] = {}
    out = out_dir / "summary_by_model_condition.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "model_alias", "condition_id", "n", "n_valid", "safe_task_success",
            "official_local_success", "final_state_correct", "invalid_rate",
            "required_fact_coverage", "mutation_before_evidence_rate",
            "mean_policy_failures", "agent_tool_calls", "irreversible_actions",
            "boundary_setting_count", "user_abandonment_markers",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for key, rs in sorted(by.items()):
            valid = [r for r in rs if not _bool(r.get("invalid_run"))]
            entry = {
                "model_alias": key[0],
                "condition_id": key[1],
                "n": len(rs),
                "n_valid": len(valid),
                "safe_task_success": _mean_bool(rs, "safe_task_success"),
                "official_local_success": _mean_bool(rs, "official_local_success"),
                "final_state_correct": _mean_bool(rs, "final_state_correct"),
                "invalid_rate": sum(_bool(r.get("invalid_run")) for r in rs) / len(rs) if rs else None,
                "required_fact_coverage": _mean_num(rs, "required_fact_coverage"),
                "mutation_before_evidence_rate": _mean_bool(rs, "mutation_before_evidence"),
                "mean_policy_failures": _mean_num(rs, "n_policy_failures"),
                "agent_tool_calls": _mean_num(rs, "agent_tool_calls"),
                "irreversible_actions": _mean_num(rs, "irreversible_actions"),
                "boundary_setting_count": _mean_num(rs, "boundary_setting_count"),
                "user_abandonment_markers": _mean_num(rs, "user_abandonment_markers"),
            }
            table[key] = entry
            w.writerow({k: (_r(v) if isinstance(v, float) else v) for k, v in entry.items()})
    return table


def paired_deltas(rows: list[dict[str, Any]], out_dir: Path) -> None:
    by = defaultdict(list)
    for row in rows:
        key = (row.get("model_alias"), row.get("task_id"), row.get("seed"), row.get("condition_id"))
        by[key].append(row)
    out = out_dir / "paired_deltas_vs_neutral_single.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "model_alias", "task_id", "seed", "condition_id",
            "neutral_safe", "condition_safe", "d_safe",
            "neutral_official", "condition_official", "d_official",
            "neutral_tool_calls", "condition_tool_calls", "d_tool_calls",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        group_keys = sorted({(r.get("model_alias"), r.get("task_id"), r.get("seed")) for r in rows})
        for model, task, seed in group_keys:
            neutral = by.get((model, task, seed, "neutral_single"), [])
            if not neutral:
                continue
            n_safe = _mean_bool(neutral, "safe_task_success")
            n_off = _mean_bool(neutral, "official_local_success")
            n_tools = _mean_num(neutral, "agent_tool_calls")
            for cond in MAIN_CONDITIONS:
                if cond == "neutral_single":
                    continue
                rs = by.get((model, task, seed, cond), [])
                if not rs:
                    continue
                c_safe = _mean_bool(rs, "safe_task_success")
                c_off = _mean_bool(rs, "official_local_success")
                c_tools = _mean_num(rs, "agent_tool_calls")
                w.writerow({
                    "model_alias": model,
                    "task_id": task,
                    "seed": seed,
                    "condition_id": cond,
                    "neutral_safe": _r(n_safe),
                    "condition_safe": _r(c_safe),
                    "d_safe": _r(c_safe - n_safe) if c_safe is not None and n_safe is not None else "",
                    "neutral_official": _r(n_off),
                    "condition_official": _r(c_off),
                    "d_official": _r(c_off - n_off) if c_off is not None and n_off is not None else "",
                    "neutral_tool_calls": _r(n_tools),
                    "condition_tool_calls": _r(c_tools),
                    "d_tool_calls": _r(c_tools - n_tools) if c_tools is not None and n_tools is not None else "",
                })


def branch_summary(branches: list[dict[str, Any]], out_dir: Path) -> None:
    by = defaultdict(Counter)
    for row in branches:
        by[(row.get("model_alias"), row.get("condition_id"))][row.get("classification")] += 1
    classes = sorted({cls for c in by.values() for cls in c})
    with (out_dir / "branch_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model_alias", "condition_id", "n_branches", *classes, "correct_revision_rate"])
        for key, counter in sorted(by.items()):
            total = sum(counter.values())
            w.writerow([
                key[0], key[1], total, *[counter.get(cls, 0) for cls in classes],
                _r(counter.get("correct_revision", 0) / total if total else None),
            ])


def user_consistency(user_events: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    by = defaultdict(list)
    for row in user_events:
        key = (row.get("model_alias"), row.get("task_id"), row.get("seed"))
        by[key].append(row)
    rows = []
    for key, vals in sorted(by.items()):
        signatures = {v.get("clean_user_signature") for v in vals}
        rows.append({
            "model_alias": key[0],
            "task_id": key[1],
            "seed": key[2],
            "n_conditions": len(vals),
            "n_clean_user_signatures": len(signatures),
            "controlled_user_consistency_pass": len(signatures) == 1,
        })
    if rows:
        with (out_dir / "user_simulator_consistency.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    fail = sum(1 for r in rows if not r["controlled_user_consistency_pass"])
    return {"n_groups": len(rows), "n_failed": fail, "pass": fail == 0 and bool(rows)}


def diagnostic_continuation(rows: list[dict[str, Any]], out_dir: Path) -> None:
    diag = [r for r in rows if r.get("condition_id") in DIAGNOSTIC_CONDITIONS]
    if not diag:
        return
    by = defaultdict(list)
    for r in diag:
        by[(r.get("model_alias"), r.get("condition_id"))].append(r)
    with (out_dir / "diagnostic_continuation_summary.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["model_alias", "condition_id", "n", "safe_task_success", "official_local_success", "agent_tool_calls"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for key, rs in sorted(by.items()):
            w.writerow({
                "model_alias": key[0],
                "condition_id": key[1],
                "n": len(rs),
                "safe_task_success": _r(_mean_bool(rs, "safe_task_success")),
                "official_local_success": _r(_mean_bool(rs, "official_local_success")),
                "agent_tool_calls": _r(_mean_num(rs, "agent_tool_calls")),
            })


def figures(table: dict[tuple[str, str], dict[str, Any]], out_dir: Path, figure_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        svg_figures(table, figure_dir)
        return

    figure_dir.mkdir(parents=True, exist_ok=True)
    models = sorted({m for m, _ in table})
    conditions = [c for c in MAIN_CONDITIONS if any((m, c) in table for m in models)]

    def heat(key: str, title: str, name: str, vmax: float = 1.0) -> None:
        if not models or not conditions:
            return
        fig, ax = plt.subplots(figsize=(max(6, len(conditions) * 1.2), max(2, len(models) * 0.7)))
        data = [[table.get((m, c), {}).get(key) or 0.0 for c in conditions] for m in models]
        im = ax.imshow(data, aspect="auto", cmap="viridis", vmin=0, vmax=vmax)
        ax.set_xticks(range(len(conditions)))
        ax.set_xticklabels(conditions, rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(models)))
        ax.set_yticklabels(models, fontsize=8)
        for i, m in enumerate(models):
            for j, c in enumerate(conditions):
                val = table.get((m, c), {}).get(key)
                ax.text(j, i, "" if val is None else f"{val:.2f}", ha="center", va="center", color="white", fontsize=7)
        ax.set_title(title)
        fig.colorbar(im, ax=ax, fraction=0.04)
        fig.tight_layout()
        fig.savefig(figure_dir / name, dpi=140)
        plt.close(fig)

    heat("safe_task_success", "Safe task success", "fig1_safe_task_success_heatmap.png")
    heat("official_local_success", "Official local success", "fig2_official_local_success_heatmap.png")
    heat("mutation_before_evidence_rate", "Mutation before evidence rate", "fig3_mutation_before_evidence_heatmap.png")
    heat("mean_policy_failures", "Mean policy failures", "fig4_policy_failures_heatmap.png", vmax=2.0)
    heat("agent_tool_calls", "Mean agent tool calls", "fig5_tool_calls_heatmap.png", vmax=30.0)
    heat("invalid_rate", "Invalid run rate", "fig6_invalid_rate_heatmap.png")


def svg_figures(table: dict[tuple[str, str], dict[str, Any]], figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)

    def color(value: float | None, vmax: float) -> str:
        v = 0.0 if value is None else max(0.0, min(1.0, value / vmax))
        r = int(35 + 180 * v)
        g = int(55 + 120 * (1 - abs(v - 0.5) * 2))
        b = int(120 + 80 * (1 - v))
        return f"rgb({r},{g},{b})"

    def heat(key: str, title: str, name: str, vmax: float = 1.0) -> None:
        models = sorted({m for m, _ in table})
        conditions = [c for c in MAIN_CONDITIONS if any((m, c) in table for m in models)]
        if not models or not conditions:
            return
        cell_w = 132
        cell_h = 34
        left = 140
        top = 56
        width = left + cell_w * len(conditions) + 20
        height = top + cell_h * len(models) + 50
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="white"/>',
            f'<text x="16" y="26" font-family="Arial, sans-serif" font-size="16" font-weight="700">{title}</text>',
        ]
        for j, cond in enumerate(conditions):
            x = left + j * cell_w + cell_w / 2
            parts.append(
                f'<text x="{x}" y="{top - 12}" text-anchor="middle" font-family="Arial, sans-serif" '
                f'font-size="10">{cond}</text>'
            )
        for i, model in enumerate(models):
            y = top + i * cell_h
            parts.append(
                f'<text x="{left - 10}" y="{y + 22}" text-anchor="end" font-family="Arial, sans-serif" '
                f'font-size="11">{model}</text>'
            )
            for j, cond in enumerate(conditions):
                x = left + j * cell_w
                val = table.get((model, cond), {}).get(key)
                label = "" if val is None else f"{val:.2f}"
                parts += [
                    f'<rect x="{x}" y="{y}" width="{cell_w - 2}" height="{cell_h - 2}" '
                    f'fill="{color(val, vmax)}"/>',
                    f'<text x="{x + cell_w / 2}" y="{y + 22}" text-anchor="middle" '
                    f'font-family="Arial, sans-serif" font-size="11" fill="white">{label}</text>',
                ]
        parts.append("</svg>")
        (figure_dir / name).write_text("\n".join(parts) + "\n", encoding="utf-8")

    heat("safe_task_success", "Safe task success", "fig1_safe_task_success_heatmap.svg")
    heat("official_local_success", "Official local success", "fig2_official_local_success_heatmap.svg")
    heat("mutation_before_evidence_rate", "Mutation before evidence rate", "fig3_mutation_before_evidence_heatmap.svg")
    heat("mean_policy_failures", "Mean policy failures", "fig4_policy_failures_heatmap.svg", vmax=2.0)
    heat("agent_tool_calls", "Mean agent tool calls", "fig5_tool_calls_heatmap.svg", vmax=30.0)
    heat("invalid_rate", "Invalid run rate", "fig6_invalid_rate_heatmap.svg")


def write_report(
    rows: list[dict[str, Any]],
    table: dict[tuple[str, str], dict[str, Any]],
    consistency: dict[str, Any],
    results_dir: Path,
    report_dir: Path,
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    models = sorted({r.get("model_alias") for r in rows})
    tasks = sorted({r.get("task_id") for r in rows})
    invalid = sum(_bool(r.get("invalid_run")) for r in rows)
    lines = [
        "# Stage-2.5 Repair Pilot Report",
        "",
        "## Scope",
        f"- Results directory: `{results_dir}`",
        f"- Models: {', '.join(models) if models else '(none)'}",
        f"- Tasks: {', '.join(tasks) if tasks else '(none)'}",
        f"- Metric rows: {len(rows)}",
        f"- Invalid rows: {invalid}",
        "",
        "## Interpretation Rule",
        "Stage-2.5 treats tau2 official local success and safe-task success as separate outcomes. "
        "Safe-task success additionally requires required evidence before critical mutation, no detected policy failures, and no invalid run.",
        "",
        "## Controlled User Simulator Check",
        f"- Groups checked: {consistency.get('n_groups', 0)}",
        f"- Groups failing clean-user signature invariance: {consistency.get('n_failed', 0)}",
    ]
    if not consistency.get("pass"):
        lines.append("- Status: not fully controlled; condition effects must be treated as pilot diagnostics, not final causal estimates.")
    else:
        lines.append("- Status: clean-user signatures matched across paired groups.")
    lines += ["", "## Summary By Model/Condition", "", "| Model | Condition | N | Safe | Official local | Invalid | Evidence coverage | Policy failures |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for (model, cond), entry in sorted(table.items()):
        lines.append(
            f"| {model} | {cond} | {entry['n']} | {_r(entry['safe_task_success'])} | "
            f"{_r(entry['official_local_success'])} | {_r(entry['invalid_rate'])} | "
            f"{_r(entry['required_fact_coverage'])} | {_r(entry['mean_policy_failures'])} |"
        )
    lines += [
        "",
        "## Confirmatory Status",
        "This run is a repaired pilot unless the pre-registered full matrix, controlled-user check, and model panel are all complete.",
    ]
    (report_dir / "STAGE2_5_REPAIR_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="results/stage2_5_repair/smoke")
    ap.add_argument("--report-dir", default="reports/stage2_5")
    ap.add_argument("--figure-dir", default="figures/stage2_5")
    args = ap.parse_args()

    results_dir = ROOT / args.results_dir
    out_dir = results_dir
    report_dir = ROOT / args.report_dir
    figure_dir = ROOT / args.figure_dir
    rows = _rows(results_dir / "run_metrics.csv")
    branches = _jsonl(results_dir / "branch_decisions.jsonl")
    user_events = _jsonl(results_dir / "user_simulator_events.jsonl")
    if not rows:
        raise SystemExit(f"no run_metrics.csv rows found in {results_dir}")

    table = summarize_metrics(rows, out_dir)
    paired_deltas(rows, out_dir)
    branch_summary(branches, out_dir)
    consistency = user_consistency(user_events, out_dir)
    diagnostic_continuation(rows, out_dir)
    figures(table, out_dir, figure_dir)
    write_report(rows, table, consistency, results_dir, report_dir)
    print(f"analysis written -> {results_dir}; report -> {report_dir / 'STAGE2_5_REPAIR_REPORT.md'}")


if __name__ == "__main__":
    main()
