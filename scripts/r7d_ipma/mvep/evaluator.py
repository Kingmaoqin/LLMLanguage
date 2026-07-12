"""Trace-only endpoint, communication, and ordered-process evaluation."""
from __future__ import annotations

from typing import Any

from scripts.r7d_ipma.reproducibility.ordered_trajectory_evaluator import (
    compare_trajectories,
)


def deterministic_communication_score(trace: dict[str, Any],
                                      required_fragments: list[str]) -> dict[str, Any]:
    messages = trace.get("assistant_messages", [])
    text = "\n".join(str(item.get("content") or "") for item in messages
                     if isinstance(item, dict) and item.get("mvep_role") == "executor").casefold()
    found = {fragment: fragment.casefold() in text for fragment in required_fragments}
    passed = bool(text.strip()) and bool(required_fragments) and all(found.values())
    return {"type": "deterministic_required_communication", "required": required_fragments,
            "found": found, "nonempty_response": bool(text.strip()), "passed": passed}


def evaluate_trace(trace: dict[str, Any], expected_actions: list[dict[str, Any]], *,
                   mutation_tools: set[str], official_env: dict[str, Any] | None,
                   required_communication: list[str]) -> dict[str, Any]:
    kind = trace["identity"]["task_kind"]
    if kind == "write":
        if official_env is None or official_env.get("reward") is None:
            raise ValueError("write_requires_official_env_score")
        endpoint = official_env
    elif kind == "no_write_communication":
        communication = deterministic_communication_score(trace, required_communication)
        endpoint = {"db_unchanged": trace["db"]["pre_hash"] == trace["db"]["post_hash"],
                    "communication": communication,
                    "passed": (trace["db"]["pre_hash"] == trace["db"]["post_hash"]
                               and communication["passed"])}
    else:
        raise ValueError("unknown_task_kind")
    process = compare_trajectories(
        {"actions": expected_actions}, {"actions": trace["tool_calls"]},
        mutation_tools=mutation_tools,
        endpoint_score_equal=True,
        final_db_equal=trace["db"]["pre_hash"] == trace["db"]["post_hash"]
        if kind == "no_write_communication" else bool(official_env.get("db_match")),
    )
    return {"endpoint": endpoint, "process": process,
            "runtime_influence": False,
            "claim_boundary": "MVEP pipeline validity only; no IPMA effect estimand."}
