#!/usr/bin/env python3
"""Evaluation-only ordered trajectory comparison.

The module deliberately has no dependency on an agent, prompt, condition selector, or
runtime gate.  It normalizes JSON representation only: action order, duplicate actions,
argument values, target values, and list multiplicity remain semantic.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from copy import deepcopy
from typing import Any, Iterable


class TrajectoryError(ValueError):
    """A trace cannot be evaluated without semantic normalization."""


def canonicalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TrajectoryError("non_string_object_key")
        return {key: canonicalize_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [canonicalize_json(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TrajectoryError("unsupported_or_non_finite_json_value")


def canonical_json(value: Any) -> str:
    return json.dumps(canonicalize_json(value), ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


@dataclasses.dataclass(frozen=True)
class Action:
    name: str
    arguments: Any
    target: Any
    mutating: bool
    call_id: str | None = None
    error: bool = False

    def semantic(self) -> dict[str, Any]:
        return canonicalize_json({
            "name": self.name,
            "arguments": self.arguments,
            "target": self.target,
            "mutating": self.mutating,
            "error": self.error,
        })


def _target_from(arguments: Any, target_keys: Iterable[str]) -> Any:
    if not isinstance(arguments, dict):
        return None
    present = {key: arguments[key] for key in target_keys if key in arguments}
    return present or None


def action_from_mapping(item: dict[str, Any], mutation_tools: set[str],
                        target_keys: Iterable[str]) -> Action:
    """Accept a compact action or an OpenAI/tau2-like tool-call mapping."""
    function = item.get("function") if isinstance(item.get("function"), dict) else {}
    name = item.get("name", function.get("name"))
    arguments = item.get("arguments", function.get("arguments", {}))
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise TrajectoryError("arguments_not_json") from exc
    if not isinstance(name, str) or not name.strip():
        raise TrajectoryError("missing_tool_name")
    arguments = canonicalize_json(arguments)
    target = item.get("target", _target_from(arguments, target_keys))
    mutating = item.get("mutating", name in mutation_tools)
    if not isinstance(mutating, bool):
        raise TrajectoryError("mutating_not_boolean")
    return Action(name=name, arguments=arguments, target=canonicalize_json(target),
                  mutating=mutating, call_id=item.get("id"),
                  error=bool(item.get("error", False)))


def extract_actions(trace: Any, mutation_tools: set[str],
                    target_keys: Iterable[str] = (
                        "user_id", "order_id", "reservation_id", "line_id",
                        "item_id", "product_id", "confirmation_number",
                    )) -> list[Action]:
    """Extract ordered calls from a list, or from {actions|messages: [...]}.

    Message mappings may contain ``tool_calls``; compact action mappings may be placed
    directly in ``actions``. Nothing is sorted or deduplicated.
    """
    rows = trace
    if isinstance(trace, dict):
        rows = trace.get("actions", trace.get("messages"))
    if not isinstance(rows, list):
        raise TrajectoryError("trace_has_no_ordered_list")
    output: list[Action] = []
    for row in rows:
        if not isinstance(row, dict):
            raise TrajectoryError("trace_row_not_object")
        calls = row.get("tool_calls")
        if calls is None and ("name" in row or "function" in row):
            calls = [row]
        if calls is None:
            continue
        if not isinstance(calls, list):
            raise TrajectoryError("tool_calls_not_list")
        output.extend(action_from_mapping(call, mutation_tools, target_keys) for call in calls)
    return output


def _eq(left: Action, right: Action) -> bool:
    return left.semantic() == right.semantic()


def _edit_script(expected: list[Action], observed: list[Action]) -> list[dict[str, Any]]:
    """Deterministic Levenshtein script; substitution wins ties, then deletion."""
    n, m = len(expected), len(observed)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1,
                           dp[i - 1][j - 1] + (not _eq(expected[i - 1], observed[j - 1])))
    i, j = n, m
    reverse: list[dict[str, Any]] = []
    while i or j:
        if i and j and dp[i][j] == dp[i - 1][j - 1] + (not _eq(expected[i - 1], observed[j - 1])):
            if not _eq(expected[i - 1], observed[j - 1]):
                reverse.append({"op": "replace", "expected_index": i - 1,
                                "observed_index": j - 1})
            i -= 1
            j -= 1
        elif i and dp[i][j] == dp[i - 1][j] + 1:
            reverse.append({"op": "delete", "expected_index": i - 1,
                            "observed_index": j})
            i -= 1
        else:
            reverse.append({"op": "insert", "expected_index": i,
                            "observed_index": j - 1})
            j -= 1
    return list(reversed(reverse))


def _replacement_kind(left: Action, right: Action) -> list[str]:
    kinds = []
    if left.name != right.name:
        kinds.append("action_change")
    if left.target != right.target:
        kinds.append("target_change")
    if left.arguments != right.arguments:
        kinds.append("argument_change")
    if left.mutating != right.mutating:
        kinds.append("mutation_class_change")
    if left.error != right.error:
        kinds.append("error_status_change")
    return kinds or ["semantic_change"]


def compare_trajectories(expected_trace: Any, observed_trace: Any, *,
                         mutation_tools: set[str], endpoint_score_equal: bool,
                         final_db_equal: bool) -> dict[str, Any]:
    expected = extract_actions(expected_trace, mutation_tools)
    observed = extract_actions(observed_trace, mutation_tools)
    edits = _edit_script(expected, observed)
    expected_sem = [action.semantic() for action in expected]
    observed_sem = [action.semantic() for action in observed]
    for edit in edits:
        if edit["op"] == "replace":
            edit["kinds"] = _replacement_kind(
                expected[edit["expected_index"]], observed[edit["observed_index"]])
        elif edit["op"] == "insert":
            candidate = observed_sem[edit["observed_index"]]
            edit["kinds"] = ["duplicate" if candidate in expected_sem else "insertion"]
        else:
            candidate = expected_sem[edit["expected_index"]]
            edit["kinds"] = ["duplicate_deletion" if expected_sem.count(candidate) > 1 else "deletion"]
    if expected_sem != observed_sem and len(expected_sem) == len(observed_sem) \
            and sorted(map(canonical_json, expected_sem)) == sorted(map(canonical_json, observed_sem)):
        for edit in edits:
            edit.setdefault("kinds", []).append("reorder")
    first = edits[0] if edits else None
    process_equal = not edits
    mut_expected = [a.semantic() for a in expected if a.mutating]
    mut_observed = [a.semantic() for a in observed if a.mutating]
    return {
        "schema_version": "r7d-ordered-trajectory-v1",
        "expected_action_count": len(expected),
        "observed_action_count": len(observed),
        "ordered_action_edit_distance": len(edits),
        "edits": edits,
        "first_decisive_deviation": first,
        "ordered_tool_name_match": [a.name for a in expected] == [a.name for a in observed],
        "mutating_action_match": mut_expected == mut_observed,
        "process_equal": process_equal,
        "endpoint_score_equal": bool(endpoint_score_equal),
        "final_db_equal": bool(final_db_equal),
        "corrupt_success": bool(endpoint_score_equal and final_db_equal and not process_equal),
        "expected_digest": digest(expected_sem),
        "observed_digest": digest(observed_sem),
        "claim_boundary": (
            "Process divergence is descriptive. It is not PASR or attack success unless "
            "the separately frozen IPMA causal definition and controls are satisfied."
        ),
    }

