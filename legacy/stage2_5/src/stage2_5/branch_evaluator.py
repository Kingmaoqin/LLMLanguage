"""Policy-annotation branch diagnostics for Stage-2.5."""

from __future__ import annotations

from typing import Any


def _first_step(events: list[dict[str, Any]], tools: set[str]) -> int | None:
    for event in events:
        if event.get("tool_name") in tools:
            return int(event.get("step_index") or 0)
    return None


def _fact_source_tools(annotation: dict[str, Any], fact_id: str) -> set[str]:
    for fact in annotation.get("required_facts") or []:
        if fact.get("fact_id") == fact_id:
            return {s.get("tool_name") for s in fact.get("admissible_sources") or []}
    return set()


def evaluate_branches(
    events: list[dict[str, Any]],
    annotation: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for branch in annotation.get("branch_points") or []:
        source_tools = _fact_source_tools(annotation, branch.get("trigger_fact"))
        valid_actions = set(branch.get("valid_actions") or [])
        invalid_actions = set(branch.get("invalid_actions") or [])
        source_step = _first_step(events, source_tools)
        valid_step = _first_step(events, valid_actions)
        invalid_step = _first_step(events, invalid_actions)

        if source_step is None:
            classification = "not_reached"
        elif invalid_step is not None and (valid_step is None or invalid_step < valid_step):
            classification = "premature_or_invalid_action"
        elif valid_step is None:
            classification = "missed_revision"
        elif valid_step < source_step:
            classification = "premature_action"
        else:
            classification = "correct_revision"

        rows.append({
            "branch_id": branch.get("branch_id"),
            "trigger_fact": branch.get("trigger_fact"),
            "source_step": source_step,
            "first_valid_action_step": valid_step,
            "first_invalid_action_step": invalid_step,
            "classification": classification,
        })
    return rows
