"""Stage-2.5b controlled-user experiment runner."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.instrument import ToolEventRecorder
from src.adapters.normalize import IRREVERSIBLE_TOOLS, extract_metrics, normalized_tool_events, parser_health
from src.stage2_5b.branch_evaluator import evaluate_branches
from src.stage2_5b.controlled_user import (
    ControlledUser,
    TASK_POLICIES,
    stable_text_hash,
)
from src.stage2_5b.evidence_graph import evaluate_evidence
from src.stage2_5b.evaluator import (
    evaluate_conversation_management,
    evaluate_policy_failures,
    official_reward_metrics,
    safe_success_metrics,
)
from src.stage2_5b.social_style_wrapper import (
    load_style_templates,
    template_by_id,
    template_ids,
)
from src.stage2_5b.trajectory_metrics import trajectory_summary


JSONL_OUTPUTS = [
    "normalized_tool_events",
    "raw_model_outputs",
    "conversation_logs",
    "state_deltas",
    "invalid_tool_calls",
    "parser_health",
    "controlled_user_events",
    "style_wrapper_events",
    "final_environment_states",
    "evidence_events",
    "branch_decisions",
    "policy_failures",
    "termination_reasons",
    "user_simulator_events",
    "adapter_errors",
]

HASH_FIELDS = [
    "config_hash",
    "model_config_hash",
    "tasks_config_hash",
    "task_set_hash",
    "template_hash",
    "policy_annotation_hash",
    "controlled_user_hash",
    "evaluator_hash",
    "source_bundle_hash",
    "benchmark_manifest_hash",
    "git_commit",
]

RUNTIME_SOURCE_PATHS = [
    ROOT / "scripts" / "stage2_5b" / "run_stage2_5b_experiment.py",
    ROOT / "src" / "adapters" / "instrument.py",
    ROOT / "src" / "adapters" / "normalize.py",
    ROOT / "src" / "stage2_5b" / "evaluator.py",
    ROOT / "src" / "stage2_5b" / "evidence_graph.py",
    ROOT / "src" / "stage2_5b" / "branch_evaluator.py",
    ROOT / "src" / "stage2_5" / "conversation_management_evaluator.py",
    ROOT / "src" / "stage2_5b" / "social_style_wrapper.py",
    ROOT / "src" / "stage2_5b" / "trajectory_metrics.py",
    ROOT / "src" / "stage2_5b" / "controlled_user.py",
    ROOT / "src" / "stage2_5b" / "user_policy.py",
    ROOT / "src" / "stage2_5b" / "response_library.py",
    ROOT / "data" / "stage2_5b" / "task_user_policies.yaml",
    ROOT / "data" / "stage2_5b" / "user_response_library.yaml",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _combined_hash(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in paths:
        h.update(str(path.relative_to(ROOT)).encode("utf-8"))
        h.update(_sha256(path).encode("utf-8"))
    return h.hexdigest()


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "NO_GIT_COMMIT"


def runtime_hashes_for_config(config_path: Path) -> dict[str, str]:
    cfg = _load_yaml(config_path)
    model_path = ROOT / cfg["paths"]["models"]
    tasks_path = ROOT / cfg["paths"]["tasks"]
    tasks_cfg = _load_yaml(tasks_path)
    task_set_path = ROOT / tasks_cfg["confirmatory_task_file"]
    template_path = ROOT / cfg["paths"]["templates"]
    policy_path = ROOT / cfg["paths"]["task_policy_annotations"]
    benchmark_manifest = ROOT / cfg["paths"]["benchmark_manifest"]
    evaluator_paths = [
        ROOT / "src" / "stage2_5b" / "evaluator.py",
        ROOT / "src" / "stage2_5b" / "evidence_graph.py",
        ROOT / "src" / "stage2_5b" / "branch_evaluator.py",
        ROOT / "src" / "stage2_5b" / "trajectory_metrics.py",
    ]
    return {
        "config_hash": _sha256(config_path),
        "model_config_hash": _sha256(model_path),
        "tasks_config_hash": _sha256(tasks_path),
        "task_set_hash": _sha256(task_set_path) if task_set_path.exists() else "MISSING",
        "template_hash": _sha256(template_path),
        "policy_annotation_hash": _sha256(policy_path),
        "controlled_user_hash": _combined_hash([
            ROOT / "src" / "stage2_5b" / "controlled_user.py",
            ROOT / "src" / "stage2_5b" / "user_policy.py",
            ROOT / "src" / "stage2_5b" / "response_library.py",
            ROOT / "data" / "stage2_5b" / "task_user_policies.yaml",
            ROOT / "data" / "stage2_5b" / "user_response_library.yaml",
        ]),
        "evaluator_hash": _combined_hash(evaluator_paths),
        "source_bundle_hash": _combined_hash(RUNTIME_SOURCE_PATHS),
        "benchmark_manifest_hash": _sha256(benchmark_manifest) if benchmark_manifest.exists() else "MISSING",
        "git_commit": _git_commit(),
    }


def _llm_args(model: dict[str, Any], temperature: float) -> dict[str, Any]:
    return {
        "api_base": model["base_url"],
        "api_key": model.get("api_key", "EMPTY"),
        "temperature": temperature,
    }


def _endpoint_ok(model: dict[str, Any], timeout: float = 5.0) -> tuple[bool, str]:
    url = model["base_url"].rstrip("/") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        ids = [m.get("id") for m in payload.get("data", [])]
        served_id = model.get("served_id")
        if served_id and served_id not in ids:
            return False, f"served_id {served_id!r} not in endpoint ids {ids!r}"
        return True, f"ok ids={ids!r}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _preflight(models: list[dict[str, Any]], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# Stage-2.5b Endpoint Preflight", ""]
    failures = []
    for model in models:
        ok, detail = _endpoint_ok(model)
        lines.append(f"- {model['alias']}: {'PASS' if ok else 'FAIL'} - {detail}")
        if not ok:
            failures.append(model["alias"])
    (report_dir / "MODEL_AND_ADAPTER_PREFLIGHT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(f"endpoint preflight failed for {failures}")


def _jsonable_message(run_meta: dict[str, Any], message: Any) -> dict[str, Any]:
    try:
        payload = message.model_dump(mode="json")
    except Exception:
        payload = {"repr": repr(message)}
    return {**run_meta, **payload}


def _conversation_row(run_meta: dict[str, Any], message: Any) -> dict[str, Any]:
    return {
        **run_meta,
        "role": getattr(message, "role", None),
        "content": getattr(message, "content", None),
        "tool_calls": [tc.name for tc in (getattr(message, "tool_calls", None) or [])],
        "turn_idx": getattr(message, "turn_idx", None),
    }


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _load_metrics(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    preferred = [
        "stage", "run_id", "model_alias", "task_id", "domain", "source_task_id",
        "condition_id", "seed", "template_block", "template_id", "temperature",
        "controlled_user_policy", "deployment_id", "deployment_base_url",
        "invalid_run", "safe_task_success",
        "official_reward_basis_success", "local_proxy_success",
        "final_state_correct", "reward",
        "required_fact_coverage", "mutation_before_evidence",
        "n_policy_failures", "policy_failure_types", "agent_tool_calls",
        "tool_name_sequence_distance", "critical_argument_sequence_distance",
        "mutation_sequence_distance", "irreversible_actions", "termination_reason",
        *HASH_FIELDS,
    ]
    fields = list({k for row in rows for k in row})
    ordered = [f for f in preferred if f in fields] + sorted(f for f in fields if f not in preferred)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered)
        writer.writeheader()
        writer.writerows(rows)


def _write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id", "model_alias", "task_id", "condition_id", "seed",
        "template_block", "template_id", "temperature", "controlled_user_policy",
        "deployment_id", "deployment_base_url",
        *HASH_FIELDS,
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{k: row.get(k) for k in fields} for row in rows])


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _normalized_csv_rows(rows: list[dict[str, Any]], fields: list[str]) -> list[dict[str, str]]:
    return [{field: str(row.get(field, "")) for field in fields} for row in rows]


def _ensure_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id", "model_alias", "task_id", "condition_id", "seed",
        "template_block", "template_id", "temperature", "controlled_user_policy",
        "deployment_id", "deployment_base_url",
        *HASH_FIELDS,
    ]
    if path.exists():
        existing = _normalized_csv_rows(_read_csv(path), fields)
        expected = _normalized_csv_rows(rows, fields)
        if existing != expected:
            raise SystemExit(f"refusing to overwrite mismatched manifest: {path}")
        return
    _write_manifest(path, rows)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _ensure_run_contract(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise SystemExit(f"run contract mismatch; use a new output directory: {path}")
        return
    _atomic_write_json(path, payload)


def _bundle_path(bundle_dir: Path, run_id: str) -> Path:
    return bundle_dir / f"{_sanitize_name(run_id)}.json"


def _load_bundle(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "metrics" not in payload or "run_meta" not in payload:
        raise SystemExit(f"invalid run bundle: {path}")
    return payload


def _validate_bundle(bundle: dict[str, Any], manifest_by_id: dict[str, dict[str, Any]]) -> None:
    run_meta = bundle["run_meta"]
    run_id = str(run_meta.get("run_id", ""))
    if run_id not in manifest_by_id:
        raise SystemExit(f"orphan run bundle: {run_id}")
    manifest = manifest_by_id[run_id]
    for key in [
        "model_alias", "task_id", "condition_id", "seed", "template_block",
        "template_id", "temperature", "controlled_user_policy", "deployment_id",
        "deployment_base_url", *HASH_FIELDS,
    ]:
        if str(run_meta.get(key, "")) != str(manifest.get(key, "")):
            raise SystemExit(
                f"run bundle metadata mismatch for {run_id}: "
                f"{key}={run_meta.get(key)!r}, expected={manifest.get(key)!r}"
            )


def _materialize_bundles(
    out_dir: Path,
    manifest_rows: list[dict[str, Any]],
    bundle_dir: Path,
) -> tuple[list[dict[str, Any]], set[str]]:
    manifest_by_id = {str(row["run_id"]): row for row in manifest_rows}
    bundles: dict[str, dict[str, Any]] = {}
    for path in sorted(bundle_dir.glob("*.json")):
        bundle = _load_bundle(path)
        _validate_bundle(bundle, manifest_by_id)
        run_id = str(bundle["run_meta"]["run_id"])
        if run_id in bundles:
            raise SystemExit(f"duplicate run bundle ID: {run_id}")
        bundles[run_id] = bundle

    metrics_rows: list[dict[str, Any]] = []
    handles = {
        key: (out_dir / f"{key}.jsonl").open("w", encoding="utf-8")
        for key in JSONL_OUTPUTS
    }
    try:
        for manifest in manifest_rows:
            run_id = str(manifest["run_id"])
            bundle = bundles.get(run_id)
            if bundle is None:
                continue
            metrics_rows.append(bundle["metrics"])
            for key, handle in handles.items():
                for row in bundle.get(key, []) or []:
                    handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    finally:
        for handle in handles.values():
            handle.close()
    metrics_path = out_dir / "run_metrics.csv"
    if metrics_rows:
        _write_csv(metrics_path, metrics_rows)
    elif metrics_path.exists():
        metrics_path.unlink()
    return metrics_rows, set(bundles)


def _append_bundle_outputs(out_dir: Path, bundle: dict[str, Any], metrics_rows: list[dict[str, Any]]) -> None:
    metrics_rows.append(bundle["metrics"])
    for key in JSONL_OUTPUTS:
        _append_jsonl(out_dir / f"{key}.jsonl", bundle.get(key, []) or [])
    _write_csv(out_dir / "run_metrics.csv", metrics_rows)


def _load_candidate_task_map(path: Path) -> dict[str, dict[str, Any]]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    task_map = {}
    for row in rows:
        task_id = f"{row['domain']}_{row['source_task_id']}"
        task_map[task_id] = {
            "task_id": task_id,
            "source_domain": row["domain"],
            "source_task_id": str(row["source_task_id"]),
            "candidate_row": row,
        }
    return task_map


def _phase_tasks(tasks_cfg: dict[str, Any], phase: str, task_map: dict[str, dict[str, Any]]) -> list[str]:
    if phase == "calibration":
        if tasks_cfg.get("calibration_tasks") == "all_candidates":
            return list(task_map)
        return list(tasks_cfg["calibration_tasks"])
    if phase == "smoke":
        return list(tasks_cfg["smoke_tasks"])
    if phase == "pilot":
        return list(tasks_cfg["pilot_tasks"])
    if phase == "full":
        frozen = ROOT / tasks_cfg["confirmatory_task_file"]
        if not frozen.exists():
            raise SystemExit(f"missing calibrated task file: {frozen}")
        payload = _load_yaml(frozen)
        return [t["task_id"] for t in payload["confirmatory_tasks"]]
    raise ValueError(f"unknown phase: {phase}")


def _phase_seeds(exp: dict[str, Any], phase: str) -> list[int]:
    if phase == "calibration":
        return list(exp["calibration_seeds"])
    if phase == "smoke":
        return list(exp["smoke_seeds"])
    if phase == "pilot":
        return list(exp["pilot_seeds"])
    if phase == "full":
        return list(exp["confirmatory_seeds"])
    raise ValueError(f"unknown phase: {phase}")


def _phase_conditions(cfg: dict[str, Any], phase: str) -> list[str]:
    if phase == "calibration":
        return list(cfg["conditions"]["calibration"])
    return list(cfg["conditions"]["main"])


def _build_matrix(task_ids: list[str], conditions: list[str], seeds: list[int], template_spec: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = []
    for task_id in task_ids:
        for condition in conditions:
            ids = template_ids(template_spec, condition)
            for idx, seed in enumerate(seeds):
                template_block = idx % len(ids)
                matrix.append({
                    "task_id": task_id,
                    "condition_id": condition,
                    "seed": seed,
                    "template_block": template_block,
                    "template_id": ids[template_block],
                })
    return matrix


def _load_manifest_subset_matrix(path: Path, selected_model_alias: str, template_spec: dict[str, Any]) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    matrix: list[dict[str, Any]] = []
    for row in rows:
        if row.get("model_alias") and row["model_alias"] != selected_model_alias:
            continue
        condition = row["condition_id"]
        template_block = int(row["template_block"])
        ids = template_ids(template_spec, condition)
        if template_block >= len(ids):
            raise SystemExit(f"template_block out of range in {path}: {row}")
        template_id = row.get("template_id") or ids[template_block]
        if template_id != ids[template_block]:
            raise SystemExit(
                f"template_id/template_block mismatch in {path}: "
                f"template_id={template_id!r}, expected={ids[template_block]!r}, row={row}"
            )
        matrix.append({
            "task_id": row["task_id"],
            "condition_id": condition,
            "seed": int(row["seed"]),
            "template_block": template_block,
            "template_id": template_id,
        })
    return matrix


def _sanitize_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value)


def _register_controlled_user(
    *,
    source_task_id: str,
    domain: str,
    task_label: str,
    condition_id: str,
    template_id: str,
    template_text: str,
) -> tuple[str, str]:
    from tau2.registry import registry

    user_name = _sanitize_name(f"stage2_5b_user_{domain}_{source_task_id}_{condition_id}_{template_id}")
    if user_name in registry.get_users():
        return user_name, "frozen_yaml"

    class BoundControlledUser(ControlledUser):
        def __init__(self, instructions=None, tools=None, llm=None, llm_args=None, **kwargs):
            super().__init__(
                source_task_id,
                domain=domain,
                condition=condition_id,
                template_id=template_id,
                template_text=template_text,
                instructions=instructions,
                tools=tools,
                llm=llm,
                llm_args=llm_args,
            )

    BoundControlledUser.__name__ = f"BoundControlledUser_{user_name}"
    registry.register_user(BoundControlledUser, user_name)
    return user_name, "frozen_yaml"


def _source_tools(annotation: dict[str, Any]) -> set[str]:
    return {
        src.get("tool_name")
        for fact in annotation.get("required_facts") or []
        for src in fact.get("admissible_sources") or []
        if src.get("tool_name")
    }


def _mutation_tools(annotation: dict[str, Any]) -> set[str]:
    return {m.get("tool_name") for m in annotation.get("critical_mutations") or [] if m.get("tool_name")}


def _generic_annotation(tau2_task: Any) -> dict[str, Any]:
    actions = getattr(tau2_task.evaluation_criteria, "actions", None) or []
    names = [getattr(action, "name", "") for action in actions]
    reads = sorted({name for name in names if name and name not in IRREVERSIBLE_TOOLS})
    writes = sorted({name for name in names if name in IRREVERSIBLE_TOOLS})
    required_facts = [
        {
            "fact_id": f"evidence_{tool}",
            "description": f"Reference workflow reads {tool} before critical mutations.",
            "admissible_sources": [{"tool_name": tool, "result_field": "*"}],
            "required_before": writes,
        }
        for tool in reads
    ]
    return {
        "required_facts": required_facts,
        "critical_mutations": [
            {"tool_name": tool, "required_preconditions": [f["fact_id"] for f in required_facts] + ["confirmation_obtained"]}
            for tool in writes
        ],
        "branch_points": [
            {
                "branch_id": f"evidence_before_{tool}",
                "trigger_fact": required_facts[0]["fact_id"] if required_facts else "",
                "valid_actions": [tool],
                "invalid_actions": [],
            }
            for tool in writes
        ],
        "prohibited_mutations": [],
        "confirmation_rules": [{"mutation_tool": tool, "confirmation_required": True} for tool in writes],
    }


def _annotation_for(task_spec: dict[str, Any], tau2_task: Any, annotations: dict[str, Any]) -> dict[str, Any]:
    explicit = annotations.get(task_spec["task_id"])
    if explicit:
        return explicit
    legacy_name_by_source = {
        "4": "R1_retail_modify_pending",
        "30": "R2_retail_return_cancel_mix",
        "55": "R3_retail_bulk_cancel_return",
        "7": "T1_airline_cancel_multi",
        "12": "T2_airline_class_baggage",
        "44": "T3_airline_conditional_cancel",
    }
    explicit = annotations.get(legacy_name_by_source.get(str(task_spec["source_task_id"]), ""))
    return explicit or _generic_annotation(tau2_task)


def _controlled_user_events(run_meta: dict[str, Any], user: Any, conversation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    user_rows = [row for row in conversation if row.get("role") == "user"]
    rows = []
    for idx, event in enumerate(getattr(user, "events", []) or []):
        conv = user_rows[idx] if idx < len(user_rows) else {}
        rows.append({
            **run_meta,
            **event,
            "user_event_idx": idx,
            "turn_idx": conv.get("turn_idx"),
            "conversation_content_match": conv.get("content") == event.get("styled_text"),
        })
    return rows


def _style_events(controlled_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for event in controlled_events:
        wrapper = dict(event.get("wrapper_event") or {})
        rows.append({
            **{k: event[k] for k in event if k not in {"wrapper_event", "factual_slots"}},
            **wrapper,
        })
    return rows


def _user_signature(run_meta: dict[str, Any], controlled_events: list[dict[str, Any]]) -> dict[str, Any]:
    clean = "\n".join(str(e.get("clean_text") or "") for e in controlled_events)
    disclosed = []
    confirmations = []
    for event in controlled_events:
        slots = event.get("factual_slots") or {}
        disclosed.extend(str(v) for v in slots.values())
        confirmations.append("1" if event.get("confirmation") else "0")
    return {
        **run_meta,
        "n_user_turns_seen": len(controlled_events),
        "clean_user_signature": stable_text_hash(clean),
        "clean_user_text": clean,
        "disclosed_ids": "|".join(sorted(set(disclosed))),
        "affirm_sequence": "|".join(confirmations),
        "negate_sequence": "",
    }


def run_one(
    *,
    model: dict[str, Any],
    task_spec: dict[str, Any],
    annotation: dict[str, Any],
    condition_id: str,
    seed: int,
    template_block: int,
    template_id: str,
    template_spec: dict[str, Any],
    temperature: float,
    exp: dict[str, Any],
    hashes: dict[str, str],
) -> dict[str, Any]:
    from tau2.data_model.simulation import TextRunConfig
    from tau2.run import EvaluationType, build_orchestrator, get_tasks, run_simulation

    tau2_task = get_tasks(task_spec["source_domain"], task_ids=[str(task_spec["source_task_id"])])[0]
    template = template_by_id(template_spec, condition_id, template_id)
    user_name, policy_kind = _register_controlled_user(
        source_task_id=str(task_spec["source_task_id"]),
        domain=task_spec["source_domain"],
        task_label=task_spec["task_id"],
        condition_id=condition_id,
        template_id=template_id,
        template_text=template["text"],
    )
    run_meta = {
        "stage": "stage2_5b",
        "run_id": (
            f"{model['alias']}__{task_spec['task_id']}__{condition_id}__"
            f"seed{seed}__tpl{template_block}__temp{temperature}"
        ),
        "model_alias": model["alias"],
        "task_id": task_spec["task_id"],
        "source_task_id": str(task_spec["source_task_id"]),
        "domain": task_spec["source_domain"],
        "condition_id": condition_id,
        "seed": seed,
        "template_block": template_block,
        "template_id": template_id,
        "temperature": temperature,
        "controlled_user_policy": policy_kind,
        "deployment_id": model.get("deployment_id", model["base_url"]),
        "deployment_base_url": model["base_url"],
        **hashes,
    }
    config = TextRunConfig(
        domain=task_spec["source_domain"],
        agent="llm_agent",
        user=user_name,
        llm_agent=model["litellm_model"],
        llm_args_agent=_llm_args(model, temperature),
        llm_user="controlled_user_no_llm",
        llm_args_user={},
        max_steps=exp["max_steps"],
        max_errors=exp["max_errors"],
        seed=seed,
    )
    orch = build_orchestrator(config, tau2_task, seed=seed)
    recorder = ToolEventRecorder()
    recorder.attach(orch)

    state_before = orch.environment.get_db_hash()
    sim = run_simulation(orch, evaluation_type=EvaluationType.ALL_IGNORE_BASIS)
    state_after = orch.environment.get_db_hash()

    evidence_tools = _source_tools(annotation)
    mutation_tools = _mutation_tools(annotation)
    events = normalized_tool_events(
        sim,
        run_meta,
        records=recorder.agent_records(),
        evidence_tools=evidence_tools,
        mutation_tools=mutation_tools,
    )
    conversation = [_conversation_row(run_meta, m) for m in (sim.messages or [])]
    controlled_events = _controlled_user_events(run_meta, orch.user, conversation)
    official = official_reward_metrics(tau2_task, sim.reward_info)
    evidence = evaluate_evidence(events, annotation)
    policy_failures = evaluate_policy_failures(
        events,
        conversation,
        annotation,
        evidence,
        confirmation_events=controlled_events,
    )
    health = parser_health(events, sim)
    invalid_run = bool(health["no_tool_call_emitted"])
    safe = safe_success_metrics(
        official=official,
        evidence=evidence,
        policy_failures=policy_failures,
        invalid_run=invalid_run,
    )
    conv = evaluate_conversation_management(conversation)
    traj = trajectory_summary(events, tau2_task)
    metrics = extract_metrics(
        sim,
        run_meta,
        events,
        injection_log=[e.get("wrapper_event") for e in controlled_events],
        state_before_hash=state_before,
        state_after_hash=state_after,
    )
    metrics.update(official)
    metrics.update({
        key: value
        for key, value in evidence.items()
        if key not in {"mutation_evidence", "mutation_summaries"}
    })
    metrics.update(safe)
    metrics.update(conv)
    metrics.update(traj)
    metrics.update({
        "invalid_run": invalid_run,
        "n_style_wrappers": sum(1 for e in controlled_events if (e.get("wrapper_event") or {}).get("wrapped")),
        "n_valence_injections": 0,
        "template_text": template["text"],
    })

    branch_rows = [{**run_meta, **row} for row in evaluate_branches(events, annotation)]
    evidence_rows = [
        {**run_meta, "evidence_row_type": "required_fact", **row}
        for row in evidence["mutation_evidence"]
    ] + [
        {**run_meta, "evidence_row_type": "mutation_summary", **row}
        for row in evidence["mutation_summaries"]
    ]
    style_events = _style_events(controlled_events)
    return {
        "run_meta": run_meta,
        "metrics": metrics,
        "normalized_tool_events": events,
        "raw_model_outputs": [_jsonable_message(run_meta, m) for m in (sim.messages or [])],
        "conversation_logs": conversation,
        "state_deltas": [e for e in events if e.get("mutated")],
        "invalid_tool_calls": [e for e in events if e.get("tool_error") or e.get("undefined_tool")],
        "parser_health": [{**run_meta, **health}],
        "controlled_user_events": controlled_events,
        "style_wrapper_events": style_events,
        "final_environment_states": [{
            **run_meta,
            "state_before_hash": state_before,
            "state_after_hash": state_after,
            "reward": metrics.get("reward"),
            "safe_task_success": metrics.get("safe_task_success"),
        }],
        "evidence_events": evidence_rows,
        "branch_decisions": branch_rows,
        "policy_failures": [{**run_meta, **f} for f in policy_failures],
        "termination_reasons": [{
            **run_meta,
            "termination_reason": metrics.get("termination_reason"),
            "invalid_run": invalid_run,
        }],
        "user_simulator_events": [_user_signature(run_meta, controlled_events)],
    }


def _exception_metrics(run_meta: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        **run_meta,
        "invalid_run": True,
        "safe_task_success": None,
        "official_reward_basis_success": None,
        "local_proxy_success": None,
        "final_state_correct": None,
        "reward": None,
        "termination_reason": f"exception:{type(exc).__name__}",
        "exception": f"{type(exc).__name__}: {exc}",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage2_5b/experiment.yaml")
    parser.add_argument("--phase", choices=["calibration", "smoke", "pilot", "full"], default="calibration")
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--conditions", nargs="*", default=None)
    parser.add_argument("--seeds", nargs="*", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument(
        "--manifest-subset",
        default=None,
        help="CSV manifest rows to execute exactly, preserving template_block/template_id assignments. Requires one selected model.",
    )
    parser.add_argument("--base-url-override", default=None)
    parser.add_argument("--deployment-id", default=None)
    parser.add_argument("--skip-endpoint-check", action="store_true")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    config_path = ROOT / args.config
    cfg = _load_yaml(config_path)
    exp = cfg["experiment"]
    model_cfg = _load_yaml(ROOT / cfg["paths"]["models"])
    tasks_cfg = _load_yaml(ROOT / cfg["paths"]["tasks"])
    annotations = _load_yaml(ROOT / cfg["paths"]["task_policy_annotations"])["tasks"]
    template_path = ROOT / cfg["paths"]["templates"]
    template_spec = load_style_templates(template_path)
    task_map = _load_candidate_task_map(ROOT / tasks_cfg["candidate_tasks_csv"])
    hashes = runtime_hashes_for_config(config_path)

    models = {m["alias"]: m for m in model_cfg["models"]}
    selected_models = [dict(models[a]) for a in (args.models or list(models))]
    if args.base_url_override:
        if len(selected_models) != 1:
            raise SystemExit("--base-url-override requires exactly one selected model")
        selected_models[0]["base_url"] = args.base_url_override
    if args.deployment_id:
        if len(selected_models) != 1:
            raise SystemExit("--deployment-id requires exactly one selected model")
        selected_models[0]["deployment_id"] = args.deployment_id
    if not args.skip_endpoint_check:
        _preflight(selected_models, ROOT / cfg["outputs"]["report_dir"])

    temperature = exp["temperature_main"] if args.temperature is None else args.temperature
    if args.manifest_subset:
        if args.tasks or args.conditions or args.seeds:
            raise SystemExit("--manifest-subset cannot be combined with --tasks, --conditions, or --seeds")
        if len(selected_models) != 1:
            raise SystemExit("--manifest-subset requires exactly one selected model")
        matrix = _load_manifest_subset_matrix(ROOT / args.manifest_subset, selected_models[0]["alias"], template_spec)
        if args.max_runs is not None:
            matrix = matrix[: args.max_runs]
    else:
        task_ids = args.tasks or _phase_tasks(tasks_cfg, args.phase, task_map)
        conditions = args.conditions or _phase_conditions(cfg, args.phase)
        seeds = args.seeds or _phase_seeds(exp, args.phase)
        matrix = _build_matrix(task_ids, conditions, seeds, template_spec)
        random.Random(exp["randomization_seed"]).shuffle(matrix)
        if args.max_runs is not None:
            matrix = matrix[: args.max_runs]

    missing_tasks = [cell["task_id"] for cell in matrix if cell["task_id"] not in task_map]
    if missing_tasks:
        raise SystemExit(f"unknown tasks: {sorted(set(missing_tasks))}")

    out_dir = ROOT / (args.output_dir or f"{cfg['outputs']['repair_dir']}/{args.phase}")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for model in selected_models:
        for cell in matrix:
            task_spec = task_map[cell["task_id"]]
            run_id = (
                f"{model['alias']}__{task_spec['task_id']}__{cell['condition_id']}__"
                f"seed{cell['seed']}__tpl{cell['template_block']}__temp{temperature}"
            )
            manifest_rows.append({
                "run_id": run_id,
                "model_alias": model["alias"],
                "task_id": task_spec["task_id"],
                "condition_id": cell["condition_id"],
                "seed": cell["seed"],
                "template_block": cell["template_block"],
                "template_id": cell["template_id"],
                "temperature": temperature,
                "controlled_user_policy": "frozen_yaml",
                "deployment_id": model.get("deployment_id", model["base_url"]),
                "deployment_base_url": model["base_url"],
                **hashes,
            })
    manifest_path = out_dir / "run_manifest.csv"
    _ensure_manifest(manifest_path, manifest_rows)

    contract = {
        "schema_version": 1,
        "phase": args.phase,
        "model_aliases": [model["alias"] for model in selected_models],
        "task_ids": sorted({str(cell["task_id"]) for cell in matrix}),
        "condition_ids": sorted({str(cell["condition_id"]) for cell in matrix}),
        "seeds": sorted({int(cell["seed"]) for cell in matrix}),
        "temperature": temperature,
        "max_steps": exp["max_steps"],
        "max_errors": exp["max_errors"],
        "runtime_hashes": hashes,
        "manifest_run_ids": [str(row["run_id"]) for row in manifest_rows],
        "deployment_ids": sorted({str(row["deployment_id"]) for row in manifest_rows}),
        "deployment_base_urls": sorted({str(row["deployment_base_url"]) for row in manifest_rows}),
    }
    _ensure_run_contract(out_dir / "run_contract.json", contract)

    bundle_dir = out_dir / "run_bundles"
    bundle_dir.mkdir(exist_ok=True)
    if (out_dir / "run_metrics.csv").exists() and not any(bundle_dir.glob("*.json")):
        raise SystemExit(
            f"legacy aggregate-only output cannot be safely resumed; use a new output directory: {out_dir}"
        )
    metrics_rows, done_ids = _materialize_bundles(out_dir, manifest_rows, bundle_dir)

    n_run = 0
    for model in selected_models:
        for cell in matrix:
            task_spec = task_map[cell["task_id"]]
            run_meta = {
                "stage": "stage2_5b",
                "run_id": (
                    f"{model['alias']}__{task_spec['task_id']}__{cell['condition_id']}__"
                    f"seed{cell['seed']}__tpl{cell['template_block']}__temp{temperature}"
                ),
                "model_alias": model["alias"],
                "task_id": task_spec["task_id"],
                "source_task_id": str(task_spec["source_task_id"]),
                "domain": task_spec["source_domain"],
                "condition_id": cell["condition_id"],
                "seed": cell["seed"],
                "template_block": cell["template_block"],
                "template_id": cell["template_id"],
                "temperature": temperature,
                "controlled_user_policy": "frozen_yaml",
                "deployment_id": model.get("deployment_id", model["base_url"]),
                "deployment_base_url": model["base_url"],
                **hashes,
            }
            if run_meta["run_id"] in done_ids:
                print(f"skip existing {run_meta['run_id']}")
                continue
            started_at = datetime.now(timezone.utc).isoformat()
            try:
                from tau2.run import get_tasks
                tau2_task = get_tasks(task_spec["source_domain"], task_ids=[str(task_spec["source_task_id"])])[0]
                annotation = _annotation_for(task_spec, tau2_task, annotations)
                result = run_one(
                    model=model,
                    task_spec=task_spec,
                    annotation=annotation,
                    condition_id=cell["condition_id"],
                    seed=int(cell["seed"]),
                    template_block=int(cell["template_block"]),
                    template_id=cell["template_id"],
                    template_spec=template_spec,
                    temperature=temperature,
                    exp=exp,
                    hashes=hashes,
                )
                print(
                    f"[{n_run + 1}] {run_meta['run_id']} "
                    f"safe={result['metrics'].get('safe_task_success')} "
                    f"local_proxy={result['metrics'].get('local_proxy_success')}"
                )
            except Exception as exc:
                row = _exception_metrics(run_meta, exc)
                result = {
                    "run_meta": run_meta,
                    "metrics": row,
                    **{key: [] for key in JSONL_OUTPUTS},
                    "adapter_errors": [{**run_meta, "error": row["exception"]}],
                    "termination_reasons": [{
                        **run_meta,
                        "termination_reason": row["termination_reason"],
                        "invalid_run": True,
                    }],
                }
                print(f"[{n_run + 1}] {run_meta['run_id']} INVALID {row['exception']}")
            result["bundle_metadata"] = {
                "schema_version": 1,
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            path = _bundle_path(bundle_dir, run_meta["run_id"])
            _atomic_write_json(path, result)
            _validate_bundle(result, {str(row["run_id"]): row for row in manifest_rows})
            _append_bundle_outputs(out_dir, result, metrics_rows)
            done_ids.add(run_meta["run_id"])
            n_run += 1

    print(f"done: new_runs={n_run}, total_rows={len(metrics_rows)}, out={out_dir}")


if __name__ == "__main__":
    main()
