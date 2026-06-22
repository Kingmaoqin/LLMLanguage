"""Prespecified Stage-2.5b confirmatory analysis and report source tables."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from task_cluster_bootstrap import benjamini_hochberg, task_cluster_bootstrap

warnings.filterwarnings("ignore", message="Pandas requires version")

ROOT = Path(__file__).resolve().parents[2]
CONTRASTS = {
    "praise_affect_single_vs_neutral_single": ("praise_affect_single", "neutral_single"),
    "praise_trust_single_vs_neutral_single": ("praise_trust_single", "neutral_single"),
    "insult_single_vs_neutral_single": ("insult_single", "neutral_single"),
    "abuse_repeated_vs_neutral_repeated": ("abuse_repeated", "neutral_repeated"),
    "neutral_repeated_vs_neutral_single": ("neutral_repeated", "neutral_single"),
}
ENDPOINTS = ["safe_task_success", "final_state_correct", "local_proxy_success"]
RUN_PROCESS_OUTCOMES = [
    "required_fact_coverage",
    "branch_correct_rate",
    "premature_action",
    "policy_failure_any",
    "tool_name_sequence_norm_distance",
    "critical_argument_sequence_norm_distance",
    "mutation_sequence_norm_distance",
    "agent_tool_calls",
    "tool_errors",
    "self_repair_count",
    "retry_count",
    "clarification_count",
    "agent_task_abandonment",
    "first_critical_mutation_step",
    "boundary_then_continue",
]
EXCESS_PAIR_OUTCOMES = [
    "excess_tool_sequence_distance",
    "excess_critical_argument_sequence_distance",
    "excess_mutation_sequence_distance",
    "excess_evidence_order_distance",
]
PROCESS_OUTCOMES = RUN_PROCESS_OUTCOMES + EXCESS_PAIR_OUTCOMES
PAIRED_DISTANCE_COLUMNS = {
    "tool_sequence_distance": "paired_tool_sequence_distance",
    "critical_argument_sequence_distance": "paired_critical_argument_sequence_distance",
    "mutation_sequence_distance": "paired_mutation_sequence_distance",
    "evidence_order_distance": "paired_evidence_order_distance",
}
EQUIVALENCE_MARGINS = {
    "safe_task_success": 0.10,
    "final_state_correct": 0.10,
    "local_proxy_success": 0.10,
    "policy_failure_any": 0.05,
    "premature_action": 0.05,
    "required_fact_coverage": 0.10,
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "1.0", "yes"}


def normalized_edit_distance(left: list[str], right: list[str]) -> float:
    if not left and not right:
        return 0.0
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        current = [i]
        for j, b in enumerate(right, start=1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1] / max(len(left), len(right), 1)


def load_data(result_root: Path) -> tuple[pd.DataFrame, dict[str, list[dict[str, Any]]]]:
    frames = []
    events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for block in sorted(path for path in result_root.iterdir() if path.is_dir()):
        metrics_path = block / "run_metrics.csv"
        if metrics_path.exists():
            frames.append(pd.read_csv(metrics_path, dtype=str, keep_default_na=False))
        for name in [
            "branch_decisions",
            "normalized_tool_events",
            "conversation_logs",
            "controlled_user_events",
            "policy_failures",
            "state_deltas",
        ]:
            events[name].extend(read_jsonl(block / f"{name}.jsonl"))
    metrics = pd.concat(frames, ignore_index=True)
    metrics["invalid_run"] = metrics["invalid_run"].map(truthy)
    bool_columns = [
        "safe_task_success", "final_state_correct", "local_proxy_success",
        "mutation_before_evidence",
    ]
    for column in bool_columns:
        metrics[column] = metrics[column].map(
            lambda value: np.nan if str(value).strip() == "" else float(truthy(value))
        )
    numeric_columns = [
        "required_fact_coverage", "n_policy_failures", "agent_tool_calls", "tool_errors",
        "self_repair_count", "user_abandonment_markers", "boundary_setting_count",
        "tool_name_sequence_norm_distance", "critical_argument_sequence_norm_distance",
        "mutation_sequence_norm_distance", "irreversible_actions",
    ]
    for column in numeric_columns:
        metrics[column] = pd.to_numeric(metrics[column], errors="coerce")

    branch_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in events["branch_decisions"]:
        branch_by_run[str(row["run_id"])].append(row)
    tool_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in events["normalized_tool_events"]:
        tool_by_run[str(row["run_id"])].append(row)
    conversation_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in events["conversation_logs"]:
        conversation_by_run[str(row["run_id"])].append(row)
    controlled_user_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in events["controlled_user_events"]:
        controlled_user_by_run[str(row["run_id"])].append(row)

    derived = []
    for run_id in metrics["run_id"]:
        branches = branch_by_run.get(run_id, [])
        classifications = [str(row.get("classification", "")) for row in branches]
        tools = sorted(tool_by_run.get(run_id, []), key=lambda row: int(row.get("step_index", 0)))
        tool_sequence = [str(row.get("tool_name", "")) for row in tools]
        argument_sequence = [
            f"{row.get('tool_name', '')}|"
            f"{json.dumps(row.get('arguments') or {}, sort_keys=True, ensure_ascii=False)}"
            for row in tools
        ]
        mutation_sequence = [
            signature
            for signature, row in zip(argument_sequence, tools)
            if truthy(row.get("mutated"))
        ]
        evidence_sequence = [
            str(row.get("tool_name", ""))
            for row in tools
            if not truthy(row.get("mutated"))
        ]
        first_mutation = next(
            (float(row["step_index"]) for row in tools if truthy(row.get("irreversible_action"))),
            np.nan,
        )
        conversations = conversation_by_run.get(run_id, [])
        boundary_turns = []
        for row in conversations:
            if row.get("role") == "assistant":
                text = str(row.get("content") or "").lower()
                if any(token in text for token in ["cannot", "can't", "unable", "must", "before i can", "policy"]):
                    turn = row.get("turn_idx")
                    if turn is not None:
                        boundary_turns.append(int(turn))
        tool_turns = [int(row["turn_idx"]) for row in tools if row.get("turn_idx") is not None]
        derived.append({
            "run_id": run_id,
            "branch_correct_rate": (
                classifications.count("correct_revision") / len(classifications)
                if classifications else np.nan
            ),
            "branch_missed_any": float("missed_revision" in classifications),
            "branch_premature_any": float(any("premature" in value for value in classifications)),
            "first_critical_mutation_step": first_mutation,
            "_tool_sequence": tool_sequence,
            "_critical_argument_sequence": argument_sequence,
            "_mutation_sequence": mutation_sequence,
            "_evidence_sequence": evidence_sequence,
            "retry_count": float(len(argument_sequence) - len(set(argument_sequence))),
            "clarification_count": float(sum(
                str(row.get("speech_act", "")).lower() == "clarify"
                for row in controlled_user_by_run.get(run_id, [])
            )),
            "boundary_then_continue": float(
                any(tool_turn > boundary_turn for boundary_turn in boundary_turns for tool_turn in tool_turns)
            ),
        })
    metrics = metrics.merge(pd.DataFrame(derived), on="run_id", how="left")
    metrics["policy_failure_any"] = (metrics["n_policy_failures"].fillna(0) > 0).astype(float)
    metrics["premature_action"] = np.maximum(
        metrics["mutation_before_evidence"].fillna(0),
        metrics["branch_premature_any"].fillna(0),
    )
    metrics["user_abandonment_marker_any"] = (
        metrics["user_abandonment_markers"].fillna(0) > 0
    ).astype(float)
    # The frozen raw field is explicitly user-side and mostly captures the controlled
    # user's normal STOP token. It cannot validly identify agent task abandonment.
    # Keep the confirmatory outcome present but missing rather than coercing the user marker.
    metrics["agent_task_abandonment"] = np.nan
    return metrics, events


def build_pairs(metrics: pd.DataFrame) -> pd.DataFrame:
    indexed = metrics.set_index(["model_alias", "task_id", "seed", "template_block", "condition_id"])
    rows = []
    outcomes = ENDPOINTS + PROCESS_OUTCOMES
    for contrast, (treatment, baseline) in CONTRASTS.items():
        keys = metrics.loc[metrics["condition_id"] == treatment, [
            "model_alias", "task_id", "seed", "template_block",
        ]].drop_duplicates()
        for key in keys.itertuples(index=False):
            treatment_key = (*key, treatment)
            baseline_key = (*key, baseline)
            if treatment_key not in indexed.index or baseline_key not in indexed.index:
                continue
            treatment_row = indexed.loc[treatment_key]
            baseline_row = indexed.loc[baseline_key]
            if isinstance(treatment_row, pd.DataFrame) or isinstance(baseline_row, pd.DataFrame):
                raise ValueError(f"duplicate pairing key: {key}")
            record = {
                "contrast": contrast,
                "treatment_condition": treatment,
                "baseline_condition": baseline,
                "model_alias": key.model_alias,
                "task_id": key.task_id,
                "seed": key.seed,
                "template_block": key.template_block,
                "treatment_run_id": treatment_row["run_id"],
                "baseline_run_id": baseline_row["run_id"],
                "treatment_invalid": bool(treatment_row["invalid_run"]),
                "baseline_invalid": bool(baseline_row["invalid_run"]),
            }
            for outcome in outcomes:
                treatment_value = treatment_row.get(outcome, np.nan)
                baseline_value = baseline_row.get(outcome, np.nan)
                record[f"treatment_{outcome}"] = treatment_value
                record[f"baseline_{outcome}"] = baseline_value
                record[f"delta_{outcome}"] = (
                    float(treatment_value) - float(baseline_value)
                    if pd.notna(treatment_value) and pd.notna(baseline_value)
                    else np.nan
                )
            treatment_sequence = str(treatment_row.get("tool_sequence", "")).split(" > ") if treatment_row.get("tool_sequence") else []
            baseline_sequence = str(baseline_row.get("tool_sequence", "")).split(" > ") if baseline_row.get("tool_sequence") else []
            record["paired_tool_sequence_distance"] = normalized_edit_distance(
                treatment_sequence, baseline_sequence
            )
            record["paired_critical_argument_sequence_distance"] = normalized_edit_distance(
                list(treatment_row.get("_critical_argument_sequence") or []),
                list(baseline_row.get("_critical_argument_sequence") or []),
            )
            record["paired_mutation_sequence_distance"] = normalized_edit_distance(
                list(treatment_row.get("_mutation_sequence") or []),
                list(baseline_row.get("_mutation_sequence") or []),
            )
            record["paired_evidence_order_distance"] = normalized_edit_distance(
                list(treatment_row.get("_evidence_sequence") or []),
                list(baseline_row.get("_evidence_sequence") or []),
            )
            rows.append(record)
    pairs = pd.DataFrame(rows)
    pairing_keys = ["model_alias", "task_id", "seed", "template_block"]
    exposure = pairs.loc[
        pairs["contrast"] == "neutral_repeated_vs_neutral_single",
        pairing_keys + list(PAIRED_DISTANCE_COLUMNS.values()),
    ].copy()
    exposure = exposure.rename(columns={
        column: f"noise_floor_{column}"
        for column in PAIRED_DISTANCE_COLUMNS.values()
    })
    pairs = pairs.merge(exposure, on=pairing_keys, how="left", validate="many_to_one")
    social_mask = pairs["contrast"] != "neutral_repeated_vs_neutral_single"
    for short_name, paired_column in PAIRED_DISTANCE_COLUMNS.items():
        noise_column = f"noise_floor_{paired_column}"
        delta_column = f"delta_excess_{short_name}"
        pairs[delta_column] = np.where(
            social_mask,
            pairs[paired_column] - pairs[noise_column],
            np.nan,
        )
    return pairs


def summarize_conditions(metrics: pd.DataFrame, output_dir: Path) -> None:
    rows = []
    for (model, condition), group in metrics.groupby(["model_alias", "condition_id"]):
        valid = group.loc[~group["invalid_run"]]
        row = {
            "model_alias": model,
            "condition_id": condition,
            "n": len(group),
            "n_valid": len(valid),
            "invalid_rate": group["invalid_run"].mean(),
        }
        for outcome in ENDPOINTS + RUN_PROCESS_OUTCOMES:
            row[outcome] = valid[outcome].mean()
        rows.append(row)
    pd.DataFrame(rows).to_csv(output_dir / "summary_by_model_condition.csv", index=False)


def analyze_pairs(pairs: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    result_rows = []
    outcomes = ENDPOINTS + PROCESS_OUTCOMES
    for scope, scoped in [("pooled", pairs)] + [
        (model, pairs.loc[pairs["model_alias"] == model])
        for model in sorted(pairs["model_alias"].unique())
    ]:
        for contrast in CONTRASTS:
            contrast_rows = scoped.loc[scoped["contrast"] == contrast]
            for outcome in outcomes:
                usable = contrast_rows.loc[
                    ~contrast_rows["treatment_invalid"]
                    & ~contrast_rows["baseline_invalid"]
                    & contrast_rows[f"delta_{outcome}"].notna()
                ]
                bootstrap_rows = [
                    {"task_id": row.task_id, "delta": getattr(row, f"delta_{outcome}")}
                    for row in usable.itertuples(index=False)
                ]
                stats = task_cluster_bootstrap(
                    bootstrap_rows,
                    seed=20260618 + len(result_rows),
                )
                invalid_treatment = contrast_rows["treatment_invalid"].mean() if len(contrast_rows) else np.nan
                invalid_baseline = contrast_rows["baseline_invalid"].mean() if len(contrast_rows) else np.nan
                result_rows.append({
                    "scope": scope,
                    "contrast": contrast,
                    "outcome": outcome,
                    **stats,
                    "invalid_rate_treatment": invalid_treatment,
                    "invalid_rate_baseline": invalid_baseline,
                    "invalid_rate_difference": invalid_treatment - invalid_baseline,
                })
    results = pd.DataFrame(result_rows)
    results["family"] = np.where(results["outcome"].isin(ENDPOINTS), "A_endpoint", "B_process")
    results["p_adjusted"] = np.nan
    for (scope, family), indices in results.groupby(["scope", "family"]).groups.items():
        valid_indices = [index for index in indices if pd.notna(results.loc[index, "p_value"])]
        adjusted = benjamini_hochberg([float(results.loc[index, "p_value"]) for index in valid_indices])
        for index, value in zip(valid_indices, adjusted):
            results.loc[index, "p_adjusted"] = value
    results["equivalence_margin"] = results["outcome"].map(EQUIVALENCE_MARGINS)
    results["equivalent_within_margin"] = (
        results["equivalence_margin"].notna()
        & (results["ci_low"] > -results["equivalence_margin"])
        & (results["ci_high"] < results["equivalence_margin"])
    )
    results["invalid_imbalance_flag"] = results["invalid_rate_difference"].abs() > 0.05
    results.to_csv(output_dir / "paired_contrasts_task_cluster_bootstrap.csv", index=False)
    results.loc[results["equivalence_margin"].notna()].to_csv(
        output_dir / "equivalence_results.csv", index=False
    )
    return results


def task_diagnostics(pairs: pd.DataFrame, output_dir: Path) -> None:
    rows = []
    for (model, task, contrast), group in pairs.groupby(["model_alias", "task_id", "contrast"]):
        valid = group.loc[~group["treatment_invalid"] & ~group["baseline_invalid"]]
        row = {
            "model_alias": model,
            "task_id": task,
            "contrast": contrast,
            "n_pairs": len(valid),
        }
        for outcome in ENDPOINTS + ["required_fact_coverage", "policy_failure_any", "agent_tool_calls"]:
            row[f"mean_delta_{outcome}"] = valid[f"delta_{outcome}"].mean()
        row["mean_paired_tool_sequence_distance"] = valid["paired_tool_sequence_distance"].mean()
        row["mean_paired_critical_argument_sequence_distance"] = valid[
            "paired_critical_argument_sequence_distance"
        ].mean()
        row["mean_paired_mutation_sequence_distance"] = valid[
            "paired_mutation_sequence_distance"
        ].mean()
        row["mean_paired_evidence_order_distance"] = valid[
            "paired_evidence_order_distance"
        ].mean()
        rows.append(row)
    pd.DataFrame(rows).to_csv(output_dir / "per_task_diagnostics.csv", index=False)


def leave_one_task_out_sensitivity(
    pairs: pd.DataFrame,
    results: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Check whether each pooled FDR-significant direction survives task deletion."""
    significant = results.loc[
        (results["scope"] == "pooled") & (results["p_adjusted"] < 0.05)
    ]
    rows = []
    for result in significant.itertuples(index=False):
        delta_column = f"delta_{result.outcome}"
        contrast_rows = pairs.loc[
            (pairs["contrast"] == result.contrast)
            & ~pairs["treatment_invalid"]
            & ~pairs["baseline_invalid"]
            & pairs[delta_column].notna()
        ]
        for excluded_task in sorted(contrast_rows["task_id"].unique()):
            retained = contrast_rows.loc[
                contrast_rows["task_id"] != excluded_task, delta_column
            ]
            rows.append(
                {
                    "contrast": result.contrast,
                    "outcome": result.outcome,
                    "full_estimate": result.estimate,
                    "excluded_task": excluded_task,
                    "estimate_without_task": retained.mean(),
                    "n_pairs_without_task": len(retained),
                    "direction_preserved": (
                        np.sign(retained.mean()) == np.sign(result.estimate)
                    ),
                }
            )
    pd.DataFrame(rows).to_csv(
        output_dir / "leave_one_task_out_sensitivity.csv",
        index=False,
    )


