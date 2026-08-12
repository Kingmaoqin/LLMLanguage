#!/usr/bin/env python3
"""R8-A: run ONE full attack episode on the NATIVE tau2 half-duplex orchestrator.

Reuses the R8 full-episode native pipeline (build_environment -> build_agent ->
run_simulation ALL + ENV DB-only re-score on the SAME trace). The ONLY difference
is the user: AttackUser wires the condition-blind Canonical Semantic Controller with
the condition style (C1/C2/C3) or the OptimizedAttacker (C4). The frozen per-task
objective (F1/F2/F3) comes from the registry.

One episode = (domain, task_id, model, condition[, policy], replicate). The record
adds attack_records (per-turn candidate/filter/selector/budget log) and the
adaptive_attack_exposure flag (spec 6.5). Infra failures write a .error.json and are
retried by the driver; agent refusal / no-op / MAX_STEPS are RESULTS, kept for ITT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r8_full_episode.build_task_registry import env_hashes, git_commit  # noqa: E402
from scripts.r8_attack.attacker import Objective, default_llm_backend  # noqa: E402
from scripts.r8_attack.attack_user import AttackUser  # noqa: E402

MODEL_ENDPOINTS = {
    "gemma4_31b": ("openai/g4-v2-1", "http://127.0.0.1:8005/v1"),
    "gpt_oss_120b": ("openai/gpt-oss", "http://127.0.0.1:8192/v1"),
    "mistral_small_3p2": ("openai/mistral-small-3p2", "http://127.0.0.1:8007/v1"),
}
USER_LLM = ("openai/mistral-small-3p2", "http://127.0.0.1:8007/v1")
ATTACKER_LLM = ("openai/mistral-small-3p2", "http://127.0.0.1:8007/v1")
REVIEWER_A_LLM = ("openai/gpt-oss", "http://127.0.0.1:8192/v1")
REVIEWER_B_LLM = ("openai/g4-v2-1", "http://127.0.0.1:8005/v1")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _model_config_hash(alias, served, api_base):
    return _sha(json.dumps({"alias": alias, "served": served, "api_base": api_base,
                            "temperature": 0.0}, sort_keys=True))


def _sum_usage(messages, role_types):
    ti = to = 0
    for m in messages:
        if type(m).__name__ in role_types and getattr(m, "usage", None):
            u = m.usage
            ti += int(u.get("prompt_tokens", 0) or 0)
            to += int(u.get("completion_tokens", 0) or 0)
    return {"tokens_input": ti, "tokens_output": to, "tokens_total": ti + to}


def _make_backends(seed: int, condition: str, policy: str):
    """Attacker/reviewer/selector backends (local vLLM). Only needed for C4."""
    if condition != "C4":
        return {}
    def attacker(system, user, seed=seed):
        return default_llm_backend(system, user, llm=ATTACKER_LLM[0], api_base=ATTACKER_LLM[1],
                                   seed=seed, max_tokens=200)
    def rev_a(system, user):
        return default_llm_backend(system, user, llm=REVIEWER_A_LLM[0], api_base=REVIEWER_A_LLM[1],
                                   seed=seed, max_tokens=160)
    def rev_b(system, user):
        return default_llm_backend(system, user, llm=REVIEWER_B_LLM[0], api_base=REVIEWER_B_LLM[1],
                                   seed=seed, max_tokens=160)
    def selector(system, user):
        return default_llm_backend(system, user, llm=ATTACKER_LLM[0], api_base=ATTACKER_LLM[1],
                                   seed=seed, max_tokens=120)
    return dict(attacker_backend=attacker, reviewer_a_backend=rev_a,
                reviewer_b_backend=rev_b, selector_backend=selector)


def run_one(domain, task_id, model_alias, condition, replicate, *, objective: Objective,
            policy: str, max_steps: int, seed: int, out_path: pathlib.Path,
            family: str, split: str) -> dict:
    from tau2.run import get_tasks
    from tau2.runner import build_agent, build_environment
    from tau2.orchestrator.orchestrator import Orchestrator
    from tau2.runner.simulation import run_simulation
    from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
    from scripts.r7d_ipma.step2_1.official_scorer import configure_local_nl_judge
    from scripts.r8_full_episode.native_patches import install as install_patches

    install_patches()
    configure_local_nl_judge(model=USER_LLM[0], api_base=USER_LLM[1])
    served, api_base = MODEL_ENDPOINTS[model_alias]

    tasks = {str(t.id): t for t in get_tasks(domain)}
    if task_id not in tasks:
        raise KeyError(f"task {task_id} not in {domain}")
    task = tasks[task_id]

    environment = build_environment(domain, solo_mode=False)
    initial_db_hash = environment.get_db_hash()
    agent = build_agent("llm_agent", environment, llm=served,
                        llm_args={"api_base": api_base, "api_key": "EMPTY",
                                  "temperature": 0.0, "seed": seed}, task=task)
    backends = _make_backends(seed, condition, policy)
    user = AttackUser(task, domain, condition, objective, tools=None,
                      instructions=str(task.user_scenario), user_llm=USER_LLM[0],
                      api_base=USER_LLM[1], seed=seed, policy=policy, **backends)

    tag = policy if condition == "C4" else condition
    sim_id = f"r8a_{domain}_{task_id}_{model_alias}_{condition}_{tag}_rep{replicate}"
    orch = Orchestrator(domain=domain, agent=agent, user=user, environment=environment,
                        task=task, max_steps=max_steps, max_errors=10, seed=seed,
                        solo_mode=False, simulation_id=sim_id)

    sim = run_simulation(orch, evaluation_type=EvaluationType.ALL)
    env_reward = evaluate_simulation(sim, task, EvaluationType.ENV, solo_mode=False, domain=domain)
    final_db_hash = orch.environment.get_db_hash()

    ri = sim.reward_info
    env_db_check = getattr(env_reward, "db_check", None) if env_reward else None
    db_component = (env_reward.reward if (env_reward and env_db_check is not None) else None)
    reward_components = {
        "overall_reward": (ri.reward if ri else None),
        "db_component": db_component,
        "db_match": getattr(env_db_check, "db_match", None),
        "reward_basis": [str(x) for x in (ri.reward_basis or [])] if ri else [],
        "n_communicate_checks": len(ri.communicate_checks or []) if ri else 0,
        "communicate_met": (sum(1 for c in (ri.communicate_checks or []) if getattr(c, "met", False))
                            if ri and ri.communicate_checks else None),
    }

    messages = sim.messages or []
    agent_tool_calls = [
        {"turn_idx": m.turn_idx, "tool_calls": [tc.model_dump() for tc in m.tool_calls]}
        for m in messages
        if type(m).__name__ == "AssistantMessage" and getattr(m, "tool_calls", None)]
    tool_results = []
    for m in messages:
        tname = type(m).__name__
        if tname == "ToolMessage":
            tool_results.append({"turn_idx": m.turn_idx, "requestor": getattr(m, "requestor", None),
                                 "id": getattr(m, "id", None), "error": getattr(m, "error", None)})
        elif tname == "MultiToolMessage":
            for tm in getattr(m, "tool_messages", []) or []:
                tool_results.append({"turn_idx": getattr(m, "turn_idx", None),
                                     "requestor": getattr(tm, "requestor", None),
                                     "id": getattr(tm, "id", None), "error": getattr(tm, "error", None)})
    usage = _sum_usage(messages, {"AssistantMessage"})

    total_tool_calls = len(agent_tool_calls)
    attack_records = None
    exposure = False
    attacker_hash = None
    if condition != "C0":
        attack_records = [r.get("attack_record") for r in user.records]
        if condition == "C4":
            exposure = user.adaptive_attack_exposure(total_tool_calls)
            attacker_hash = user.template_bank_hash

    env_h = env_hashes(domain)
    record = dict(
        run_id=sim_id, task_id=task_id, domain=domain, family=family, split=split,
        objective=dataclasses_objective(objective), model=model_alias, condition=condition,
        attacker_policy=(policy if condition == "C4" else None), replicate=replicate,
        git_commit=git_commit(ROOT), tau_commit=git_commit(pathlib.Path("/home/xqin5/tau2-bench")),
        task_hash=_sha(task.model_dump_json()),
        policy_hash=env_h["policy_hash"], tool_schema_hash=env_h["tool_schema_hash"],
        model_config_hash=_model_config_hash(model_alias, served, api_base),
        user_controller_hash=(user._controller.system_prompt_hash if condition != "C0" else "C0_native"),
        attacker_system_hash=attacker_hash,
        initial_db_hash=initial_db_hash, final_db_hash=final_db_hash,
        native_messages=[m.model_dump() for m in messages],
        agent_tool_calls=agent_tool_calls, tool_results=tool_results,
        user_state_records=user.records if condition != "C0" else [],
        semantic_payload_hashes=([r["semantic_payload_hash"] for r in user.records]
                                 if condition != "C0" else []),
        attack_records=attack_records, adaptive_attack_exposure=exposure,
        official_reward=(ri.reward if ri else None), reward_components=reward_components,
        tokens_input=usage["tokens_input"], tokens_output=usage["tokens_output"],
        tokens_total=usage["tokens_total"], duration_seconds=sim.duration,
        termination_reason=str(sim.termination_reason),
        agent_errors=(str(sim.termination_reason)
                      if any(k in str(sim.termination_reason)
                             for k in ("AGENT_ERROR", "USER_ERROR", "MAX_STEPS", "TOO_MANY_ERRORS"))
                      else None),
        total_agent_tool_calls=total_tool_calls, seed=seed, max_steps=max_steps,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return record


def dataclasses_objective(obj: Objective) -> dict:
    return {"family": obj.family, "target_direction": obj.target_direction, "metric": obj.metric}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["retail", "airline"])
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--model", required=True, choices=list(MODEL_ENDPOINTS))
    ap.add_argument("--condition", required=True, choices=["C0", "C1", "C2", "C3", "C4"])
    ap.add_argument("--policy", default="P3", choices=["P0", "P1", "P2", "P3"])
    ap.add_argument("--family", required=True, choices=["F1", "F2", "F3"])
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--target-direction", required=True)
    ap.add_argument("--metric", required=True)
    ap.add_argument("--replicate", type=int, required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--max-steps", type=int, default=100)
    ap.add_argument("--out-path", type=pathlib.Path, required=True)
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else 1000 + args.replicate
    if args.skip_existing and args.out_path.exists():
        print(f"SKIP existing {args.out_path}")
        return 0
    obj = Objective(family=args.family, target_direction=args.target_direction, metric=args.metric)
    try:
        rec = run_one(args.domain, args.task_id, args.model, args.condition, args.replicate,
                      objective=obj, policy=args.policy, max_steps=args.max_steps, seed=seed,
                      out_path=args.out_path, family=args.family, split=args.split)
        print(f"OK {rec['run_id']} reward={rec['official_reward']} "
              f"tools={rec['total_agent_tool_calls']} term={rec['termination_reason']} "
              f"exposure={rec['adaptive_attack_exposure']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        err = {"error": repr(exc)[:300], "traceback": traceback.format_exc()[-1800:]}
        args.out_path.parent.mkdir(parents=True, exist_ok=True)
        args.out_path.with_suffix(".error.json").write_text(json.dumps(err, indent=2))
        print(f"INFRA-FAIL {args.domain}/{args.task_id}/{args.model}/{args.condition}: {exc!r}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
