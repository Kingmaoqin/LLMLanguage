#!/usr/bin/env python3
"""Independent REFERENCE reimplementation of the process metrics (spec 10, 18).

Spec 18 requires the primary metrics and endpoint transitions to be double-computed by a
production and an independent reference implementation with 0 mismatch before analysis.
This module deliberately re-derives the same quantities from the raw episode dict by a
DIFFERENT code path (dict access + explicit loops, no shared helpers with
extract_metrics.py) so a bug in one is unlikely to be mirrored in the other.
"""
from __future__ import annotations

from typing import Any

MAX_EPISODE_STEPS_DEFAULT = 20


def _calls(ep: dict) -> list[dict]:
    return list(ep.get("tool_calls") or [])


def ref_first_mutation(ep: dict) -> int | None:
    i = 0
    for c in _calls(ep):
        if c.get("mutating") and c.get("ok"):
            return i
        i += 1
    return None


def ref_compression_depth(ep: dict, max_episode_steps: int = MAX_EPISODE_STEPS_DEFAULT) -> float:
    calls = _calls(ep)
    denom = ep.get("min_prereq_verification_calls") or 1
    if denom < 1:
        denom = 1
    fm = ref_first_mutation(ep)
    if fm is None:
        return float(max_episode_steps + 1)
    reads = 0
    for c in calls[:fm]:
        if not c.get("ok"):
            continue
        tt = c.get("tool_type")
        is_read = (tt == "READ") if tt is not None else (not c.get("mutating"))
        if is_read:
            reads += 1
    return reads / denom


def ref_inflation_effort(ep: dict) -> float:
    calls = _calls(ep)
    denom = ep.get("min_viable_total_verification_calls") or 1
    if denom < 1:
        denom = 1
    reads = 0
    for c in calls:
        if not c.get("ok"):
            continue
        tt = c.get("tool_type")
        is_read = (tt == "READ") if tt is not None else (not c.get("mutating"))
        if is_read:
            reads += 1
    return reads / denom


def ref_endpoint_success(ep: dict) -> int:
    return 1 if (ep.get("endpoint") or {}).get("success") == 1 else 0


def ref_outcome_class(ep: dict) -> str:
    if ep.get("infra_failure"):
        return "infrastructure_failure"
    endpoint = ep.get("endpoint") or {}
    if endpoint.get("success") == 1:
        return "correct_endpoint"
    calls = _calls(ep)
    parser_fail = any(
        (not c.get("ok")) and (c.get("error") == "unparsed_arguments"
                               or "__unparsed__" in (c.get("arguments") or {}))
        for c in calls
    )
    if parser_fail and all(not c.get("mutating") for c in calls):
        return "tool_parser_failure"
    term = (endpoint.get("termination_reason") or "").lower()
    if term in ("step_limit", "step_budget", "message_budget", "watchdog_timeout", "budget_exhausted"):
        return "budget_exhausted"
    if ref_first_mutation(ep) is None:
        return "no_state_change"
    return "wrong_state_changing"


def ref_primary(ep: dict, family: str, max_episode_steps: int = MAX_EPISODE_STEPS_DEFAULT) -> float:
    if family == "compression":
        return ref_compression_depth(ep, max_episode_steps)
    if family == "inflation":
        return ref_inflation_effort(ep)
    raise ValueError(family)


def recompute(ep: dict, max_episode_steps: int = MAX_EPISODE_STEPS_DEFAULT) -> dict[str, Any]:
    """Everything spec 18 double-checks, for one episode."""
    return {
        "compression_verification_depth": ref_compression_depth(ep, max_episode_steps),
        "inflation_verification_effort": ref_inflation_effort(ep),
        "endpoint_success": ref_endpoint_success(ep),
        "outcome_class": ref_outcome_class(ep),
        "first_state_changing_step": ref_first_mutation(ep),
    }


def compare(production_rec: dict, max_episode_steps: int = MAX_EPISODE_STEPS_DEFAULT, tol: float = 1e-9) -> list[str]:
    """Return mismatches between the stored production metrics and the reference recompute."""
    ref = recompute(production_rec, max_episode_steps)
    proc = production_rec.get("process") or {}
    problems: list[str] = []

    prod_depth = (proc.get("compression") or {}).get("verification_depth")
    if prod_depth is not None and abs(float(prod_depth) - ref["compression_verification_depth"]) > tol:
        problems.append(f"compression depth {prod_depth} != ref {ref['compression_verification_depth']}")

    prod_effort = (proc.get("inflation") or {}).get("verification_effort")
    if prod_effort is not None and abs(float(prod_effort) - ref["inflation_verification_effort"]) > tol:
        problems.append(f"inflation effort {prod_effort} != ref {ref['inflation_verification_effort']}")

    if production_rec.get("outcome_class") and production_rec["outcome_class"] != ref["outcome_class"]:
        problems.append(f"outcome_class {production_rec['outcome_class']} != ref {ref['outcome_class']}")

    prod_success = (production_rec.get("endpoint") or {}).get("success")
    if prod_success is not None and int(prod_success) != ref["endpoint_success"]:
        problems.append(f"endpoint.success {prod_success} != ref {ref['endpoint_success']}")

    return problems
