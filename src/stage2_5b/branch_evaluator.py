"""Canonical branch-decision diagnostics for Stage-2.5b."""

from __future__ import annotations

from typing import Any


def _step(event: dict[str, Any]) -> int:
    try:
        return int(event.get("step_index") or 0)
    except (TypeError, ValueError):
        return 0


def _first_step(
    events: list[dict[str, Any]],
    tools: set[str],
) -> int | None:
    return next(
        (
            _step(event)
            for event in sorted(events, key=_step)
            if event.get("tool_name") in tools
        ),
        None,
    )


def _fact_source_tools(
    annotation: dict[str, Any],
    fact_id: str,
) -> set[str]:
    for fact in annotation.get("required_facts") or []:
        if fact.get("fact_id") == fact_id:
            return {
                str(source.get("tool_name"))
                for source in fact.get("admissible_sources") or []
                if source.get("tool_name")
            }
    return set()


def evaluate_branches(
    events: list[dict[str, Any]],
    annotation: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for branch in annotation.get("branch_points") or []:
        source_tools = _fact_source_tools(
            annotation,
            str(branch.get("trigger_fact") or ""),
        )
        valid_actions = {
            str(action)
            for action in branch.get("valid_actions") or []
            if action
        }
        invalid_actions = {
            str(action)
            for action in branch.get("invalid_actions") or []
            if action
        } - valid_actions
        source_step = _first_step(events, source_tools)
        valid_step = _first_step(events, valid_actions)
        invalid_step = _first_step(events, invalid_actions)

        if source_step is None:
            classification = "not_reached"
        elif not valid_actions and not invalid_actions:
            classification = "reached_unscored"
        elif invalid_step is not None and (
            valid_step is None or invalid_step <= valid_step
        ):
            classification = "invalid_action"
        elif valid_step is None:
            classification = "missed_revision"
        elif valid_step < source_step:
            classification = "premature_action"
        else:
            classification = "correct_revision"

        rows.append(
            {
                "branch_id": branch.get("branch_id"),
                "trigger_fact": branch.get("trigger_fact"),
                "source_step": source_step,
                "first_valid_action_step": valid_step,
                "first_invalid_action_step": invalid_step,
                "classification": classification,
            }
        )
    return rows