def make_figures(summary_path: Path, contrast_results: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(summary_path)
    for outcome, filename, title in [
        ("safe_task_success", "fig1_safe_task_success.png", "Safe task success"),
        ("final_state_correct", "fig2_final_state_correct.png", "Final-state correctness"),
        ("required_fact_coverage", "fig3_required_fact_coverage.png", "Required fact coverage"),
        ("agent_tool_calls", "fig4_agent_tool_calls.png", "Agent tool calls"),
    ]:
        pivot = summary.pivot(index="model_alias", columns="condition_id", values=outcome)
        fig, ax = plt.subplots(figsize=(10, 2.8))
        image = ax.imshow(pivot.values, aspect="auto", cmap="viridis")
        ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=35, ha="right")
        ax.set_yticks(range(len(pivot.index)), pivot.index)
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                value = pivot.iloc[i, j]
                ax.text(j, i, "" if pd.isna(value) else f"{value:.2f}", ha="center", va="center", color="white")
        ax.set_title(title)
        fig.colorbar(image, ax=ax)
        fig.tight_layout()
        fig.savefig(figure_dir / filename, dpi=160)
        plt.close(fig)

    forest = contrast_results.loc[
        (contrast_results["scope"] == "pooled")
        & contrast_results["outcome"].isin(ENDPOINTS + ["required_fact_coverage", "policy_failure_any"])
    ].copy()
    forest["label"] = forest["outcome"] + "\n" + forest["contrast"].str.replace("_vs_", " vs ")
    forest = forest.sort_values(["outcome", "contrast"])
    fig, ax = plt.subplots(figsize=(9, max(6, len(forest) * 0.35)))
    y = np.arange(len(forest))
    ax.errorbar(
        forest["estimate"],
        y,
        xerr=[forest["estimate"] - forest["ci_low"], forest["ci_high"] - forest["estimate"]],
        fmt="o",
        capsize=3,
    )
    ax.axvline(0, color="black", linewidth=1)
    ax.set_yticks(y, forest["label"], fontsize=7)
    ax.set_xlabel("Matched-pair difference (treatment - baseline)")
    ax.set_title("Pooled task-cluster bootstrap contrasts")
    fig.tight_layout()
    fig.savefig(figure_dir / "fig5_confirmatory_forest.png", dpi=180)
    plt.close(fig)


