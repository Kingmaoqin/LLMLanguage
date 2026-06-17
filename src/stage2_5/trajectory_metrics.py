"""Tool-trajectory diagnostics for Stage-2.5."""

from __future__ import annotations

from collections import Counter
import json
from typing import Any

from src.adapters.normalize import IRREVERSIBLE_TOOLS


def tool_sequence(events: list[dict[str, Any]]) -> list[str]:
    return [str(e.get("tool_name")) for e in sorted(events, key=lambda x: int(x.get("step_index") or 0))]


def levenshtein(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, ai in enumerate(a, start=1):
        cur = [i]
        for j, bj in enumerate(b, start=1):
            cur.append(min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + (0 if ai == bj else 1),
            ))
        prev = cur
    return prev[-1]


def bag_jaccard_distance(a: list[str], b: list[str]) -> float:
    ca = Counter(a)
    cb = Counter(b)
    keys = set(ca) | set(cb)
    if not keys:
        return 0.0
    inter = sum(min(ca[k], cb[k]) for k in keys)
    union = sum(max(ca[k], cb[k]) for k in keys)
    return 1.0 - (inter / union)


def normalized_distance(distance: int | None, a: list[str], b: list[str]) -> float | None:
    if distance is None:
        return None
    denom = max(len(a), len(b), 1)
    return distance / denom


def mutation_sequence(events: list[dict[str, Any]]) -> list[str]:
    return [name for name in tool_sequence(events) if name in IRREVERSIBLE_TOOLS]


def _action_name(action: Any) -> str:
    return str(getattr(action, "name", ""))


def _action_arguments(action: Any) -> Any:
    return getattr(action, "arguments", None)


def _stable_args(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    except TypeError:
        return json.dumps(str(value), ensure_ascii=True)


def argument_signature(name: str, arguments: Any) -> str:
    return f"{name}:{_stable_args(arguments)}"


def event_argument_sequence(events: list[dict[str, Any]]) -> list[str]:
    return [
        argument_signature(str(e.get("tool_name")), e.get("arguments"))
        for e in sorted(events, key=lambda x: int(x.get("step_index") or 0))
    ]


def reference_tool_sequence(task: Any) -> list[str]:
    criteria = getattr(task, "evaluation_criteria", None)
    actions = getattr(criteria, "actions", None) or []
    return [_action_name(action) for action in actions if _action_name(action)]


def reference_argument_sequence(task: Any) -> list[str]:
    criteria = getattr(task, "evaluation_criteria", None)
    actions = getattr(criteria, "actions", None) or []
    return [
        argument_signature(_action_name(action), _action_arguments(action))
        for action in actions
        if _action_name(action)
    ]


def reference_mutation_sequence(task: Any) -> list[str]:
    return [name for name in reference_tool_sequence(task) if name in IRREVERSIBLE_TOOLS]


def trajectory_summary(events: list[dict[str, Any]], reference_task: Any | None = None) -> dict[str, Any]:
    seq = tool_sequence(events)
    mut_seq = mutation_sequence(events)
    ref_seq = reference_tool_sequence(reference_task) if reference_task is not None else []
    ref_arg_seq = reference_argument_sequence(reference_task) if reference_task is not None else []
    ref_mut_seq = reference_mutation_sequence(reference_task) if reference_task is not None else []
    arg_seq = event_argument_sequence(events)
    tool_dist = levenshtein(seq, ref_seq) if reference_task is not None else None
    arg_dist = levenshtein(arg_seq, ref_arg_seq) if reference_task is not None else None
    mutation_dist = levenshtein(mut_seq, ref_mut_seq) if reference_task is not None else None
    return {
        "tool_sequence": " > ".join(seq),
        "tool_sequence_len": len(seq),
        "unique_tools": len(set(seq)),
        "read_calls": sum(1 for e in events if e.get("mutation_type") == "read"),
        "write_calls": sum(1 for e in events if e.get("mutation_type") == "write"),
        "mutation_sequence": " > ".join(mut_seq),
        "mutation_sequence_len": len(mut_seq),
        "reference_tool_sequence_len": len(ref_seq) if reference_task is not None else None,
        "reference_mutation_sequence_len": len(ref_mut_seq) if reference_task is not None else None,
        "tool_name_sequence_distance": tool_dist,
        "tool_name_sequence_norm_distance": normalized_distance(tool_dist, seq, ref_seq),
        "critical_argument_sequence_distance": arg_dist,
        "critical_argument_sequence_norm_distance": normalized_distance(arg_dist, arg_seq, ref_arg_seq),
        "mutation_sequence_distance": mutation_dist,
        "mutation_sequence_norm_distance": normalized_distance(mutation_dist, mut_seq, ref_mut_seq),
    }
