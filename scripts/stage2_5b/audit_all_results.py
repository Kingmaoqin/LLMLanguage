#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]

JSONL_FILES = [
    "conversation_logs",
    "normalized_tool_events",
    "user_simulator_events",
    "style_wrapper_events",
    "state_deltas",
    "final_environment_states",
    "evidence_events",
    "branch_decisions",
    "policy_failures",
    "termination_reasons",
    "parser_health",
    "adapter_errors",
]

STRICT_STAGE2_5B_REQUIRED = [
    "run_metrics.csv",
    "run_manifest.csv",
    "conversation_logs.jsonl",
    "normalized_tool_events.jsonl",
    "user_simulator_events.jsonl",
    "style_wrapper_events.jsonl",
    "state_deltas.jsonl",
    "final_environment_states.jsonl",
    "evidence_events.jsonl",
    "branch_decisions.jsonl",
    "policy_failures.jsonl",
    "termination_reasons.jsonl",
    "parser_health.jsonl",
]

META_FIELDS = [
    "model_alias",
    "task_id",
    "domain",
    "source_task_id",
    "condition_id",
    "seed",
    "template_block",
    "template_id",
    "temperature",
    "user_sim_model_alias",
    "repeat_id",
]

ID_RE = re.compile(
    r"(#[A-Z]\d+|[A-Z]{2,}\d{2,}|\b\d{5}\b|\b\d{10,}\b|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
)


def parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stable_json_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not path.exists():
        return rows, errors
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append({
                    "file": str(path),
                    "line_no": line_no,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue
            if isinstance(row, dict):
                row["_line_no"] = line_no
                row["_line_hash"] = hashlib.sha256(line.encode("utf-8")).hexdigest()
                rows.append(row)
            else:
                errors.append({
                    "file": str(path),
                    "line_no": line_no,
                    "error": "jsonl row is not an object",
                })
    return rows, errors


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fields: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fields.append(key)
        fieldnames = fields or ["empty"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def by_run(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        run_id = row.get("run_id")
        if run_id:
            out[str(run_id)].append(row)
    return out


def first_by_run(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        run_id = row.get("run_id")
        if run_id and str(run_id) not in out:
            out[str(run_id)] = row
    return out


def count_duplicate_values(values: Iterable[str]) -> dict[str, int]:
    return {k: v for k, v in Counter(values).items() if v > 1}


def add_issue(
    issues: list[dict[str, Any]],
    result_dir: Path,
    severity: str,
    issue_type: str,
    detail: str,
    run_id: str = "",
    file_name: str = "",
) -> None:
    issues.append({
        "result_dir": str(result_dir),
        "severity": severity,
        "issue_type": issue_type,
        "run_id": run_id,
        "file": file_name,
        "detail": detail,
    })


def expected_run_ids(manifest_rows: list[dict[str, str]], metrics_rows: list[dict[str, str]]) -> set[str]:
    if manifest_rows:
        return {r["run_id"] for r in manifest_rows if r.get("run_id")}
    return {r["run_id"] for r in metrics_rows if r.get("run_id")}


def canonical_row(
    result_dir: Path,
    run_id: str,
    manifest: dict[str, str] | None,
    metric: dict[str, str] | None,
    events: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    final = (events["final_environment_states"].get(run_id) or [{}])[-1]
    evidence = (events["evidence_events"].get(run_id) or [{}])[-1]
    parser = (events["parser_health"].get(run_id) or [{}])[-1]
    termination = (events["termination_reasons"].get(run_id) or [{}])[-1]
    conversations = events["conversation_logs"].get(run_id) or []
    tools = events["normalized_tool_events"].get(run_id) or []
    wrappers = events["style_wrapper_events"].get(run_id) or []
    policy_failures = events["policy_failures"].get(run_id) or []
    state_deltas = events["state_deltas"].get(run_id) or []
    branches = events["branch_decisions"].get(run_id) or []

    src = manifest or metric or final or parser or termination or (conversations[0] if conversations else {})
    reward = parse_float(final.get("reward"))
    safe = parse_bool(final.get("safe_task_success"))
    if safe is None and metric is not None:
        safe = parse_bool(metric.get("safe_task_success"))
    final_state_correct = parse_bool(metric.get("final_state_correct") if metric else None)
    if final_state_correct is None and reward is not None:
        final_state_correct = reward == 1.0

    return {
        "result_dir": result_dir.name,
        "run_id": run_id,
        "model_alias": src.get("model_alias", ""),
        "task_id": src.get("task_id", ""),
        "domain": src.get("domain", ""),
        "source_task_id": src.get("source_task_id", ""),
        "condition_id": src.get("condition_id", ""),
        "seed": src.get("seed", ""),
        "repeat_id": src.get("repeat_id", ""),
        "template_block": src.get("template_block", ""),
        "template_id": src.get("template_id", ""),
        "temperature": src.get("temperature", ""),
        "user_sim_model_alias": src.get("user_sim_model_alias", ""),
        "invalid_run": parse_bool(termination.get("invalid_run")) if termination else parse_bool(metric.get("invalid_run") if metric else None),
        "termination_reason": termination.get("termination_reason", metric.get("termination_reason", "") if metric else ""),
        "reward": reward,
        "safe_task_success": safe,
        "final_state_correct": final_state_correct,
        "state_before_hash": final.get("state_before_hash", metric.get("state_before_hash", "") if metric else ""),
        "state_after_hash": final.get("state_after_hash", metric.get("state_after_hash", "") if metric else ""),
        "required_fact_coverage": evidence.get("required_fact_coverage", metric.get("required_fact_coverage", "") if metric else ""),
        "mutation_before_evidence": evidence.get("mutation_before_evidence", metric.get("mutation_before_evidence", "") if metric else ""),
        "n_conversation_rows": len(conversations),
        "n_user_messages": sum(1 for r in conversations if r.get("role") == "user"),
        "n_assistant_messages": sum(1 for r in conversations if r.get("role") == "assistant"),
        "n_tool_events": len(tools),
        "n_state_deltas": len(state_deltas),
        "n_branch_decisions": len(branches),
        "n_policy_failures": len(policy_failures),
        "n_style_wrappers": len(wrappers),
        "parser_n_tool_errors": parser.get("n_tool_errors", ""),
        "parser_n_undefined_tools": parser.get("n_undefined_tools", ""),
        "parser_no_tool_call_emitted": parser.get("no_tool_call_emitted", ""),
        "tool_sequence": " > ".join(str(r.get("tool_name")) for r in tools if r.get("tool_name")),
    }


def audit_cross_file_metadata(
    result_dir: Path,
    manifest_by_id: dict[str, dict[str, str]],
    jsonl_rows_by_file: dict[str, list[dict[str, Any]]],
    reconciliation: list[dict[str, Any]],
) -> None:
    for file_key, rows in jsonl_rows_by_file.items():
        for row in rows:
            run_id = str(row.get("run_id") or "")
            if not run_id or run_id not in manifest_by_id:
                continue
            expected = manifest_by_id[run_id]
            for field in META_FIELDS:
                if field not in row or field not in expected:
                    continue
                if str(row.get(field)) != str(expected.get(field)):
                    reconciliation.append({
                        "result_dir": str(result_dir),
                        "run_id": run_id,
                        "file": f"{file_key}.jsonl",
                        "field": field,
                        "manifest_value": expected.get(field),
                        "event_value": row.get(field),
                        "line_no": row.get("_line_no", ""),
                    })


def audit_directory(result_dir: Path, stage_family: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    reconciliation: list[dict[str, Any]] = []
    canonical: list[dict[str, Any]] = []

    metrics_rows = read_csv(result_dir / "run_metrics.csv")
    manifest_rows = read_csv(result_dir / "run_manifest.csv")
    manifest_by_id = {r["run_id"]: r for r in manifest_rows if r.get("run_id")}
    metrics_by_id = {r["run_id"]: r for r in metrics_rows if r.get("run_id")}
    expected_ids = expected_run_ids(manifest_rows, metrics_rows)

    required = STRICT_STAGE2_5B_REQUIRED if stage_family == "stage2_5" else ["run_metrics.csv", "conversation_logs.jsonl", "normalized_tool_events.jsonl", "final_environment_states.jsonl", "parser_health.jsonl"]
    for name in required:
        if not (result_dir / name).exists():
            severity = "error" if stage_family == "stage2_5" else "warning"
            add_issue(issues, result_dir, severity, "missing_file", f"missing expected file {name}", file_name=name)

    for label, rows in [("run_manifest.csv", manifest_rows), ("run_metrics.csv", metrics_rows)]:
        dupes = count_duplicate_values(r.get("run_id", "") for r in rows if r.get("run_id"))
        for run_id, count in dupes.items():
            add_issue(issues, result_dir, "error", "duplicate_run_id", f"{label} contains {count} rows for run_id", run_id, label)

    if manifest_rows:
        missing_metrics = sorted(set(manifest_by_id) - set(metrics_by_id))
        extra_metrics = sorted(set(metrics_by_id) - set(manifest_by_id))
        for run_id in missing_metrics:
            add_issue(issues, result_dir, "error", "missing_metric_row", "manifest run has no run_metrics row", run_id, "run_metrics.csv")
        for run_id in extra_metrics:
            add_issue(issues, result_dir, "error", "orphan_metric_row", "run_metrics row is not in manifest", run_id, "run_metrics.csv")

    jsonl_rows: dict[str, list[dict[str, Any]]] = {}
    events_by_file_run: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for key in JSONL_FILES:
        path = result_dir / f"{key}.jsonl"
        rows, parse_errors = read_jsonl(path)
        jsonl_rows[key] = rows
        events_by_file_run[key] = by_run(rows)
        for err in parse_errors:
            add_issue(issues, result_dir, "error", "json_parse_error", err["error"], file_name=str(path))
        if path.exists():
            exact_dupes = count_duplicate_values(r["_line_hash"] for r in rows)
            for line_hash, count in exact_dupes.items():
                add_issue(issues, result_dir, "warning", "duplicate_jsonl_line", f"{count} exact duplicate JSONL lines with hash {line_hash}", file_name=f"{key}.jsonl")
        for run_id in set(events_by_file_run[key]) - expected_ids:
            add_issue(issues, result_dir, "error", "orphan_event", f"{key}.jsonl contains run_id outside manifest/metrics", run_id, f"{key}.jsonl")

    audit_cross_file_metadata(result_dir, manifest_by_id, jsonl_rows, reconciliation)

    terminal_ids = set(events_by_file_run["termination_reasons"])
    if (result_dir / "termination_reasons.jsonl").exists():
        for run_id in sorted(expected_ids - terminal_ids):
            add_issue(issues, result_dir, "error", "missing_terminal_record", "expected run has no termination_reasons row", run_id, "termination_reasons.jsonl")
    else:
        for run_id in sorted(expected_ids):
            add_issue(issues, result_dir, "warning", "missing_terminal_file", "termination_reasons.jsonl absent; cannot verify terminal row", run_id, "termination_reasons.jsonl")

    conversations_by_id = events_by_file_run["conversation_logs"]
    for run_id in sorted(expected_ids):
        if not conversations_by_id.get(run_id):
            add_issue(issues, result_dir, "error", "empty_conversation", "expected run has no conversation rows", run_id, "conversation_logs.jsonl")

    for run_id, metric in metrics_by_id.items():
        invalid = parse_bool(metric.get("invalid_run"))
        term = (events_by_file_run["termination_reasons"].get(run_id) or [{}])[-1]
        if invalid and not term:
            add_issue(issues, result_dir, "error", "silent_failed_run", "run_metrics marks invalid but no terminal reason row exists", run_id)
        if metric.get("exception") and run_id not in metrics_by_id:
            add_issue(issues, result_dir, "error", "exception_not_retained", "exception surfaced without retained metric row", run_id)

    final_by_id = first_by_run(jsonl_rows["final_environment_states"])
    first_tool_by_id = first_by_run(jsonl_rows["normalized_tool_events"])
    for run_id, final in final_by_id.items():
        first_tool = first_tool_by_id.get(run_id)
        if first_tool and final.get("state_before_hash") and first_tool.get("state_before_hash") and final.get("state_before_hash") != first_tool.get("state_before_hash"):
            add_issue(issues, result_dir, "error", "initial_state_mismatch", "final_environment_states state_before_hash differs from first tool event", run_id)

    initial_by_task: dict[tuple[str, str], set[str]] = defaultdict(set)
    for run_id in expected_ids:
        source = metrics_by_id.get(run_id) or manifest_by_id.get(run_id) or final_by_id.get(run_id) or {}
        final = final_by_id.get(run_id) or {}
        h = final.get("state_before_hash") or source.get("state_before_hash")
        if h:
            initial_by_task[(str(source.get("domain", "")), str(source.get("task_id", "")))].add(str(h))
    for (domain, task_id), hashes in initial_by_task.items():
        if len(hashes) > 1:
            add_issue(issues, result_dir, "error", "initial_state_hash_variance", f"{domain}/{task_id} has {len(hashes)} initial hashes: {sorted(hashes)}")

    config_hash_fields = [f for f in ("config_hash", "task_set_hash", "template_hash", "benchmark_hash") if any(f in r for r in metrics_rows + manifest_rows)]
    if not config_hash_fields and stage_family == "stage2_5":
        add_issue(issues, result_dir, "warning", "config_hash_missing", "no config/task/template/benchmark hash fields found in manifest or metrics")
    for field in config_hash_fields:
        vals = {str(r.get(field)) for r in metrics_rows + manifest_rows if r.get(field)}
        if len(vals) > 1:
            add_issue(issues, result_dir, "error", "config_hash_mismatch", f"{field} has multiple values: {sorted(vals)}")

    for run_id in sorted(expected_ids):
        canonical.append(canonical_row(result_dir, run_id, manifest_by_id.get(run_id), metrics_by_id.get(run_id), events_by_file_run))

    summary = {
        "result_dir": str(result_dir),
        "stage_family": stage_family,
        "n_manifest_rows": len(manifest_rows),
        "n_metric_rows": len(metrics_rows),
        "n_expected_runs": len(expected_ids),
        "n_canonical_rows": len(canonical),
        "n_issues": len(issues),
        "n_error_issues": sum(1 for i in issues if i["severity"] == "error"),
        "n_reconciliation_rows": len(reconciliation),
    }
    return canonical, issues, reconciliation, summary


def audit_wrapper_schedule(canonical_rows: list[dict[str, Any]], jsonl_cache: dict[str, dict[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    canonical_by_dir_run = {(r["result_dir"], r["run_id"]): r for r in canonical_rows}
    for result_dir_name, by_file in jsonl_cache.items():
        wrappers_by_run = by_file.get("style_wrapper_events", {})
        user_by_run = by_file.get("user_simulator_events", {})
        for run_key, canonical in sorted(canonical_by_dir_run.items()):
            if run_key[0] != result_dir_name:
                continue
            run_id = run_key[1]
            condition = str(canonical.get("condition_id") or "")
            wrappers = wrappers_by_run.get(run_id, [])
            wrapped = [w for w in wrappers if parse_bool(w.get("wrapped")) is not False]
            user = (user_by_run.get(run_id) or [{}])[-1]
            n_user_turns = parse_float(user.get("n_user_turns_seen"))
            idxs = sorted({int(w.get("user_turn_idx")) for w in wrapped if str(w.get("user_turn_idx", "")).isdigit()})
            schedule_class = "unknown"
            ok = True
            problem = ""
            if condition.endswith("_single"):
                schedule_class = "first_turn_only"
                ok = len(idxs) <= 1 and (not idxs or idxs == [0])
                if not ok:
                    problem = "single condition wrapped turns other than first natural user turn"
            elif condition.endswith("_repeated") or condition in {"repeated_abuse", "repeated_praise"}:
                schedule_class = "every_user_turn"
                if n_user_turns is not None and wrapped:
                    ok = len(idxs) <= int(n_user_turns) and (not idxs or min(idxs) == 0)
                if not ok:
                    problem = "repeated condition wrapper index inconsistent with user turns"
            rows.append({
                "result_dir": result_dir_name,
                "run_id": run_id,
                "condition_id": condition,
                "schedule_class": schedule_class,
                "n_wrapper_events": len(wrappers),
                "n_wrapped_events": len(wrapped),
                "wrapped_user_turn_indices": "|".join(str(i) for i in idxs),
                "n_user_turns_seen": int(n_user_turns) if n_user_turns is not None else "",
                "schedule_ok": ok,
                "problem": problem,
            })
    return rows


def audit_user_sim_drift(jsonl_cache: dict[str, dict[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result_dir_name, by_file in jsonl_cache.items():
        user_rows = [r for group in by_file.get("user_simulator_events", {}).values() for r in group]
        groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in user_rows:
            key = (
                row.get("model_alias"),
                row.get("task_id"),
                row.get("seed", row.get("repeat_id", "")),
                row.get("template_block", ""),
            )
            groups[key].append(row)
        for key, group in sorted(groups.items(), key=lambda item: str(item[0])):
            signatures = {str(g.get("clean_user_signature", "")) for g in group if g.get("clean_user_signature")}
            ids_by_condition = {
                str(g.get("condition_id")): sorted(set(ID_RE.findall(str(g.get("clean_user_text", "")))))
                for g in group
            }
            id_sets = {tuple(v) for v in ids_by_condition.values()}
            rows.append({
                "result_dir": result_dir_name,
                "model_alias": key[0],
                "task_id": key[1],
                "seed_or_repeat": key[2],
                "template_block": key[3],
                "n_conditions": len({g.get("condition_id") for g in group}),
                "n_user_events": len(group),
                "n_clean_signatures": len(signatures),
                "clean_signature_drift": len(signatures) > 1,
                "n_id_sets": len(id_sets),
                "object_id_drift": len(id_sets) > 1,
                "conditions": "|".join(sorted(str(g.get("condition_id")) for g in group)),
                "signatures": "|".join(sorted(signatures)),
                "ids_by_condition": json.dumps(ids_by_condition, ensure_ascii=False, sort_keys=True),
            })
    return rows


def load_jsonl_cache(result_dirs: list[Path]) -> dict[str, dict[str, dict[str, list[dict[str, Any]]]]]:
    cache: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}
    for result_dir in result_dirs:
        by_file: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for key in JSONL_FILES:
            rows, _ = read_jsonl(result_dir / f"{key}.jsonl")
            by_file[key] = by_run(rows)
        cache[result_dir.name] = by_file
    return cache


def discover_stage2_5_dirs(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return sorted([p for p in base.iterdir() if p.is_dir() and (p / "run_metrics.csv").exists()])


def write_reports(
    report_dir: Path,
    audit_dir: Path,
    summaries: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    drift_rows: list[dict[str, Any]],
) -> None:
    by_severity = Counter(row["severity"] for row in issues)
    by_type = Counter(row["issue_type"] for row in issues)
    lines = [
        "# Integrity Findings",
        "",
        "## Scope",
        "",
        "This audit reads raw CSV/JSONL artifacts directly. It does not rely on prior Markdown reports and does not modify legacy result directories.",
        "",
        "## Directory Summary",
        "",
        "| Directory | Family | Manifest Rows | Metric Rows | Expected Runs | Canonical Rows | Errors | Issues |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        lines.append(
            f"| `{s['result_dir']}` | {s['stage_family']} | {s['n_manifest_rows']} | {s['n_metric_rows']} | {s['n_expected_runs']} | {s['n_canonical_rows']} | {s['n_error_issues']} | {s['n_issues']} |"
        )
    lines.extend(["", "## Issue Counts", ""])
    for key, count in sorted(by_severity.items()):
        lines.append(f"- {key}: {count}")
    lines.append("")
    for key, count in sorted(by_type.items()):
        lines.append(f"- {key}: {count}")
    clean_full = [
        s for s in summaries
        if s["stage_family"] == "stage2_5"
        and Path(str(s["result_dir"])).name.startswith("full_")
        and int(s["n_error_issues"]) == 0
        and int(s["n_metric_rows"]) == int(s["n_expected_runs"])
    ]
    broken_full = [
        s for s in summaries
        if s["stage_family"] == "stage2_5"
        and Path(str(s["result_dir"])).name.startswith("full_")
        and (int(s["n_error_issues"]) > 0 or int(s["n_metric_rows"]) != int(s["n_expected_runs"]))
    ]
    lines.extend(["", "## Stage-2.5 Formal Directory Status", ""])
    if clean_full:
        lines.append("Clean full directories suitable for historical Stage-2.5 pilot summaries:")
        for s in clean_full:
            lines.append(f"- `{s['result_dir']}`: {s['n_metric_rows']}/{s['n_expected_runs']} rows, {s['n_error_issues']} errors")
    if broken_full:
        lines.append("")
        lines.append("Broken/incomplete full directories that must not be used as formal evidence:")
        for s in broken_full:
            lines.append(f"- `{s['result_dir']}`: {s['n_metric_rows']}/{s['n_expected_runs']} rows, {s['n_error_issues']} errors")
    lines.extend(
        [
            "",
            "## Required Outputs",
            "",
            f"- `results/stage2_5b_audit/legacy_stage2_canonical_metrics.csv`",
            f"- `results/stage2_5b_audit/stage2_5_canonical_metrics.csv`",
            f"- `results/stage2_5b_audit/stage2_5_formal_clean_canonical_metrics.csv`",
            f"- `results/stage2_5b_audit/integrity_issues.csv`",
            f"- `results/stage2_5b_audit/cross_file_reconciliation.csv`",
            f"- `results/stage2_5b_audit/wrapper_schedule_audit.csv`",
            f"- `results/stage2_5b_audit/user_sim_drift.csv`",
            "",
            "## Interpretation",
            "",
            "Stage-2 Mini remains exploratory/confound-discovery pilot data. Stage-2.5 remains causal-repair pilot data because it used an LLM user simulator; user simulator drift rows quantify that risk rather than eliminating it.",
        ]
    )
    (report_dir / "INTEGRITY_FINDINGS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    drift_count = sum(1 for row in drift_rows if str(row.get("clean_signature_drift")).lower() == "true")
    id_drift_count = sum(1 for row in drift_rows if str(row.get("object_id_drift")).lower() == "true")
    drift_lines = [
        "# Legacy User Simulator Drift Audit",
        "",
        "This audit groups Stage-2.5 LLM user-simulator rows by matched model/task/seed-or-repeat/template block and compares clean-user signatures and extracted object identifiers across conditions.",
        "",
        f"- groups audited: {len(drift_rows)}",
        f"- groups with clean signature drift: {drift_count}",
        f"- groups with extracted object-id drift: {id_drift_count}",
        "",
        "These results do not convert old LLM user-sim runs into strict causal evidence. They document why Stage-2.5b must use a deterministic controlled user.",
        "",
        f"Detailed CSV: `{audit_dir / 'user_sim_drift.csv'}`",
    ]
    (report_dir / "LEGACY_USER_SIM_DRIFT_AUDIT.md").write_text("\n".join(drift_lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-dir", default=str(ROOT / "results" / "stage2_mini"))
    ap.add_argument("--stage2-5-root", default=str(ROOT / "results" / "stage2_5_repair"))
    ap.add_argument("--audit-dir", default=str(ROOT / "results" / "stage2_5b_audit"))
    ap.add_argument("--report-dir", default=str(ROOT / "reports" / "stage2_5b"))
    args = ap.parse_args()

    audit_dir = Path(args.audit_dir)
    report_dir = Path(args.report_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    legacy_dir = Path(args.legacy_dir)
    stage2_5_dirs = discover_stage2_5_dirs(Path(args.stage2_5_root))
    all_dirs = [legacy_dir, *stage2_5_dirs]

    all_issues: list[dict[str, Any]] = []
    all_reconciliation: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    legacy_canonical: list[dict[str, Any]] = []
    stage2_5_canonical: list[dict[str, Any]] = []

    for result_dir in all_dirs:
        family = "legacy_stage2" if result_dir == legacy_dir else "stage2_5"
        canonical, issues, reconciliation, summary = audit_directory(result_dir, family)
        summaries.append(summary)
        all_issues.extend(issues)
        all_reconciliation.extend(reconciliation)
        if family == "legacy_stage2":
            legacy_canonical.extend(canonical)
        else:
            stage2_5_canonical.extend(canonical)

    jsonl_cache = load_jsonl_cache(all_dirs)
    wrapper_rows = audit_wrapper_schedule([*legacy_canonical, *stage2_5_canonical], jsonl_cache)
    drift_rows = audit_user_sim_drift(jsonl_cache)

    write_csv(audit_dir / "legacy_stage2_canonical_metrics.csv", legacy_canonical)
    write_csv(audit_dir / "stage2_5_canonical_metrics.csv", stage2_5_canonical)
    formal_clean = [
        r for r in stage2_5_canonical
        if r.get("result_dir") in {"full_gemma_v2", "full_gpt_oss"}
    ]
    write_csv(audit_dir / "stage2_5_formal_clean_canonical_metrics.csv", formal_clean)
    write_csv(audit_dir / "integrity_issues.csv", all_issues)
    write_csv(audit_dir / "cross_file_reconciliation.csv", all_reconciliation)
    write_csv(audit_dir / "wrapper_schedule_audit.csv", wrapper_rows)
    write_csv(audit_dir / "user_sim_drift.csv", drift_rows)
    write_csv(audit_dir / "directory_summary.csv", summaries)
    write_reports(report_dir, audit_dir, summaries, all_issues, drift_rows)

    print(f"legacy canonical rows: {len(legacy_canonical)}")
    print(f"stage2.5 canonical rows: {len(stage2_5_canonical)}")
    print(f"issues: {len(all_issues)}")
    print(f"reconciliation rows: {len(all_reconciliation)}")
    print(f"audit dir: {audit_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
