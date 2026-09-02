"""R6 trace validation helpers.

R6 traces intentionally remain compatible with the Stage-2.5b canonical trace
schema, but R6 analysis also relies on additional provenance and interactional
fields. This validator checks those R6-specific fields before metrics/analysis.
"""

from __future__ import annotations

from typing import Any

from src.stage2_5b.metrics.trace_metrics import validate_trace as validate_stage2_trace


R6_REQUIRED_TOP_LEVEL_LISTS = (
    "field_level_state_diff",
    "confirmation_events",
    "refusal_events",
    "boundary_events",
    "privacy_events",
    "unsafe_events",
)


def validate_r6_trace(trace: dict[str, Any]) -> list[str]:
    errors = validate_stage2_trace(trace)
    meta = trace.get("run_meta") or {}
    for key in ("executor", "executor_mode", "model_call_performed"):
        if key not in meta:
            errors.append(f"missing run_meta.{key}")
    for key in R6_REQUIRED_TOP_LEVEL_LISTS:
        if not isinstance(trace.get(key), list):
            errors.append(f"{key} must be a list")
    if not isinstance(trace.get("initial_environment_state"), dict):
        errors.append("initial_environment_state must be a dict")
    final = trace.get("final_environment_state")
    if not isinstance(final, dict) or "state_hash" not in final:
        errors.append("final_environment_state.state_hash missing")
    return errors

