"""Reference and matched-neutral trajectory diagnostics for Stage-2.5b."""

from __future__ import annotations

from collections import Counter
import json
from typing import Any

from src.adapters.normalize import IRREVERSIBLE_TOOLS


def tool_sequence(events: list[dict[str, Any]]) -> list[str]:
    return [
        str(event.get("tool_name"))
        for event in sorted(
            events,
            key=lambda event: int(event.get("step_index") or 0),
        )
    ]


def levenshtein(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for i, left_item in enumerate(left, start=1):
        current = [i]
        for j, right_item in enumerate(right, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (0 if left_item == right_item else 1),
                )
            )
        previous = current
    return previous[-1]


def bag_jaccard_distance(left: list[str], right: list[str]) -> float:
    left_counts = Counter(left)
    right_counts = Counter(right)
    keys = set(left_counts) | set(right_counts)
    if not keys:
        return 0.0
    intersection = sum(
        min(left_counts[key], right_counts[key]) for key in keys
    )
    union = sum(max(left_counts[key], right_counts[key]) for key in keys)
    return 1.0 - (intersection / union)


def normalized_distance(
    distance: int | None,
    left: list[str],
    right: list[str],
) -> float | None:
    if distance is None:
        return None
    return distance / max(len(left), len(right), 1)


def mutation_sequence(events: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in tool_sequence(events)
        if name in IRREVERSIBLE_TOOLS
    ]


def _stable_args(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )
    except TypeError:
        return json.dumps(str(value), ensure_ascii=True)


def argument_signature(name: str, arguments: Any) -> str:
    return f"{name}:{_stable_args(arguments)}"


def event_argument_sequence(events: list[dict[str, Any]]) -> list[str]:
    return [
        argument_signature(
            str(event.get("tool_name")),
            event.get("arguments"),
        )
        for event in sorted(
            events,
            key=lambda event: int(event.get("step_index") or 0),
        )
    ]


def reference_tool_sequence(task: Any) -> list[str]:
    criteria = getattr(task, "evaluation_criteria", None)
    actions = getattr(criteria, "actions", None) or []
    return [
        str(getattr(action, "name", ""))
        for action in actions
        if getattr(action, "name", "")
    ]


def reference_argument_sequence(task: Any) -> list[str]:
    criteria = getattr(task, "evaluation_criteria", None)
    actions = getattr(criteria, "actions", None) or []
    return [
        argument_signature(
            str(getattr(action, "name", "")),
            getattr(action, "arguments", None),
        )
        for action in actions
        if getattr(action, "name", "")
    ]


def reference_mutation_sequence(task: Any) -> list[str]:
    return [
        name
        for name in reference_tool_sequence(task)
        if name in IRREVERSIBLE_TOOLS
    ]


def trajectory_summary(
    events: list[dict[str, Any]],
    reference_task: Any | None = None,
) -> dict[str, Any]:
    tools = tool_sequence(events)
    arguments = event_argument_sequence(events)
    mutations = mutation_sequence(events)
    reference_tools = (
        reference_tool_sequence(reference_task)
        if reference_task is not None
        else []
    )
    reference_arguments = (
        reference_argument_sequence(reference_task)
        if reference_task is not None
        else []
    )
    reference_mutations = (
        reference_mutation_sequence(reference_task)
        if reference_task is not None
        else []
    )
    tool_edit = (
        levenshtein(tools, reference_tools)
        if reference_task is not None
        else None
    )
    argument_edit = (
        levenshtein(arguments, reference_arguments)
        if reference_task is not None
        else None
    )
    mutation_edit = (
        levenshtein(mutations, reference_mutations)
        if reference_task is not None
        else None
    )
    reference_tool_distance = normalized_distance(
        tool_edit,
        tools,
        reference_tools,
    )
    reference_argument_distance = normalized_distance(
        argument_edit,
        arguments,
        reference_arguments,
    )
    reference_mutation_distance = normalized_distance(
        mutation_edit,
        mutations,
        reference_mutations,
    )
    return {
        "tool_sequence": " > ".join(tools),
        "tool_sequence_len": len(tools),
        "unique_tools": len(set(tools)),
        "read_calls": sum(
            1 for event in events if event.get("mutation_type") == "read"
        ),
        "write_calls": sum(
            1 for event in events if event.get("mutation_type") == "write"
        ),
        "mutation_sequence": " > ".join(mutations),
        "mutation_sequence_len": len(mutations),
        "reference_tool_sequence_len": (
            len(reference_tools) if reference_task is not None else None
        ),
        "reference_mutation_sequence_len": (
            len(reference_mutations) if reference_task is not None else None
        ),
        "reference_tool_distance": reference_tool_distance,
        "reference_argument_distance": reference_argument_distance,
        "reference_mutation_distance": reference_mutation_distance,
        "tool_name_sequence_distance": tool_edit,
        "tool_name_sequence_norm_distance": reference_tool_distance,
        "critical_argument_sequence_distance": argument_edit,
        "critical_argument_sequence_norm_distance": (
            reference_argument_distance
        ),
        "mutation_sequence_distance": mutation_edit,
        "mutation_sequence_norm_distance": reference_mutation_distance,
    }


def matched_neutral_distances(
    treatment_events: list[dict[str, Any]],
    neutral_events: list[dict[str, Any]],
    *,
    treatment_branch_labels: list[str] | None = None,
    neutral_branch_labels: list[str] | None = None,
) -> dict[str, float]:
    treatment_tools = tool_sequence(treatment_events)
    neutral_tools = tool_sequence(neutral_events)
    treatment_arguments = event_argument_sequence(treatment_events)
    neutral_arguments = event_argument_sequence(neutral_events)
    treatment_mutations = mutation_sequence(treatment_events)
    neutral_mutations = mutation_sequence(neutral_events)
    treatment_branches = treatment_branch_labels or []
    neutral_branches = neutral_branch_labels or []
    return {
        "matched_neutral_tool_distance": (
            normalized_distance(
                levenshtein(treatment_tools, neutral_tools),
                treatment_tools,
                neutral_tools,
            )
            or 0.0
        ),
        "matched_neutral_argument_distance": (
            normalized_distance(
                levenshtein(treatment_arguments, neutral_arguments),
                treatment_arguments,
                neutral_arguments,
            )
            or 0.0
        ),
        "matched_neutral_mutation_distance": (
            normalized_distance(
                levenshtein(treatment_mutations, neutral_mutations),
                treatment_mutations,
                neutral_mutations,
            )
            or 0.0
        ),
        "matched_neutral_branch_divergence": (
            normalized_distance(
                levenshtein(treatment_branches, neutral_branches),
                treatment_branches,
                neutral_branches,
            )
            or 0.0
        ),
    }
