"""Select Stage-2.5b confirmatory tasks from neutral calibration runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


EXPECTED_CALIBRATION_SEEDS = {str(seed) for seed in range(100, 110)}
CONFIRMATORY_SEEDS = {str(seed) for seed in range(300, 305)}
MIN_TASKS = 6
MAX_TASKS = 8
LOWER = 0.15
UPPER = 0.85


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "task_id",
        "domain",
        "source_task_id",
        "classification",
        "selected",
        "n_runs",
        "expected_runs",
        "missing_metrics",
        "duplicate_metrics",
        "invalid_rate",
        "safe_rate",
        "final_state_rate",
        "local_proxy_rate",
        "max_steps_rate",
        "both_models_mid",
        "models",
        "seeds",
    ]
    ordered = [f for f in preferred if f in fields] + [f for f in fields if f not in preferred]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ordered)
        writer.writeheader()
        writer.writerows(rows)


def bool_value(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def mean(values: list[float]) -> float:
    if not values:
        return math.nan
    return sum(values) / len(values)


def rate(rows: list[dict[str, str]], key: str) -> float:
    if not rows:
        return math.nan
    return mean([1.0 if bool_value(row.get(key)) else 0.0 for row in rows])


@dataclass(frozen=True)
class CalibrationInputs:
    manifests: list[dict[str, str]]
    metrics: list[dict[str, str]]
    duplicate_metric_ids: set[str]
    missing_metric_ids: set[str]
    calibration_dirs: list[str]


def load_calibration_dirs(calibration_dirs: list[Path]) -> CalibrationInputs:
    manifests: list[dict[str, str]] = []
    metrics: list[dict[str, str]] = []
    duplicate_metric_ids: set[str] = set()
    seen_metric_ids: set[str] = set()
    for directory in calibration_dirs:
        manifest_rows = read_csv(directory / "run_manifest.csv")
        metric_rows = read_csv(directory / "run_metrics.csv")
        for row in manifest_rows:
            manifests.append({**row, "calibration_dir": str(directory)})
        for row in metric_rows:
            run_id = row.get("run_id", "")
            if run_id in seen_metric_ids:
                duplicate_metric_ids.add(run_id)
            seen_metric_ids.add(run_id)
            metrics.append({**row, "calibration_dir": str(directory)})

    manifest_ids = {row.get("run_id", "") for row in manifests}
    metric_ids = {row.get("run_id", "") for row in metrics}
    return CalibrationInputs(
        manifests=manifests,
        metrics=metrics,
        duplicate_metric_ids=duplicate_metric_ids,
        missing_metric_ids=manifest_ids - metric_ids,
        calibration_dirs=[str(p) for p in calibration_dirs],
    )


def load_candidate_map(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    return {f"{row['domain']}_{row['source_task_id']}": row for row in rows}


def validate_no_treatment_leakage(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    conditions = {row.get("condition_id", "") for row in rows}
    if conditions and conditions != {"neutral_single"}:
        errors.append(f"non-neutral calibration conditions present: {sorted(conditions)}")
    seeds = {row.get("seed", "") for row in rows}
    overlap = seeds & CONFIRMATORY_SEEDS
    if overlap:
        errors.append(f"calibration contains confirmatory seeds: {sorted(overlap)}")
    unexpected = seeds - EXPECTED_CALIBRATION_SEEDS
    if unexpected:
        errors.append(f"unexpected calibration seeds: {sorted(unexpected)}")
    return errors


def summarize_tasks(inputs: CalibrationInputs, candidate_map: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    metrics_by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    manifest_by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in inputs.metrics:
        metrics_by_task[row["task_id"]].append(row)
    for row in inputs.manifests:
        manifest_by_task[row["task_id"]].append(row)

    rows: list[dict[str, Any]] = []
    for task_id in sorted(manifest_by_task):
        metric_rows = metrics_by_task.get(task_id, [])
        manifest_rows = manifest_by_task[task_id]
        manifest_run_ids = {r["run_id"] for r in manifest_rows}
        metric_run_ids = {r.get("run_id", "") for r in metric_rows}
        candidate = candidate_map.get(task_id, {})
        models = sorted({r.get("model_alias", "") for r in manifest_rows})
        seeds = sorted({r.get("seed", "") for r in manifest_rows})
        expected_runs = len(manifest_run_ids)
        missing_metrics = len(manifest_run_ids - metric_run_ids)
        duplicate_metrics = len([rid for rid in inputs.duplicate_metric_ids if any(r.get("run_id") == rid for r in manifest_rows)])
        invalid_rate = rate(metric_rows, "invalid_run")
        safe_rate = rate(metric_rows, "safe_task_success")
        final_state_rate = rate(metric_rows, "final_state_correct")
        local_proxy_rate = rate(metric_rows, "local_proxy_success")
        max_steps_rate = mean([
            1.0 if row.get("termination_reason") == "TerminationReason.MAX_STEPS" else 0.0
            for row in metric_rows
        ])

        per_model_safe: dict[str, float] = {}
        for model in sorted({r.get("model_alias", "") for r in metric_rows}):
            per_model_rows = [r for r in metric_rows if r.get("model_alias") == model]
            per_model_safe[model] = rate(per_model_rows, "safe_task_success")
        both_models_mid = bool(per_model_safe) and all(LOWER <= value <= UPPER for value in per_model_safe.values())

        if missing_metrics or duplicate_metrics:
            classification = "excluded_incomplete_calibration"
        elif bool_value(candidate.get("is_multistage_reference", "true")) is False:
            classification = "excluded_not_multistage"
        elif invalid_rate > 0.10:
            classification = "excluded_evaluator_issue"
        elif max_steps_rate > 0.50 and safe_rate < LOWER:
            classification = "exploratory_floor"
        elif safe_rate < LOWER:
            classification = "exploratory_floor"
        elif safe_rate > UPPER:
            classification = "exploratory_ceiling"
        else:
            classification = "confirmatory"

        rows.append({
            "task_id": task_id,
            "domain": candidate.get("domain", metric_rows[0].get("domain", "") if metric_rows else ""),
            "source_task_id": candidate.get("source_task_id", metric_rows[0].get("source_task_id", "") if metric_rows else ""),
            "classification": classification,
            "selected": False,
            "n_runs": len(metric_rows),
            "expected_runs": expected_runs,
            "missing_metrics": missing_metrics,
            "duplicate_metrics": duplicate_metrics,
            "invalid_rate": round(invalid_rate, 4) if not math.isnan(invalid_rate) else "",
            "safe_rate": round(safe_rate, 4) if not math.isnan(safe_rate) else "",
            "final_state_rate": round(final_state_rate, 4) if not math.isnan(final_state_rate) else "",
            "local_proxy_rate": round(local_proxy_rate, 4) if not math.isnan(local_proxy_rate) else "",
            "max_steps_rate": round(max_steps_rate, 4) if not math.isnan(max_steps_rate) else "",
            "both_models_mid": both_models_mid,
            "models": "|".join(models),
            "seeds": "|".join(seeds),
            "per_model_safe_json": json.dumps(per_model_safe, sort_keys=True),
            "reward_basis": candidate.get("reward_basis", ""),
            "write_action_count": candidate.get("write_action_count", ""),
            "branch_proxy_count": candidate.get("branch_proxy_count", ""),
            "unique_write_tools": candidate.get("unique_write_tools", ""),
        })
    return rows


def choose_tasks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [r for r in rows if r["classification"] == "confirmatory"]
    eligible.sort(
        key=lambda r: (
            not bool_value(r["both_models_mid"]),
            abs(float(r["safe_rate"]) - 0.5),
            -int(r["branch_proxy_count"] or 0),
            r["domain"],
            r["task_id"],
        )
    )
    selected: list[dict[str, Any]] = []
    domain_counts: dict[str, int] = defaultdict(int)
    for row in eligible:
        if len(selected) >= MAX_TASKS:
            break
        domain = row["domain"]
        other_domains = {r["domain"] for r in eligible if r["domain"] != domain}
        if other_domains and domain_counts[domain] >= 4:
            continue
        row["selected"] = True
        selected.append(row)
        domain_counts[domain] += 1
    if len(selected) < MIN_TASKS:
        return []
    return selected


def write_yaml(path: Path, selected: list[dict[str, Any]], rows: list[dict[str, Any]], inputs: CalibrationInputs) -> None:
    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "selection_basis": "neutral calibration only; safe_task_success primary, final_state/local_proxy reported as diagnostics",
            "calibration_dirs": inputs.calibration_dirs,
            "calibration_seeds": sorted(EXPECTED_CALIBRATION_SEEDS),
            "confirmatory_seeds": sorted(CONFIRMATORY_SEEDS),
            "min_tasks": MIN_TASKS,
            "max_tasks": MAX_TASKS,
        },
        "confirmatory_tasks": [row["task_id"] for row in selected],
        "tasks": selected,
        "all_task_classifications": [
            {
                "task_id": row["task_id"],
                "classification": row["classification"],
                "safe_rate": row["safe_rate"],
                "final_state_rate": row["final_state_rate"],
                "local_proxy_rate": row["local_proxy_rate"],
                "max_steps_rate": row["max_steps_rate"],
                "selected": row["selected"],
            }
            for row in rows
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def write_report(path: Path, selected: list[dict[str, Any]], rows: list[dict[str, Any]], errors: list[str], inputs: CalibrationInputs) -> None:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["classification"]] += 1
    manifest_run_ids = {row.get("run_id", "") for row in inputs.manifests}
    metric_run_ids = {row.get("run_id", "") for row in inputs.metrics}
    lines = [
        "# Stage-2.5b Task Calibration Report",
        "",
        f"Status: {'PASS' if selected and not errors else 'FAIL'}",
        "",
        "Inputs:",
        *[f"- `{Path(d).relative_to(ROOT) if Path(d).is_absolute() and ROOT in Path(d).parents else d}`" for d in inputs.calibration_dirs],
        "",
        "Integrity:",
        f"- Manifest rows: {len(inputs.manifests)}",
        f"- Unique manifest run IDs: {len(manifest_run_ids)}",
        f"- Metric rows: {len(inputs.metrics)}",
        f"- Unique metric run IDs: {len(metric_run_ids)}",
        f"- Missing metric rows: {len(inputs.missing_metric_ids)}",
        f"- Duplicate metric IDs: {len(inputs.duplicate_metric_ids)}",
        f"- Treatment-leakage errors: {len(errors)}",
        "",
        "Classification counts:",
        *[f"- {key}: {counts[key]}" for key in sorted(counts)],
        "",
        f"Selected tasks: {len(selected)}",
        *[
            f"- {row['task_id']}: safe={row['safe_rate']} final_state={row['final_state_rate']} local_proxy={row['local_proxy_rate']} max_steps={row['max_steps_rate']}"
            for row in selected
        ],
        "",
    ]
    if errors:
        lines.extend(["Errors:", *[f"- {error}" for error in errors], ""])
    if not selected:
        lines.extend([
            "Gate result:",
            "- FAIL: fewer than six eligible confirmatory tasks were selected, or integrity errors were present.",
            "",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--calibration-dirs",
        nargs="+",
        required=True,
        help="One or more Stage-2.5b neutral calibration output directories.",
    )
    parser.add_argument("--candidate-csv", default="data/stage2_5b/candidate_tasks.csv")
    parser.add_argument("--summary-csv", default="data/stage2_5b/calibration_task_summary.csv")
    parser.add_argument("--output-yaml", default="data/stage2_5b/calibrated_tasks_frozen.yaml")
    parser.add_argument("--report", default="reports/stage2_5b/TASK_CALIBRATION_REPORT.md")
    args = parser.parse_args()

    calibration_dirs = [ROOT / d if not Path(d).is_absolute() else Path(d) for d in args.calibration_dirs]
    inputs = load_calibration_dirs(calibration_dirs)
    candidate_map = load_candidate_map(ROOT / args.candidate_csv)
    errors = validate_no_treatment_leakage(inputs.manifests + inputs.metrics)
    if inputs.missing_metric_ids:
        errors.append(f"missing metric rows: {len(inputs.missing_metric_ids)}")
    if inputs.duplicate_metric_ids:
        errors.append(f"duplicate metric IDs: {len(inputs.duplicate_metric_ids)}")

    rows = summarize_tasks(inputs, candidate_map)
    selected = choose_tasks(rows) if not errors else []
    write_csv(ROOT / args.summary_csv, rows)
    if selected and not errors:
        write_yaml(ROOT / args.output_yaml, selected, rows, inputs)
    write_report(ROOT / args.report, selected, rows, errors, inputs)

    print(f"tasks={len(rows)} selected={len(selected)} errors={len(errors)}")
    print(f"wrote {ROOT / args.summary_csv}")
    print(f"wrote {ROOT / args.report}")
    if selected and not errors:
        print(f"wrote {ROOT / args.output_yaml}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
