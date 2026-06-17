"""Stage-2.5b controlled-user experiment runner."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.instrument import ToolEventRecorder
from src.adapters.normalize import IRREVERSIBLE_TOOLS, extract_metrics, normalized_tool_events, parser_health
from src.stage2_5.branch_evaluator import evaluate_branches
from src.stage2_5.conversation_management_evaluator import evaluate_conversation_management
from src.stage2_5.evidence_graph_evaluator import evaluate_evidence
from src.stage2_5.official_tau_evaluator import official_local_metrics
from src.stage2_5.safe_task_evaluator import evaluate_policy_failures, safe_success_metrics
from src.stage2_5.social_style_wrapper import load_style_templates, template_by_id, template_ids
from src.stage2_5.trajectory_metrics import trajectory_summary
from src.stage2_5b.controlled_user import ControlledUser, TASK_POLICIES, generic_policy_from_task, stable_text_hash


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
        "controlled_user_policy", "invalid_run", "safe_task_success",
        "official_reward_basis_success", "local_proxy_success", "official_local_success",
        "official_task_success", "final_state_correct", "reward",
        "required_fact_coverage", "mutation_before_evidence",
        "n_policy_failures", "policy_failure_types", "agent_tool_calls",
        "tool_name_sequence_distance", "critical_argument_sequence_distance",
        "mutation_sequence_distance", "irreversible_actions", "termination_reason",
        "config_hash", "template_hash", "controlled_user_hash", "evaluator_hash",
        "benchmark_manifest_hash",
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
        "config_hash", "template_hash", "controlled_user_hash", "evaluator_hash",
        "benchmark_manifest_hash",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{k: row.get(k) for k in fields} for row in rows])


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
        return list(payload["confirmatory_tasks"])
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


def _sanitize_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value)


def _register_controlled_user(
    *,
    source_task_id: str,
    domain: str,
    task_label: str,
    tau2_task: Any,
    condition_id: str,
    template_id: str,
    template_text: str,
) -> tuple[str, str]:
    from tau2.registry import registry

    user_name = _sanitize_name(f"stage2_5b_user_{domain}_{source_task_id}_{condition_id}_{template_id}")
    if user_name in registry.get_users():
        policy_kind = "static" if source_task_id in TASK_POLICIES else "generic"
        return user_name, policy_kind

    policy_override = None
    policy_kind = "static"
    if source_task_id not in TASK_POLICIES:
        policy_kind = "generic"
        policy_override = generic_policy_from_task(
            source_task_id=source_task_id,
            domain=domain,
            task_label=task_label,
            user_scenario=tau2_task.user_scenario,
        )

    class BoundControlledUser(ControlledUser):
        def __init__(self, instructions=None, tools=None, llm=None, llm_args=None, **kwargs):
            super().__init__(
                source_task_id,
                condition=condition_id,
                template_id=template_id,
                template_text=template_text,
                instructions=instructions,
                tools=tools,
                llm=llm,
                llm_args=llm_args,
                policy_override=policy_override,
            )

    BoundControlledUser.__name__ = f"BoundControlledUser_{user_name}"
    registry.register_user(BoundControlledUser, user_name)
    return user_name, policy_kind


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
                "invalid_actions": [tool],
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
        tau2_task=tau2_task,
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
    official = official_local_metrics(tau2_task, sim.reward_info)
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
    metrics.update(evidence)
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
    evidence_row = {**run_meta, **evidence}
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
        "evidence_events": [evidence_row],
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
        "official_local_success": None,
        "final_state_correct": None,
        "reward": None,
        "termination_reason": f"exception:{type(exc).__name__}",
        "exception": f"{type(exc).__name__}: {exc}",
    }


def _hashes(config_path: Path, template_path: Path, benchmark_manifest: Path) -> dict[str, str]:
    evaluator_paths = [
        ROOT / "src" / "stage2_5" / "official_tau_evaluator.py",
        ROOT / "src" / "stage2_5" / "safe_task_evaluator.py",
        ROOT / "src" / "stage2_5" / "evidence_graph_evaluator.py",
        ROOT / "src" / "stage2_5" / "branch_evaluator.py",
        ROOT / "src" / "stage2_5" / "trajectory_metrics.py",
    ]
    return {
        "config_hash": _sha256(config_path),
        "template_hash": _sha256(template_path),
        "controlled_user_hash": _sha256(ROOT / "src" / "stage2_5b" / "controlled_user.py"),
        "evaluator_hash": _combined_hash(evaluator_paths),
        "benchmark_manifest_hash": _sha256(benchmark_manifest) if benchmark_manifest.exists() else "MISSING",
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
    hashes = _hashes(config_path, template_path, ROOT / cfg["paths"]["benchmark_manifest"])

    models = {m["alias"]: m for m in model_cfg["models"]}
    selected_models = [models[a] for a in (args.models or list(models))]
    if not args.skip_endpoint_check:
        _preflight(selected_models, ROOT / cfg["outputs"]["report_dir"])

    task_ids = args.tasks or _phase_tasks(tasks_cfg, args.phase, task_map)
    conditions = args.conditions or _phase_conditions(cfg, args.phase)
    seeds = args.seeds or _phase_seeds(exp, args.phase)
    temperature = exp["temperature_main"] if args.temperature is None else args.temperature

    missing_tasks = [task_id for task_id in task_ids if task_id not in task_map]
    if missing_tasks:
        raise SystemExit(f"unknown tasks: {missing_tasks}")

    matrix = _build_matrix(task_ids, conditions, seeds, template_spec)
    random.Random(exp["randomization_seed"]).shuffle(matrix)
    if args.max_runs is not None:
        matrix = matrix[: args.max_runs]

    out_dir = ROOT / (args.output_dir or f"{cfg['outputs']['repair_dir']}/{args.phase}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for key in JSONL_OUTPUTS:
        (out_dir / f"{key}.jsonl").touch(exist_ok=True)

    metrics_path = out_dir / "run_metrics.csv"
    metrics_rows = _load_metrics(metrics_path)
    done_ids = {row["run_id"] for row in metrics_rows}

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
                "controlled_user_policy": "static" if str(task_spec["source_task_id"]) in TASK_POLICIES else "generic",
                **hashes,
            })
    _write_manifest(out_dir / "run_manifest.csv", manifest_rows)

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
                "controlled_user_policy": "static" if str(task_spec["source_task_id"]) in TASK_POLICIES else "generic",
                **hashes,
            }
            if run_meta["run_id"] in done_ids:
                print(f"skip existing {run_meta['run_id']}")
                continue
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
                metrics_rows.append(result["metrics"])
                for key in JSONL_OUTPUTS:
                    if key == "adapter_errors":
                        continue
                    _append_jsonl(out_dir / f"{key}.jsonl", result.get(key, []))
                print(
                    f"[{n_run + 1}] {run_meta['run_id']} "
                    f"safe={result['metrics'].get('safe_task_success')} "
                    f"local_proxy={result['metrics'].get('local_proxy_success')}"
                )
            except Exception as exc:
                row = _exception_metrics(run_meta, exc)
                metrics_rows.append(row)
                _append_jsonl(out_dir / "adapter_errors.jsonl", [{**run_meta, "error": row["exception"]}])
                _append_jsonl(out_dir / "termination_reasons.jsonl", [{
                    **run_meta,
                    "termination_reason": row["termination_reason"],
                    "invalid_run": True,
                }])
                print(f"[{n_run + 1}] {run_meta['run_id']} INVALID {row['exception']}")
            done_ids.add(run_meta["run_id"])
            _write_csv(metrics_path, metrics_rows)
            n_run += 1

    print(f"done: new_runs={n_run}, total_rows={len(metrics_rows)}, out={out_dir}")


if __name__ == "__main__":
    main()
