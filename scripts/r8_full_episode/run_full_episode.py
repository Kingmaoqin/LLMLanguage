#!/usr/bin/env python3
"""R8 Full-Episode: run ONE full episode on the NATIVE tau2 half-duplex orchestrator
and save the full trace (spec 9).

Pipeline (all native; no evaluator copy):
    build_environment -> build_agent -> FullEpisodeUser -> Orchestrator
    -> run_simulation(ALL)         # native run + native evaluate_simulation (DB+COMMUNICATE)
    -> evaluate_simulation(ENV)    # native DB-only component on the SAME trace

The agent under test runs on a fixed local vLLM endpoint (temperature 0). The user
runs on a fixed neutral user endpoint. COMMUNICATE is judged by a local NL judge.

One episode = (domain, task_id, model, condition, replicate). A full BLOCK is
task x model x replicate x all 5 conditions; block-level reruns belong to the
driver, not here. This script is resumable (--skip-existing) and never deletes
agent outcomes (refusal / no-op / wrong tool are results, not errors).
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

from scripts.r8_full_episode.full_episode_user import FullEpisodeUser
from scripts.r8_full_episode.build_task_registry import env_hashes, git_commit, MUT

MODEL_ENDPOINTS = {
    "gemma4_31b": ("openai/g4-v2-1", "http://127.0.0.1:8005/v1"),
    "gpt_oss_120b": ("openai/gpt-oss", "http://127.0.0.1:8192/v1"),
    "mistral_small_3p2": ("openai/mistral-small-3p2", "http://127.0.0.1:8007/v1"),
}
USER_LLM = ("openai/mistral-small-3p2", "http://127.0.0.1:8007/v1")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _model_config_hash(model_alias: str, served: str, api_base: str) -> str:
    return _sha(json.dumps({"alias": model_alias, "served": served, "api_base": api_base,
                            "temperature": 0.0}, sort_keys=True))


def _sum_usage(messages, role_types) -> dict:
    ti = to = 0
    for m in messages:
        if type(m).__name__ in role_types and getattr(m, "usage", None):
            u = m.usage
            ti += int(u.get("prompt_tokens", 0) or 0)
            to += int(u.get("completion_tokens", 0) or 0)
    return {"tokens_input": ti, "tokens_output": to, "tokens_total": ti + to}


def run_one(domain: str, task_id: str, model_alias: str, condition: str, replicate: int,
            *, max_steps: int, seed: int, out_path: pathlib.Path,
            task_type: str | None = None) -> dict:
    from tau2.run import get_tasks
    from tau2.runner import build_agent, build_environment
    from tau2.orchestrator.orchestrator import Orchestrator
    from tau2.runner.simulation import run_simulation
    from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
    from scripts.r7d_ipma.step2_1.official_scorer import configure_local_nl_judge
    from scripts.r8_full_episode.native_patches import install as install_patches

    install_patches()  # fail-closed sanitize empty tool-call names (mistral quirk); non-fatal
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
    user = FullEpisodeUser(task, domain, condition, tools=None,
                           instructions=str(task.user_scenario),
                           user_llm=USER_LLM[0], api_base=USER_LLM[1], seed=seed)

    sim_id = f"r8_{domain}_{task_id}_{model_alias}_{condition}_rep{replicate}"
    orch = Orchestrator(domain=domain, agent=agent, user=user, environment=environment,
                        task=task, max_steps=max_steps, max_errors=10, seed=seed,
                        solo_mode=False, simulation_id=sim_id)

    infra_error = None
    sim = run_simulation(orch, evaluation_type=EvaluationType.ALL)
    # native DB-only component on the SAME completed trace
    env_reward = evaluate_simulation(sim, task, EvaluationType.ENV, solo_mode=False,
                                     domain=domain)
    final_db_hash = orch.environment.get_db_hash()

    ri = sim.reward_info
    # If the trajectory terminated prematurely the ENV evaluator returns reward=0.0
    # with db_check=None (NOT evaluated) -> emit None, not 0.0, so "not scored" is not
    # misread as "DB wrong".
    env_db_check = getattr(env_reward, "db_check", None) if env_reward else None
    db_component = (env_reward.reward if (env_reward and env_db_check is not None) else None)
    reward_components = {
        "overall_reward": (ri.reward if ri else None),
        "db_component": db_component,
        "db_match": getattr(env_db_check, "db_match", None),
        "reward_basis": [str(x) for x in (ri.reward_basis or [])] if ri else [],
        "reward_breakdown": ({str(k): v for k, v in ri.reward_breakdown.items()}
                             if ri and ri.reward_breakdown else None),
        "n_communicate_checks": len(ri.communicate_checks or []) if ri else 0,
        "communicate_met": (sum(1 for c in (ri.communicate_checks or [])
                                if getattr(c, "met", False)) if ri and ri.communicate_checks
                            else None),
    }

    messages = sim.messages or []
    agent_tool_calls = [
        {"turn_idx": m.turn_idx, "tool_calls": [tc.model_dump() for tc in m.tool_calls]}
        for m in messages
        if type(m).__name__ == "AssistantMessage" and getattr(m, "tool_calls", None)
    ]
    tool_results = []
    for m in messages:
        tname = type(m).__name__
        if tname == "ToolMessage":
            tool_results.append({"turn_idx": m.turn_idx, "requestor": getattr(m, "requestor", None),
                                 "id": getattr(m, "id", None), "error": getattr(m, "error", None)})
        elif tname == "MultiToolMessage":
            # batched tool calls -> capture each inner ToolMessage (id/error) too
            for tm in getattr(m, "tool_messages", []) or []:
                tool_results.append({"turn_idx": getattr(m, "turn_idx", None),
                                     "requestor": getattr(tm, "requestor", None),
                                     "id": getattr(tm, "id", None),
                                     "error": getattr(tm, "error", None)})
    usage = _sum_usage(messages, {"AssistantMessage"})

    env_h = env_hashes(domain)
    record = dict(
        run_id=sim_id, task_id=task_id, domain=domain,
        task_type=task_type,  # from the frozen manifest (passed by the batch driver)
        model=model_alias, condition=condition, replicate=replicate,
        git_commit=git_commit(ROOT), tau_commit=git_commit(pathlib.Path("/home/xqin5/tau2-bench")),
        task_hash=_sha(task.model_dump_json()),
        policy_hash=env_h["policy_hash"], tool_schema_hash=env_h["tool_schema_hash"],
        model_config_hash=_model_config_hash(model_alias, served, api_base),
        user_policy_hash=user._controller.system_prompt_hash if condition != "C0" else "C0_native",
        template_bank_hash=getattr(user, "template_bank_hash", None),
        initial_db_hash=initial_db_hash, final_db_hash=final_db_hash,
        native_messages=[m.model_dump() for m in messages],
        agent_tool_calls=agent_tool_calls, tool_results=tool_results,
        user_state_records=user.records,
        semantic_payload_hashes=[r["semantic_payload_hash"] for r in user.records],
        official_reward=(ri.reward if ri else None),
        reward_components=reward_components,
        tokens_input=usage["tokens_input"], tokens_output=usage["tokens_output"],
        tokens_total=usage["tokens_total"],
        duration_seconds=sim.duration,
        termination_reason=str(sim.termination_reason),
        infrastructure_errors=infra_error,
        # agent-side outcome flag derived from the native termination reason (sim.info is
        # never populated by the native orchestrator). AGENT_ERROR/USER_ERROR/MAX_STEPS/
        # TOO_MANY_ERRORS are AGENT OUTCOMES (kept for ITT), not infra failures.
        agent_errors=(str(sim.termination_reason)
                      if any(k in str(sim.termination_reason)
                             for k in ("AGENT_ERROR", "USER_ERROR", "MAX_STEPS", "TOO_MANY_ERRORS"))
                      else None),
        seed=seed, max_steps=max_steps,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["retail", "airline"])
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--model", required=True, choices=list(MODEL_ENDPOINTS))
    ap.add_argument("--condition", required=True, choices=["C0", "C1", "C2", "C3", "C4"])
    ap.add_argument("--replicate", type=int, required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--max-steps", type=int, default=100)
    ap.add_argument("--out-root", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/traces")
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else 1000 + args.replicate
    out_path = (args.out_root / args.domain / args.task_id / args.model /
                args.condition / f"rep_{args.replicate}.json")
    if args.skip_existing and out_path.exists():
        print(f"SKIP existing {out_path}")
        return 0
    try:
        rec = run_one(args.domain, args.task_id, args.model, args.condition,
                      args.replicate, max_steps=args.max_steps, seed=seed, out_path=out_path)
        print(f"OK {rec['run_id']} reward={rec['official_reward']} "
              f"db={rec['reward_components']['db_component']} "
              f"term={rec['termination_reason']} tools={len(rec['agent_tool_calls'])} "
              f"tokens={rec['tokens_total']}")
        return 0
    except Exception as exc:  # noqa: BLE001 - infra failure: record, do not fake an outcome
        err = {"error": repr(exc)[:300], "traceback": traceback.format_exc()[-1500:]}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        (out_path.with_suffix(".error.json")).write_text(json.dumps(err, indent=2))
        print(f"INFRA-FAIL {args.domain}/{args.task_id}/{args.model}/{args.condition}"
              f"/rep{args.replicate}: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
