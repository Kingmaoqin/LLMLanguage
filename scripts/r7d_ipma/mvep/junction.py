"""Prospective, event-bound MVEP junction proofs."""
from __future__ import annotations

from typing import Any


def validate_junction(proof: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    observations = proof.get("recorded_observations")
    remaining = proof.get("remaining_required_path")
    if not isinstance(observations, list) or not observations:
        failures.append("no_recorded_observation")
    if not isinstance(remaining, list) or not remaining:
        failures.append("no_concrete_remaining_path")
    if proof.get("junction_after_event_id") not in {
        item.get("event_id") for item in observations or [] if isinstance(item, dict)
    }:
        failures.append("junction_not_bound_to_observation")
    evidence_ids = [item.get("evidence_id") for item in observations or []
                    if isinstance(item, dict)]
    if None in evidence_ids or len(evidence_ids) != len(set(evidence_ids)):
        failures.append("evidence_not_uniquely_bound")
    for item in observations or []:
        if not isinstance(item, dict) or not all(item.get(k) for k in (
            "event_id", "evidence_id", "tool_name", "arguments_hash", "response_hash",
        )):
            failures.append("observation_binding_incomplete")
            break
    for item in remaining or []:
        if not isinstance(item, dict) or not all(item.get(k) for k in (
            "required_action_id", "tool_name", "target_binding", "reason",
        )):
            failures.append("remaining_action_not_concrete")
            break
    if proof.get("suffix_required") is not True:
        failures.append("suffix_not_required")
    if proof.get("mutation_consumed") is not False:
        failures.append("mutation_already_consumed")
    if proof.get("confirmation_consumed") is not False:
        failures.append("confirmation_already_consumed")
    if proof.get("label") == "pre_confirmation" and proof.get("confirmation_asked") is True:
        failures.append("confirmation_already_asked")
    if proof.get("task_kind") not in {"write", "no_write_communication"}:
        failures.append("unknown_task_kind")
    return not failures, sorted(set(failures))


def assert_valid_junction(proof: dict[str, Any]) -> None:
    passed, failures = validate_junction(proof)
    if not passed:
        raise ValueError("junction_proof_failed:" + ",".join(failures))

