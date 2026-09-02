#!/usr/bin/env python3
"""R7-D Step 2.1 Gate G1: official tau2 endpoint scorer, closed.

Step 2's endpoint pillar failed because the pilot hand-built a SimulationRun whose
AssistantMessages carried no `.tool_calls`, so the official evaluator's replay
(Environment.set_state(message_history=...)) had nothing to reconstruct and returned
None on 120/120 rows.

The evaluator (evaluator_env.calculate_reward) reconstructs the *predicted* DB purely
by replaying the message trajectory into a fresh environment, then compares its DB
hash to a *gold* environment that executed task.evaluation_criteria.actions. The only
requirement is therefore that `simulation.messages` be PROPER tau2 Message objects:
    AssistantMessage(tool_calls=[ToolCall(id=..., name=..., arguments=...)]),
    ToolMessage(id == that ToolCall.id, ...), ...
in that order, with matching ids.

This module provides:
  * official_reward(messages, task, domain) -> RewardInfo   (native evaluate_simulation)
  * a golden-action replay that builds a KNOWN-PASS trajectory (reward should be 1)
  * a KNOWN-FAIL trajectory (no/incorrect actions -> reward 0, but NON-None)

No mutation-count proxy is used anywhere. All local; nothing external is touched.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage
from tau2.data_model.simulation import RewardInfo, SimulationRun, TerminationReason
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation

# A fixed timestamp so SimulationRun construction is deterministic (Date.now-free).
_TS = "2026-07-12T00:00:00"


def configure_local_nl_judge(model: str = "openai/mistral-small-3p2",
                             api_base: str = "http://127.0.0.1:8007/v1") -> None:
    """Point tau2's NL-assertion (COMMUNICATE) judge at a LOCAL vLLM model so the
    COMMUNICATE reward path is reachable without any external API key. The judge is
    only used to READ the COMMUNICATE diagnostic; the deterministic pass/fail gate
    uses EvaluationType.ENV (DB-based) and does not depend on it."""
    import tau2.config as cfg
    # response_format json_object forces raw JSON so tau2's json.loads(content) parses
    # (the NL evaluator does not strip markdown fences).
    cfg.DEFAULT_LLM_NL_ASSERTIONS = model
    cfg.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": 0.0, "api_base": api_base, "api_key": "EMPTY", "num_retries": 2,
        "response_format": {"type": "json_object"},
    }
    # the evaluator imported these names at module load; rebind there too
    import tau2.evaluator.evaluator_nl_assertions as nl
    nl.DEFAULT_LLM_NL_ASSERTIONS = model
    nl.DEFAULT_LLM_NL_ASSERTIONS_ARGS = cfg.DEFAULT_LLM_NL_ASSERTIONS_ARGS


def get_env(domain: str):
    mod = __import__(f"tau2.domains.{domain}.environment", fromlist=["get_environment"])
    return mod.get_environment()


def official_reward(messages: list, task, domain: str,
                    evaluation_type: EvaluationType = EvaluationType.ALL,
                    solo_mode: bool = False) -> RewardInfo:
    """Score a message trajectory with the official tau2 evaluator (no proxy)."""
    sim = SimulationRun(
        id=str(uuid.uuid4()),
        task_id=str(task.id),
        messages=messages,
        trial=0,
        seed=0,
        start_time=_TS,
        end_time=_TS,
        duration=0.0,
        termination_reason=TerminationReason.AGENT_STOP,
    )
    return evaluate_simulation(
        simulation=sim, task=task, evaluation_type=evaluation_type,
        solo_mode=solo_mode, domain=domain,
    )


def golden_trajectory(task, domain: str) -> list:
    """Build a KNOWN-PASS message trajectory by executing the task's golden actions
    against a fresh env via env.get_response (which returns properly-id'd ToolMessages).
    Returns [AssistantMessage(tool_calls=[tc]), ToolMessage, ...]."""
    env = get_env(domain)
    actions = task.evaluation_criteria.actions or []
    msgs: list = []
    for i, action in enumerate(actions):
        tc = ToolCall(id=f"g{i}", name=action.name, arguments=dict(action.arguments),
                      requestor=action.requestor)
        if action.requestor == "user":
            msgs.append(UserMessage(role="user", content=None, tool_calls=[tc]))
        else:
            msgs.append(AssistantMessage(role="assistant", content=None, tool_calls=[tc]))
        tm = env.get_response(tc)  # real ToolMessage with id == tc.id
        msgs.append(tm)
    return msgs


def broken_trajectory(task, domain: str) -> list:
    """A KNOWN-FAIL trajectory: the agent chats but performs none of the golden
    mutations, so the predicted DB stays at initial != gold. Reward should be 0."""
    return [
        UserMessage(role="user", content="Hi, I have a request."),
        AssistantMessage(role="assistant", content="I'm sorry, I cannot help with that."),
    ]


if __name__ == "__main__":
    import json
    import pathlib
    import sys
    from tau2.run import get_tasks

    ROOT = pathlib.Path(__file__).resolve().parents[3]
    OUT = ROOT / "results/r7d_ipma/step2_1/integrity/g1_scorer_fixtures.json"

    # Deterministic pass/fail uses EvaluationType.ENV (DB-based; no LLM judge).
    FIXTURES = [("retail", "60"), ("airline", "8"), ("telecom", None)]
    rows = []
    all_ok = True
    print(f"{'domain':9s} {'task':30s} {'pass(ENV)':10s} {'fail(ENV)':10s} verdict")
    for domain, tid in FIXTURES:
        tasks = get_tasks(domain)
        task = (next(t for t in tasks if t.evaluation_criteria and t.evaluation_criteria.actions)
                if tid is None else next(t for t in tasks if str(t.id) == tid))
        try:
            rp = official_reward(golden_trajectory(task, domain), task, domain, EvaluationType.ENV)
            rf = official_reward(broken_trajectory(task, domain), task, domain, EvaluationType.ENV)
            pass_ok = rp.reward is not None and rp.reward >= 0.999
            fail_ok = rf.reward is not None and rf.reward < 0.999
            ok = pass_ok and fail_ok
            all_ok &= ok
            rows.append(dict(domain=domain, task_id=str(task.id),
                             known_pass_reward_ENV=rp.reward, known_fail_reward_ENV=rf.reward,
                             db_match_pass=getattr(rp.db_check, "db_match", None),
                             db_match_fail=getattr(rf.db_check, "db_match", None),
                             n_action_checks=len(rp.action_checks or []),
                             n_env_assertions=len(rp.env_assertions or []),
                             n_nl_assertions=len(task.evaluation_criteria.nl_assertions or []),
                             verdict="PASS" if ok else "FAIL"))
            print(f"{domain:9s} {str(task.id)[:30]:30s} {str(rp.reward):10s} {str(rf.reward):10s} "
                  f"{'PASS' if ok else 'FAIL'}")
        except Exception as exc:  # noqa: BLE001
            all_ok = False
            rows.append(dict(domain=domain, task_id=str(task.id), error=repr(exc)[:200], verdict="FAIL"))
            print(f"{domain:9s} {str(task.id)[:30]:30s} EXCEPTION {exc!r}")

    # COMMUNICATE reachability: point NL judge local, run ALL on retail 60 golden,
    # show communicate_checks are populated (not None) -> the COMMUNICATE field reads.
    comm_ok = False
    try:
        configure_local_nl_judge()
        t60 = next(t for t in get_tasks("retail") if str(t.id) == "60")
        rc = official_reward(golden_trajectory(t60, "retail"), t60, "retail", EvaluationType.ALL)
        comm = rc.communicate_checks
        comm_ok = comm is not None
        rows.append(dict(check="COMMUNICATE_reachability", domain="retail", task_id="60",
                         reward_ALL=rc.reward, n_communicate_checks=len(comm or []),
                         reward_basis=[str(x) for x in (rc.reward_basis or [])],
                         verdict="PASS" if comm_ok else "FAIL"))
        print(f"\nCOMMUNICATE reachability (local NL judge): communicate_checks="
              f"{len(comm or [])} reward_ALL={rc.reward}  -> {'PASS' if comm_ok else 'FAIL'}")
    except Exception as exc:  # noqa: BLE001
        rows.append(dict(check="COMMUNICATE_reachability", error=repr(exc)[:200], verdict="FAIL"))
        print(f"\nCOMMUNICATE reachability EXCEPTION {exc!r}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(env_fixtures=rows, all_env_fixtures_pass=all_ok,
                                   communicate_reachable=comm_ok), indent=2, ensure_ascii=False))
    verdict = all_ok and comm_ok
    print(f"\nG1 fixture gate (ENV pass/fail + COMMUNICATE reachable): {'PASS' if verdict else 'FAIL'}")
    print(f"wrote {OUT}")
    sys.exit(0 if verdict else 1)
