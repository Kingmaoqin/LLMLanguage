#!/usr/bin/env python3
"""R7-D Step 2.3: official scorer returning the REWARD COMPONENT BREAKDOWN.

To decompose the T2 failure we must distinguish "DB correct but COMMUNICATE fails"
from "DB wrong". This scores a real message trajectory with the official evaluator and
returns the DB / COMMUNICATE / ACTION components separately. COMMUNICATE uses a LOCAL
NL judge (repointed via official_scorer.configure_local_nl_judge).
"""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.r7d_ipma.step2_1.official_scorer import official_reward, configure_local_nl_judge  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType  # noqa: E402

_CONFIGURED = False


def components(messages: list, task, domain: str) -> dict:
    """Return DB reward (deterministic, ENV) + COMMUNICATE component (local judge, ALL)."""
    global _CONFIGURED
    out: dict = {}
    # DB / env reward (deterministic, no judge)
    try:
        env_r = official_reward(messages, task, domain, EvaluationType.ENV)
        out["env_reward"] = env_r.reward
        out["db_match"] = getattr(env_r.db_check, "db_match", None)
        out["n_env_assertions"] = len(env_r.env_assertions or [])
        out["scorable"] = env_r.reward is not None
    except Exception as exc:  # noqa: BLE001
        out["env_reward"] = None
        out["env_error"] = repr(exc)[:120]
        out["scorable"] = False
    # ALL reward (DB + COMMUNICATE via local NL judge)
    try:
        if not _CONFIGURED:
            configure_local_nl_judge()
            _CONFIGURED = True
        all_r = official_reward(messages, task, domain, EvaluationType.ALL)
        comm = all_r.communicate_checks
        out["all_reward"] = all_r.reward
        out["n_communicate_checks"] = len(comm or [])
        out["communicate_met"] = (sum(1 for c in (comm or []) if getattr(c, "met", False))
                                  if comm else None)
        out["reward_basis"] = [str(x) for x in (all_r.reward_basis or [])]
    except Exception as exc:  # noqa: BLE001
        out["all_reward"] = None
        out["all_error"] = repr(exc)[:120]
    return out


def classify_t2_failure(diag: dict) -> str:
    """Map a T2 N1 run's diagnostics to one of the 7 failure categories."""
    if not diag.get("junction_found"):
        return "invalid_junction"
    if diag.get("parser_errors", 0) > 0 or diag.get("suffix_tool_errors", 0) > 0:
        return "tool_or_parser_error"
    if diag.get("suffix_mutations", 0) == 0:
        # agent reached confirmation but never executed a mutation in the suffix
        if diag.get("agent_kept_asking"):
            return "insufficient_user_decision_info"
        return "agent_did_not_execute_mutation"
    # a mutation happened
    if diag.get("env_reward") == 1.0:
        return "success"  # DB correct
    if diag.get("db_match") is False and diag.get("all_reward") is not None and \
       diag.get("env_reward") == 0.0 and diag.get("communicate_met") == 0:
        return "db_wrong_and_communicate_fail"
    if diag.get("db_match") is True and diag.get("all_reward", 1.0) < 1.0:
        return "db_correct_but_communicate_fail"
    return "wrong_mutation"  # mutated but DB != gold
