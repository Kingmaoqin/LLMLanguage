"""Final integrity audit for the atomic Stage-2.5b confirmatory result root."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVENT_FILES = [
    "conversation_logs",
    "normalized_tool_events",
    "controlled_user_events",
    "style_wrapper_events",
    "state_deltas",
    "invalid_tool_calls",
    "evidence_events",
    "branch_decisions",
    "policy_failures",
    "termination_reasons",
    "parser_health",
    "final_environment_states",
    "adapter_errors",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return rows


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default="results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic",
    )
    parser.add_argument(
        "--csv",
        default="results/stage2_5b_repair/final_integrity_report.csv",
    )
    parser.add_argument(
        "--report",
        default="reports/stage2_5b/FINAL_INTEGRITY_AUDIT.md",
    )
    args = parser.parse_args()

    result_root = ROOT / args.root
    contract = json.loads((result_root / "FULL_RUN_CONTRACT.json").read_text(encoding="utf-8"))
    expected_runs = int(contract["expected_runs"])
    expected_hashes = contract["runtime_hashes"]
    expected_jobs = {
        (job["model_alias"], job["task_id"]): job
        for job in contract["jobs"]
    }
    detail_rows: list[dict[str, Any]] = []
    global_errors: list[str] = []
    all_manifest: list[dict[str, str]] = []
    all_metrics: list[dict[str, str]] = []
    all_events: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for key, job in sorted(expected_jobs.items()):
        model, task = key
        block = result_root / f"{model}__{task}"
        manifest = read_csv(block / "run_manifest.csv")
        metrics = read_csv(block / "run_metrics.csv")
        block_contract_path = block / "run_contract.json"
        block_contract = (
            json.loads(block_contract_path.read_text(encoding="utf-8"))
            if block_contract_path.exists()
            else {}
        )
        bundles = sorted((block / "run_bundles").glob("*.json")) if (block / "run_bundles").exists() else []
        manifest_ids = [row.get("run_id", "") for row in manifest]
        metric_ids = [row.get("run_id", "") for row in metrics]
        bundle_ids = []
        bundle_hash_mismatches = 0
        for bundle_path in bundles:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            run_meta = bundle.get("run_meta") or {}
            bundle_ids.append(str(run_meta.get("run_id", "")))
            bundle_hash_mismatches += sum(
                run_meta.get(field, "") != expected
                for field, expected in expected_hashes.items()
            )
        errors = []
        if not block_contract:
            errors.append("missing_run_contract")
        else:
            if block_contract.get("runtime_hashes") != expected_hashes:
                errors.append("run_contract_hash_mismatch")
            if block_contract.get("model_aliases") != [model] or block_contract.get("task_ids") != [task]:
                errors.append("run_contract_block_mismatch")
            if block_contract.get("deployment_ids") != [job["deployment_id"]]:
                errors.append("run_contract_deployment_mismatch")
        if len(manifest) != 30:
            errors.append(f"manifest={len(manifest)}")
        if len(metrics) != 30:
            errors.append(f"metrics={len(metrics)}")
        if len(bundles) != 30:
            errors.append(f"bundles={len(bundles)}")
        if len(set(manifest_ids)) != len(manifest_ids):
            errors.append("duplicate_manifest_ids")
        if len(set(metric_ids)) != len(metric_ids):
            errors.append("duplicate_metric_ids")
        if set(manifest_ids) != set(metric_ids) or set(metric_ids) != set(bundle_ids):
            errors.append("manifest_metric_bundle_id_mismatch")
        hash_mismatches = 0
        for field, expected in expected_hashes.items():
            if {row.get(field, "") for row in metrics} not in ({expected}, set()):
                hash_mismatches += 1
            if {row.get(field, "") for row in manifest} not in ({expected}, set()):
                hash_mismatches += 1
        if hash_mismatches:
            errors.append(f"hash_mismatches={hash_mismatches}")
        if bundle_hash_mismatches:
            errors.append(f"bundle_hash_mismatches={bundle_hash_mismatches}")
        if {row.get("deployment_id", "") for row in metrics} not in ({job["deployment_id"]}, set()):
            errors.append("deployment_mismatch")
        invalid_ids = {row["run_id"] for row in metrics if truthy(row.get("invalid_run"))}
        valid_ids = set(metric_ids) - invalid_ids
        terminal_rows = read_jsonl(block / "termination_reasons.jsonl")
        final_rows = read_jsonl(block / "final_environment_states.jsonl")
        parser_rows = read_jsonl(block / "parser_health.jsonl")
        terminal = {row.get("run_id", "") for row in terminal_rows}
        final = {row.get("run_id", "") for row in final_rows}
        parser_ids = {row.get("run_id", "") for row in parser_rows}
        if terminal != set(metric_ids):
            errors.append("termination_id_mismatch")
        if len(terminal_rows) != len(metric_ids):
            errors.append("termination_record_count_mismatch")
        if any(not str(row.get("termination_reason", "")).strip() for row in terminal_rows):
            errors.append("missing_termination_reason")
        if final != valid_ids:
            errors.append("final_state_id_mismatch")
        if len(final_rows) != len(valid_ids):
            errors.append("final_state_record_count_mismatch")
        if parser_ids != valid_ids:
            errors.append("parser_id_mismatch")
        if len(parser_rows) != len(valid_ids):
            errors.append("parser_record_count_mismatch")
        orphan_events = 0
        for event_name in EVENT_FILES:
            rows = read_jsonl(block / f"{event_name}.jsonl")
            all_events[event_name].extend(rows)
            orphan_events += sum(row.get("run_id", "") not in set(manifest_ids) for row in rows)
        if orphan_events:
            errors.append(f"orphan_events={orphan_events}")
        detail_rows.append({
            "scope": "block",
            "model_alias": model,
            "task_id": task,
            "manifest_rows": len(manifest),
            "metric_rows": len(metrics),
            "bundle_rows": len(bundles),
            "valid_runs": len(valid_ids),
            "invalid_runs": len(invalid_ids),
            "status": "PASS" if not errors else "FAIL",
            "errors": " | ".join(errors),
        })
        all_manifest.extend(manifest)
        all_metrics.extend(metrics)

    manifest_ids = [row.get("run_id", "") for row in all_manifest]
    metric_ids = [row.get("run_id", "") for row in all_metrics]
    if len(all_manifest) != expected_runs:
        global_errors.append(f"manifest rows {len(all_manifest)} != {expected_runs}")
    if len(all_metrics) != expected_runs:
        global_errors.append(f"metric rows {len(all_metrics)} != {expected_runs}")
    if len(set(manifest_ids)) != expected_runs:
        global_errors.append(f"unique manifest IDs {len(set(manifest_ids))} != {expected_runs}")
    if len(set(metric_ids)) != expected_runs:
        global_errors.append(f"unique metric IDs {len(set(metric_ids))} != {expected_runs}")
    if set(manifest_ids) != set(metric_ids):
        global_errors.append("global manifest/metric ID mismatch")

    invalid = [row for row in all_metrics if truthy(row.get("invalid_run"))]
    valid = [row for row in all_metrics if not truthy(row.get("invalid_run"))]
    condition_counts = Counter(row.get("condition_id", "") for row in all_metrics)
    model_counts = Counter(row.get("model_alias", "") for row in all_metrics)
    task_counts = Counter(row.get("task_id", "") for row in all_metrics)
    seed_counts = Counter(row.get("seed", "") for row in all_metrics)
    if set(condition_counts.values()) != {80}:
        global_errors.append(f"condition imbalance: {dict(condition_counts)}")
    if set(model_counts.values()) != {240}:
        global_errors.append(f"model imbalance: {dict(model_counts)}")
    if set(task_counts.values()) != {60}:
        global_errors.append(f"task imbalance: {dict(task_counts)}")
    if set(seed_counts.values()) != {96}:
        global_errors.append(f"seed imbalance: {dict(seed_counts)}")

    valid_ids = {row["run_id"] for row in valid}
    initial_hashes: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in valid:
        initial_hashes[(row["model_alias"], row["task_id"], row["seed"])].add(row.get("state_before_hash", ""))
    drift_groups = [key for key, values in initial_hashes.items() if len(values) != 1]
    if drift_groups:
        global_errors.append(f"initial-state drift groups={len(drift_groups)}")

    controlled_openings: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    controlled_opening_conditions: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    controlled_opening_run_ids: list[str] = []
    for row in all_events["controlled_user_events"]:
        if row.get("run_id") in valid_ids and row.get("user_state") == "turn_0":
            group = (str(row["model_alias"]), str(row["task_id"]), str(row["seed"]))
            controlled_openings[group].add(
                str(row.get("clean_text_hash", ""))
            )
            controlled_opening_conditions[group].add(str(row.get("condition_id", "")))
            controlled_opening_run_ids.append(str(row.get("run_id", "")))
    user_drift = [key for key, values in controlled_openings.items() if len(values) != 1]
    if user_drift:
        global_errors.append(f"controlled-user opening drift groups={len(user_drift)}")
    if set(controlled_opening_run_ids) != valid_ids:
        global_errors.append("controlled-user opening run coverage mismatch")
    if len(controlled_opening_run_ids) != len(valid_ids):
        global_errors.append("controlled-user opening duplicate/missing records")
    expected_valid_conditions: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in valid:
        expected_valid_conditions[
            (row["model_alias"], row["task_id"], row["seed"])
        ].add(row["condition_id"])
    if set(initial_hashes) != set(expected_valid_conditions):
        global_errors.append("initial-state group coverage mismatch")
    if set(controlled_openings) != set(expected_valid_conditions):
        global_errors.append("controlled-user group coverage mismatch")
    user_condition_mismatches = [
        key
        for key, expected in expected_valid_conditions.items()
        if controlled_opening_conditions.get(key, set()) != expected
    ]
    if user_condition_mismatches:
        global_errors.append(
            f"controlled-user condition coverage mismatches={len(user_condition_mismatches)}"
        )

    detail_rows.append({
        "scope": "global",
        "model_alias": "",
        "task_id": "",
        "manifest_rows": len(all_manifest),
        "metric_rows": len(all_metrics),
        "bundle_rows": sum(int(row["bundle_rows"]) for row in detail_rows if row["scope"] == "block"),
        "valid_runs": len(valid),
        "invalid_runs": len(invalid),
        "status": "PASS" if not global_errors and all(row["status"] == "PASS" for row in detail_rows) else "FAIL",
        "errors": " | ".join(global_errors),
    })
    write_csv(ROOT / args.csv, detail_rows)

    status = detail_rows[-1]["status"]
    invalid_by_condition = Counter(row["condition_id"] for row in invalid)
    invalid_by_model = Counter(row["model_alias"] for row in invalid)
    lines = [
        "# Stage-2.5b Final Integrity Audit",
        "",
        f"Status: **{status}**",
        "",
        "## Global accounting",
        "",
        f"- Expected runs: {expected_runs}",
        f"- Manifest rows: {len(all_manifest)}",
        f"- Metric rows: {len(all_metrics)}",
        f"- Unique run IDs: {len(set(metric_ids))}",
        f"- Valid behavioral runs: {len(valid)}",
        f"- Retained invalid/infrastructure runs: {len(invalid)}",
        f"- Duplicate run IDs: {len(metric_ids) - len(set(metric_ids))}",
        f"- Initial-state drift groups: {len(drift_groups)}",
        f"- Initial-state groups covered: {len(initial_hashes)}",
        f"- Controlled-user opening drift groups: {len(user_drift)}",
        f"- Controlled-user valid-run openings: {len(controlled_opening_run_ids)}",
        "",
        "## Balance",
        "",
        f"- By model: `{dict(model_counts)}`",
        f"- By condition: `{dict(condition_counts)}`",
        f"- By task: `{dict(task_counts)}`",
        f"- By seed: `{dict(seed_counts)}`",
        "",
        "## Invalid runs",
        "",
        f"- By model: `{dict(invalid_by_model)}`",
        f"- By condition: `{dict(invalid_by_condition)}`",
    ]
    for row in invalid:
        lines.append(
            f"- `{row['run_id']}` — `{row.get('termination_reason', '')}`; retained in the 480-run denominator."
        )
    lines.extend([
        "",
        "## Block results",
        "",
        "| Model | Task | Metrics | Valid | Invalid | Status |",
        "|---|---|---:|---:|---:|---|",
    ])
    for row in detail_rows[:-1]:
        lines.append(
            f"| {row['model_alias']} | {row['task_id']} | {row['metric_rows']} | "
            f"{row['valid_runs']} | {row['invalid_runs']} | {row['status']} |"
        )
    if global_errors:
        lines.extend(["", "## Errors", "", *[f"- {error}" for error in global_errors]])
    lines.extend([
        "",
        "## Gate decision",
        "",
        (
            "G11_FINAL_INTEGRITY_PASS. Behavioral analyses use valid runs; the retained invalid "
            "run is reported separately and is not reclassified as model behavior."
            if status == "PASS"
            else "G11_FINAL_INTEGRITY_FAIL. Confirmatory analysis is blocked."
        ),
        "",
    ])
    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"{status}: metrics={len(all_metrics)} valid={len(valid)} invalid={len(invalid)}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
