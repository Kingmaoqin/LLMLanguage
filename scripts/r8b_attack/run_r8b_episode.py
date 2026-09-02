#!/usr/bin/env python3
"""R8-B: run ONE episode (Part A / B / C) on the native tau2 orchestrator using R8BUser.

Reuses the R8-A native pipeline; the only differences are the R8BUser (cached turn-0,
H0-H3 conditions, confounder flags, boundary flags) and the frozen per-task objective.
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
from scripts.r8_attack.run_attack_episode import (  # noqa: E402
    MODEL_ENDPOINTS, USER_LLM, ATTACKER_LLM, REVIEWER_A_LLM, REVIEWER_B_LLM, _sum_usage, _model_config_hash,
)
from scripts.r8b_attack.r8b_user import R8BUser  # noqa: E402


def _sha(t): return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _backends(seed, needs_attacker):
    if not needs_attacker:
        return {}
    return dict(
        attacker_backend=lambda s, u, seed=seed: default_llm_backend(s, u, llm=ATTACKER_LLM[0], api_base=ATTACKER_LLM[1], seed=seed, max_tokens=200),
        reviewer_a_backend=lambda s, u: default_llm_backend(s, u, llm=REVIEWER_A_LLM[0], api_base=REVIEWER_A_LLM[1], seed=seed, max_tokens=160),
        reviewer_b_backend=lambda s, u: default_llm_backend(s, u, llm=REVIEWER_B_LLM[0], api_base=REVIEWER_B_LLM[1], seed=seed, max_tokens=160),
        selector_backend=lambda s, u: default_llm_backend(s, u, llm=ATTACKER_LLM[0], api_base=ATTACKER_LLM[1], seed=seed, max_tokens=120),
    )


def run_one(domain, task_id, model_alias, condition, replicate, *, objective, part,
            confounders, boundary, max_steps, seed, out_path):
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
    task = {str(t.id): t for t in get_tasks(domain)}[task_id]

    environment = build_environment(domain, solo_mode=False)
    initial_db_hash = environment.get_db_hash()
    agent = build_agent("llm_agent", environment, llm=served,
                        llm_args={"api_base": api_base, "api_key": "EMPTY", "temperature": 0.0, "seed": seed}, task=task)
    needs_attacker = condition in ("H1", "H2", "H3")
    user = R8BUser(task, domain, condition, objective, tools=None, instructions=str(task.user_scenario),
                   user_llm=USER_LLM[0], api_base=USER_LLM[1], seed=seed, replicate=replicate,
                   confounders=confounders, boundary=boundary, **_backends(seed, needs_attacker))

    sim_id = f"r8b_{part}_{domain}_{task_id}_{model_alias}_{condition}_rep{replicate}"
    orch = Orchestrator(domain=domain, agent=agent, user=user, environment=environment, task=task,
                        max_steps=max_steps, max_errors=10, seed=seed, solo_mode=False, simulation_id=sim_id)
    sim = run_simulation(orch, evaluation_type=EvaluationType.ALL)
    env_reward = evaluate_simulation(sim, task, EvaluationType.ENV, solo_mode=False, domain=domain)
    final_db_hash = orch.environment.get_db_hash()

    ri = sim.reward_info
    env_db_check = getattr(env_reward, "db_check", None) if env_reward else None
    db_component = (env_reward.reward if (env_reward and env_db_check is not None) else None)
    reward_components = {
        "overall_reward": (ri.reward if ri else None), "db_component": db_component,
        "db_match": getattr(env_db_check, "db_match", None),
        "communicate_met": (sum(1 for c in (ri.communicate_checks or []) if getattr(c, "met", False))
                            if ri and ri.communicate_checks else None),
        "n_communicate_checks": len(ri.communicate_checks or []) if ri else 0,
    }
    messages = sim.messages or []
    agent_tool_calls = [{"turn_idx": m.turn_idx, "tool_calls": [tc.model_dump() for tc in m.tool_calls]}
                        for m in messages if type(m).__name__ == "AssistantMessage" and getattr(m, "tool_calls", None)]
    tool_results = []
    for m in messages:
        tn = type(m).__name__
        if tn == "ToolMessage":
            tool_results.append({"turn_idx": m.turn_idx, "id": getattr(m, "id", None), "error": getattr(m, "error", None)})
        elif tn == "MultiToolMessage":
            for tm in getattr(m, "tool_messages", []) or []:
                tool_results.append({"turn_idx": getattr(m, "turn_idx", None), "id": getattr(tm, "id", None), "error": getattr(tm, "error", None)})
    usage = _sum_usage(messages, {"AssistantMessage"})
    total_tool_calls = len(agent_tool_calls)

    rec = dict(
        run_id=sim_id, part=part, domain=domain, task_id=task_id, family=objective.family,
        objective={"family": objective.family, "target_direction": objective.target_direction, "metric": objective.metric},
        model=model_alias, condition=condition, confounders=confounders, boundary=boundary, replicate=replicate,
        git_commit=git_commit(ROOT), task_hash=_sha(task.model_dump_json()),
        model_config_hash=_model_config_hash(model_alias, served, api_base),
        attacker_hash=(user.attacker_hash if needs_attacker else None),
        initial_db_hash=initial_db_hash, final_db_hash=final_db_hash,
        native_messages=[m.model_dump() for m in messages], agent_tool_calls=agent_tool_calls,
        tool_results=tool_results, user_state_records=user.records,
        attack_records=[r.get("attack_record") for r in user.records],
        adaptive_attack_exposure=(user.adaptive_exposure(total_tool_calls) if needs_attacker else False),
        official_reward=(ri.reward if ri else None), reward_components=reward_components,
        tokens_total=usage["tokens_total"], duration_seconds=sim.duration,
        termination_reason=str(sim.termination_reason), total_agent_tool_calls=total_tool_calls,
        seed=seed, max_steps=max_steps)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True); ap.add_argument("--task-id", required=True)
    ap.add_argument("--model", required=True, choices=list(MODEL_ENDPOINTS))
    ap.add_argument("--condition", required=True)
    ap.add_argument("--part", required=True); ap.add_argument("--family", required=True)
    ap.add_argument("--target-direction", required=True); ap.add_argument("--metric", required=True)
    ap.add_argument("--confounders", default="{}"); ap.add_argument("--boundary", default="")
    ap.add_argument("--replicate", type=int, required=True); ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--max-steps", type=int, default=100); ap.add_argument("--out-path", type=pathlib.Path, required=True)
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()
    if args.skip_existing and args.out_path.exists():
        print(f"SKIP {args.out_path}"); return 0
    seed = args.seed if args.seed is not None else 2000 + args.replicate
    obj = Objective(args.family, args.target_direction, args.metric)
    try:
        rec = run_one(args.domain, args.task_id, args.model, args.condition, args.replicate,
                      objective=obj, part=args.part, confounders=json.loads(args.confounders),
                      boundary=(args.boundary or None), max_steps=args.max_steps, seed=seed, out_path=args.out_path)
        print(f"OK {rec['run_id']} reward={rec['official_reward']} tools={rec['total_agent_tool_calls']} term={rec['termination_reason']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        args.out_path.parent.mkdir(parents=True, exist_ok=True)
        args.out_path.with_suffix(".error.json").write_text(json.dumps({"error": repr(exc)[:300], "traceback": traceback.format_exc()[-1500:]}, indent=2))
        print(f"INFRA-FAIL {args.domain}/{args.task_id}/{args.model}/{args.condition}: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