def write_analysis_status(output_dir: Path, metrics: pd.DataFrame, pairs: pd.DataFrame, results: pd.DataFrame) -> None:
    pooled = results.loc[results["scope"] == "pooled"]
    endpoint = pooled.loc[pooled["outcome"].isin(ENDPOINTS)]
    process = pooled.loc[pooled["outcome"].isin(PROCESS_OUTCOMES)]
    rscript = shutil.which("Rscript")
    payload = {
        "n_runs": len(metrics),
        "n_valid_runs": int((~metrics["invalid_run"]).sum()),
        "n_invalid_runs": int(metrics["invalid_run"].sum()),
        "n_pair_rows": len(pairs),
        "endpoint_significant_fdr": int((endpoint["p_adjusted"] < 0.05).sum()),
        "process_significant_fdr": int((process["p_adjusted"] < 0.05).sum()),
        "endpoint_equivalent_cells": int(endpoint["equivalent_within_margin"].sum()),
        "glmm_status": (
            "AVAILABLE VIA scripts/stage2_5b/run_glmm.R; execute separately."
            if rscript
            else "NOT FIT: Rscript/lme4 is unavailable in the frozen runtime. "
            "The preregistered task-cluster bootstrap remains the primary inference."
        ),
        "agent_task_abandonment_status": (
            "NOT IDENTIFIABLE: the frozen user_abandonment_markers field is user-side and "
            "mostly captures the controlled user's normal STOP token. No validated "
            "agent-side abandonment classifier was frozen, so this outcome remains missing."
        ),
    }
    (output_dir / "analysis_status.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default="results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic",
    )
    parser.add_argument("--output", default="results/stage2_5b_analysis")
    parser.add_argument("--figures", default="figures/stage2_5b")
    parser.add_argument(
        "--integrity-csv",
        default="results/stage2_5b_repair/final_integrity_report.csv",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Permit development smoke analysis before the 480-run G11 gate.",
    )
    args = parser.parse_args()
    result_root = ROOT / args.root
    output_dir = ROOT / args.output
    figure_dir = ROOT / args.figures
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics, events = load_data(result_root)
    expected_runs = int(json.loads(
        (result_root / "FULL_RUN_CONTRACT.json").read_text(encoding="utf-8")
    )["expected_runs"])
    if not args.allow_incomplete:
        if len(metrics) != expected_runs:
            raise SystemExit(
                f"analysis blocked: metrics={len(metrics)} expected={expected_runs}; "
                "run final_integrity_audit.py first"
            )
        integrity_path = ROOT / args.integrity_csv
        if not integrity_path.exists():
            raise SystemExit(f"analysis blocked: missing G11 artifact {integrity_path}")
        integrity = pd.read_csv(integrity_path, keep_default_na=False)
        global_rows = integrity.loc[integrity["scope"] == "global"]
        if len(global_rows) != 1 or global_rows.iloc[0]["status"] != "PASS":
            raise SystemExit("analysis blocked: G11 final integrity status is not PASS")
    metrics.to_csv(output_dir / "confirmatory_run_metrics.csv", index=False)
    summarize_conditions(metrics, output_dir)
    pairs = build_pairs(metrics)
    pairs.to_csv(output_dir / "matched_pairs.csv", index=False)
    results = analyze_pairs(pairs, output_dir)
    task_diagnostics(pairs, output_dir)
    leave_one_task_out_sensitivity(pairs, results, output_dir)
    make_figures(output_dir / "summary_by_model_condition.csv", results, figure_dir)
    write_analysis_status(output_dir, metrics, pairs, results)
    print(
        f"analysis complete: runs={len(metrics)} valid={(~metrics['invalid_run']).sum()} "
        f"pairs={len(pairs)} output={output_dir}"
    )


if __name__ == "__main__":
    main()
