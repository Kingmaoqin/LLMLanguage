"""Stage-2.5 causal repair runner.

This runner intentionally does not reuse the legacy Stage-2 valence scheduler.
Social style is applied only to natural user turns, with fixed condition/seed
pairing and outputs isolated under results/stage2_5_repair/<phase>/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.instrument import ToolEventRecorder
from src.adapters.normalize import extract_metrics, normalized_tool_events, parser_health
from src.stage2_5.branch_evaluator import evaluate_branches
from src.stage2_5.controlled_user_simulator import user_turn_signature
from src.stage2_5.conversation_management_evaluator import evaluate_conversation_management
from src.stage2_5.evidence_graph_evaluator import evaluate_evidence
from src.stage2_5.official_tau_evaluator import official_local_metrics
from src.stage2_5.safe_task_evaluator import evaluate_policy_failures, safe_success_metrics
from src.stage2_5.social_style_wrapper import (
    SocialStyleController,
    apply_social_style,
    load_style_templates,
    template_by_id,
    template_ids,
)
from src.stage2_5.trajectory_metrics import trajectory_summary


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _llm_args(model: dict[str, Any], temperature: float) -> dict[str, Any]:
    return {
        "api_base": model["base_url"],
        "api_key": model.get("api_key", "EMPTY"),
        "temperature": temperature,
    }


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


def _source_tools(annotation: dict[str, Any]) -> set[str]:
    return {
        src.get("tool_name")
        for fact in annotation.get("required_facts") or []
        for src in fact.get("admissible_sources") or []
        if src.get("tool_name")
    }


def _mutation_tools(annotation: dict[str, Any]) -> set[str]:
    return {m.get("tool_name") for m in annotation.get("critical_mutations") or [] if m.get("tool_name")}


def _phase_tasks(tasks_cfg: dict[str, Any], phase: str) -> list[str]:
    if phase == "smoke":
        return list(tasks_cfg["smoke_tasks"])
    if phase == "diagnostic":
        return list(tasks_cfg["diagnostic_tasks"])
    if phase in {"pilot", "full"}:
        return list(tasks_cfg["repair_pilot_tasks"])
    raise ValueError(f"unknown phase: {phase}")


def _phase_seeds(exp: dict[str, Any], phase: str) -> list[int]:
    if phase == "smoke":
        return list(exp["smoke_seeds"])
    if phase == "pilot":
        return list(exp["pilot_seeds"])
    if phase in {"full", "diagnostic"}:
        return list(exp["seeds"])
    raise ValueError(f"unknown phase: {phase}")


def _phase_conditions(cfg: dict[str, Any], phase: str) -> list[str]:
    if phase == "diagnostic":
        return list(cfg["conditions"]["diagnostic"])
    return list(cfg["conditions"]["main"])


def _build_matrix(
    *,
    task_ids: list[str],
    conditions: list[str],
    seeds: list[int],
    template_spec: dict[str, Any],
) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
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
    lines = ["# Stage-2.5 Endpoint Preflight", ""]
    failures = []
    for model in models:
        ok, detail = _endpoint_ok(model)
        lines.append(f"- {model['alias']}: {'PASS' if ok else 'FAIL'} - {detail}")
        if not ok:
            failures.append(model["alias"])
    (report_dir / "MODEL_ENDPOINT_CHECK_STAGE2_5.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(f"endpoint preflight failed for {failures}")


def run_one(
    *,
    model: dict[str, Any],
    user_sim_model: dict[str, Any],
    task_spec: dict[str, Any],
    annotation: dict[str, Any],
    condition_id: str,
    seed: int,
    template_block: int,
    template_id: str,
    template_spec: dict[str, Any],
    temperature: float,
    exp: dict[str, Any],
) -> dict[str, Any]:
    from tau2.data_model.simulation import TextRunConfig
    from tau2.run import EvaluationType, build_orchestrator, get_tasks, run_simulation

    tau2_task = get_tasks(task_spec["source_domain"], task_ids=[str(task_spec["source_task_id"])])[0]
    run_meta = {
        "stage": "stage2_5",
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
        "user_sim_model_alias": user_sim_model["alias"],
    }

    config = TextRunConfig(
        domain=task_spec["source_domain"],
        agent="llm_agent",
        user="user_simulator",
        llm_agent=model["litellm_model"],
        llm_args_agent=_llm_args(model, temperature),
        llm_user=user_sim_model["litellm_model"],
        llm_args_user=_llm_args(user_sim_model, 0.0),
        max_steps=exp["max_steps"],
        max_errors=exp["max_errors"],
        seed=seed,
    )
    orch = build_orchestrator(config, tau2_task, seed=seed)
    template = template_by_id(template_spec, condition_id, template_id)
    controller = SocialStyleController(
        condition=condition_id,
        condition_spec=template_spec["conditions"][condition_id],
        template=template,
        template_block=template_block,
    )
    apply_social_style(orch, controller)
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
    official = official_local_metrics(tau2_task, sim.reward_info)
    evidence = evaluate_evidence(events, annotation)
    policy_failures = evaluate_policy_failures(events, conversation, annotation, evidence)
    health = parser_health(events, sim)
    invalid_run = bool(health["no_tool_call_emitted"])
    safe = safe_success_metrics(
        official=official,
        evidence=evidence,
        policy_failures=policy_failures,
        invalid_run=invalid_run,
    )
    conv = evaluate_conversation_management(conversation)
    traj = trajectory_summary(events)
    metrics = extract_metrics(
        sim,
        run_meta,
        events,
        injection_log=controller.wrapper_events,
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
        "n_style_wrappers": sum(1 for e in controller.wrapper_events if e.get("wrapped")),
        "n_valence_injections": 0,
        "template_text": template["text"],
    })

    branch_rows = [{**run_meta, **row} for row in evaluate_branches(events, annotation)]
    evidence_row = {**run_meta, **evidence}
    user_sigs = [
        user_turn_signature(row.get("content"), [template["text"]])
        for row in conversation
        if row.get("role") == "user"
    ]
    clean_user_text = "\n".join(sig["clean_text"] for sig in user_sigs)
    user_sig = {
        **run_meta,
        "n_user_turns_seen": len(user_sigs),
        "clean_user_signature": hashlib.sha256(clean_user_text.encode("utf-8")).hexdigest(),
        "clean_user_text": clean_user_text,
        "disclosed_ids": "|".join(sorted({x for sig in user_sigs for x in sig["ids"]})),
        "affirm_sequence": "|".join("1" if sig["affirm"] else "0" for sig in user_sigs),
        "negate_sequence": "|".join("1" if sig["negate"] else "0" for sig in user_sigs),
    }

    return {
        "run_meta": run_meta,
        "metrics": metrics,
        "normalized_tool_events": events,
        "raw_model_outputs": [_jsonable_message(run_meta, m) for m in (sim.messages or [])],
        "conversation_logs": conversation,
        "state_deltas": [e for e in events if e.get("mutated")],
        "invalid_tool_calls": [e for e in events if e.get("tool_error") or e.get("undefined_tool")],
        "parser_health": [{**run_meta, **health}],
        "style_wrapper_events": [{**run_meta, **e} for e in controller.wrapper_events],
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
        "user_simulator_events": [user_sig],
    }


JSONL_OUTPUTS = [
    "normalized_tool_events",
    "raw_model_outputs",
    "conversation_logs",
    "state_deltas",
    "invalid_tool_calls",
    "parser_health",
    "style_wrapper_events",
    "final_environment_states",
    "evidence_events",
    "branch_decisions",
    "policy_failures",
    "termination_reasons",
    "user_simulator_events",
    "adapter_errors",
]


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
        "user_sim_model_alias", "invalid_run", "safe_task_success",
        "official_local_success", "official_task_success", "final_state_correct",
        "reward", "required_fact_coverage", "mutation_before_evidence",
        "n_policy_failures", "policy_failure_types", "agent_tool_calls",
        "irreversible_actions", "boundary_setting_count", "self_repair_count",
        "user_abandonment_markers", "termination_reason",
    ]
    fields = list({k for row in rows for k in row})
    ordered = [f for f in preferred if f in fields] + sorted(f for f in fields if f not in preferred)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ordered)
        w.writeheader()
        w.writerows(rows)


def _write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run_id", "model_alias", "task_id", "condition_id", "seed",
        "template_block", "template_id", "temperature", "user_sim_model_alias",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows([{k: row[k] for k in fields} for row in rows])


def _exception_metrics(run_meta: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        **run_meta,
        "invalid_run": True,
        "safe_task_success": None,
        "official_local_success": None,
        "final_state_correct": None,
        "reward": None,
        "termination_reason": f"exception:{type(exc).__name__}",
        "exception": f"{type(exc).__name__}: {exc}",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage2_5/experiment.yaml")
    ap.add_argument("--phase", choices=["smoke", "pilot", "full", "diagnostic"], default="smoke")
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--tasks", nargs="*", default=None)
    ap.add_argument("--conditions", nargs="*", default=None)
    ap.add_argument("--seeds", nargs="*", type=int, default=None)
    ap.add_argument("--user-sim", default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--max-runs", type=int, default=None)
    ap.add_argument("--skip-endpoint-check", action="store_true")
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()

    cfg = _load_yaml(ROOT / args.config)
    exp = cfg["experiment"]
    model_cfg = _load_yaml(ROOT / cfg["paths"]["models"])
    tasks_cfg = _load_yaml(ROOT / cfg["paths"]["tasks"])
    annotations = _load_yaml(ROOT / cfg["paths"]["task_policy_annotations"])["tasks"]
    template_spec = load_style_templates(ROOT / cfg["paths"]["templates"])
    source_spec = _load_yaml(ROOT / tasks_cfg["task_source"])
    task_map = {t["task_id"]: t for t in source_spec["mini_stage2_v1"]}

    models = {m["alias"]: m for m in model_cfg["models"]}
    selected_models = [models[a] for a in (args.models or list(models))]
    user_sim_model = models[args.user_sim or model_cfg["user_simulator_llm"]]
    endpoint_models = {m["alias"]: m for m in [*selected_models, user_sim_model]}.values()
    if not args.skip_endpoint_check:
        _preflight(list(endpoint_models), ROOT / cfg["outputs"]["report_dir"])

    task_ids = args.tasks or _phase_tasks(tasks_cfg, args.phase)
    conditions = args.conditions or _phase_conditions(cfg, args.phase)
    seeds = args.seeds or _phase_seeds(exp, args.phase)
    temperature = exp["temperature_main"] if args.temperature is None else args.temperature

    missing_tasks = [t for t in task_ids if t not in task_map]
    if missing_tasks:
        raise SystemExit(f"unknown tasks: {missing_tasks}")
    missing_annotations = [t for t in task_ids if t not in annotations]
    if missing_annotations:
        raise SystemExit(f"missing policy annotations: {missing_annotations}")

    matrix = _build_matrix(
        task_ids=task_ids,
        conditions=conditions,
        seeds=seeds,
        template_spec=template_spec,
    )
    random.Random(exp["randomization_seed"]).shuffle(matrix)
    if args.max_runs is not None:
        matrix = matrix[: args.max_runs]

    out_dir = ROOT / (args.output_dir or f"{cfg['outputs']['repair_dir']}/{args.phase}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for key in JSONL_OUTPUTS:
        (out_dir / f"{key}.jsonl").touch(exist_ok=True)
    metrics_path = out_dir / "run_metrics.csv"
    metrics_rows = _load_metrics(metrics_path)
    done_ids = {r["run_id"] for r in metrics_rows}

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
                "user_sim_model_alias": user_sim_model["alias"],
            })
    _write_manifest(out_dir / "run_manifest.csv", manifest_rows)

    n_run = 0
    for model in selected_models:
        for cell in matrix:
            task_spec = task_map[cell["task_id"]]
            run_meta = {
                "stage": "stage2_5",
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
                "user_sim_model_alias": user_sim_model["alias"],
            }
            if run_meta["run_id"] in done_ids:
                print(f"skip existing {run_meta['run_id']}")
                continue
            try:
                result = run_one(
                    model=model,
                    user_sim_model=user_sim_model,
                    task_spec=task_spec,
                    annotation=annotations[task_spec["task_id"]],
                    condition_id=cell["condition_id"],
                    seed=int(cell["seed"]),
                    template_block=int(cell["template_block"]),
                    template_id=cell["template_id"],
                    template_spec=template_spec,
                    temperature=temperature,
                    exp=exp,
                )
                metrics_rows.append(result["metrics"])
                for key in JSONL_OUTPUTS:
                    if key == "adapter_errors":
                        continue
                    _append_jsonl(out_dir / f"{key}.jsonl", result.get(key, []))
                print(
                    f"[{n_run + 1}] {run_meta['run_id']} "
                    f"safe={result['metrics'].get('safe_task_success')} "
                    f"official={result['metrics'].get('official_local_success')}"
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
