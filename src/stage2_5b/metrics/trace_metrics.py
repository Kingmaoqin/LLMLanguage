"""Trace schema + interactional-robustness metric extraction (round-5 §3-4).

The Stage-2.5b run bundles already persist the full per-run trajectory. This module
defines a *canonical, stable* trace view over a bundle and a single extraction function
that produces the multidimensional interactional-robustness profile for one run.

Design rules (round-5 §0):
- Endpoint metrics alone never decide robustness; we always emit tool / trajectory /
  policy / efficiency / conversation dimensions alongside.
- Uncomputable metrics are emitted as ``None`` (missing), never silently 0.
- ``total_tokens`` is recomputed with an explicit ``token_source`` provenance flag.
"""

from __future__ import annotations

from typing import Any

# ---- canonical trace schema -------------------------------------------------

# Top-level keys every reconstructed trace must carry. Kept intentionally close to the
# existing bundle so reconstruction is loss-free, not a re-design (round-5 §3).
TRACE_TOP_LEVEL = (
    "schema_version",
    "run_id",
    "run_meta",
    "conversation",
    "tool_events",
    "state_deltas",
    "controlled_user_events",
    "policy_failures",
    "branch_decisions",
    "final_environment_state",
    "token_usage",
)

REQUIRED_RUN_META = ("run_id", "model_alias", "task_id", "source_task_id", "condition_id", "seed")

TRACE_SCHEMA_VERSION = "stage2_5b_trace_v1"


def build_trace(bundle: dict[str, Any]) -> dict[str, Any]:
    """Assemble a canonical trace dict from a stored run bundle (loss-free view)."""
    meta = bundle.get("run_meta") or {}
    fes = bundle.get("final_environment_states") or []
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "run_id": meta.get("run_id"),
        "run_meta": meta,
        "conversation": bundle.get("conversation_logs") or [],
        "tool_events": bundle.get("normalized_tool_events") or [],
        "state_deltas": bundle.get("state_deltas") or [],
        "controlled_user_events": bundle.get("controlled_user_events") or [],
        "policy_failures": bundle.get("policy_failures") or [],
        "branch_decisions": bundle.get("branch_decisions") or [],
        "final_environment_state": fes[0] if fes else {},
        "token_usage": token_usage(bundle.get("metrics") or {}),
    }


def validate_trace(trace: dict[str, Any]) -> list[str]:
    """Return a list of schema violations (empty == valid)."""
    errors: list[str] = []
    for key in TRACE_TOP_LEVEL:
        if key not in trace:
            errors.append(f"missing top-level key: {key}")
    if trace.get("schema_version") != TRACE_SCHEMA_VERSION:
        errors.append(f"bad schema_version: {trace.get('schema_version')!r}")
    meta = trace.get("run_meta") or {}
    for key in REQUIRED_RUN_META:
        if not meta.get(key):
            errors.append(f"missing run_meta.{key}")
    for list_key in ("conversation", "tool_events", "controlled_user_events"):
        if not isinstance(trace.get(list_key), list):
            errors.append(f"{list_key} must be a list")
    tu = trace.get("token_usage") or {}
    if tu.get("token_source") not in {"reported_total", "prompt_plus_completion", "missing"}:
        errors.append(f"bad token_source: {tu.get('token_source')!r}")
    return errors


# ---- token recompute (round-5 §4) ------------------------------------------

def recompute_total_tokens(
    input_tokens: int | None,
    output_tokens: int | None,
    reported_total: int | None = None,
) -> tuple[int | None, str]:
    """(total_tokens, token_source). Missing inputs => (None, 'missing')."""
    it = int(input_tokens or 0)
    ot = int(output_tokens or 0)
    rt = int(reported_total or 0)
    if rt > 0:
        return rt, "reported_total"
    if it + ot > 0:
        return it + ot, "prompt_plus_completion"
    return None, "missing"


def token_usage(metrics: dict[str, Any]) -> dict[str, Any]:
    """Token usage view from a stored metrics row, with the bug-fixed total."""
    it = metrics.get("input_tokens")
    ot = metrics.get("output_tokens")
    # A previously-stored total may be the buggy 0; only trust it if positive.
    stored_total = metrics.get("total_tokens")
    reported = stored_total if metrics.get("token_source") == "reported_total" else None
    total, source = recompute_total_tokens(it, ot, reported)
    return {
        "input_tokens": int(it) if it is not None else None,
        "output_tokens": int(ot) if ot is not None else None,
        "tokens_total": total,
        "token_source": source,
    }


# ---- interactional-robustness profile (round-5 §4, §6) ---------------------

def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _b(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1"}


def interactional_metrics(trace: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """Full multidimensional profile for one run. Dimensions are explicitly grouped so no
    single endpoint number can stand in for interactional robustness (round-5 §2, §14)."""
    meta = trace.get("run_meta") or metrics
    tu = trace.get("token_usage") or token_usage(metrics)
    tool_events = trace.get("tool_events") or []
    state_deltas = trace.get("state_deltas") or []
    n_policy_failures = _num(metrics.get("n_policy_failures"))

    row: dict[str, Any] = {
        # identity
        "run_id": meta.get("run_id"),
        "model_alias": meta.get("model_alias"),
        "task_id": meta.get("task_id"),
        "source_task_id": meta.get("source_task_id"),
        "condition_id": meta.get("condition_id"),
        "seed": meta.get("seed"),
        "template_id": meta.get("template_id"),
        "template_block": meta.get("template_block"),
        "invalid_run": _b(metrics.get("invalid_run")),

        # --- 1. task execution (endpoint) ---
        "safe_task_success": _b(metrics.get("safe_task_success")),
        "local_proxy_success": _b(metrics.get("local_proxy_success")),
        "final_state_correct": _b(metrics.get("final_state_correct")),
        "official_reward_basis_success": _b(metrics.get("official_reward_basis_success")),
        "reward": _num(metrics.get("reward")),

        # --- 2. tool-call trajectory ---
        "agent_tool_calls": _num(metrics.get("agent_tool_calls")),
        "unique_tools": _num(metrics.get("unique_tools")),
        "read_calls": _num(metrics.get("read_calls")),
        "write_calls": _num(metrics.get("write_calls")),
        "tool_errors": _num(metrics.get("tool_errors")),
        "n_state_mutations": float(len(state_deltas)),
        "n_tool_events": float(len(tool_events)),

        # --- 3. trajectory divergence vs reference ---
        "tool_name_sequence_norm_distance": _num(metrics.get("tool_name_sequence_norm_distance")),
        "critical_argument_sequence_norm_distance": _num(metrics.get("critical_argument_sequence_norm_distance")),
        "mutation_sequence_norm_distance": _num(metrics.get("mutation_sequence_norm_distance")),

        # --- 4. safety / policy ---
        "n_policy_failures": n_policy_failures,
        "policy_failure_types": metrics.get("policy_failure_types") or "",
        "policy_failure_any": (n_policy_failures > 0) if n_policy_failures is not None else None,
        "mutation_before_evidence": _b(metrics.get("mutation_before_evidence")),
        "required_fact_coverage": _num(metrics.get("required_fact_coverage")),
        "first_mutation_step": _num(metrics.get("first_mutation_step")),

        # --- 5. efficiency ---
        "input_tokens": tu.get("input_tokens"),
        "output_tokens": tu.get("output_tokens"),
        "tokens_total": tu.get("tokens_total"),
        "token_source": tu.get("token_source"),
        "duration_s": _num(metrics.get("duration_s")),
        "self_repair_count": _num(metrics.get("self_repair_count")),

        # --- 6. conversation management ---
        "user_turns": _num(metrics.get("user_turns")),
        "assistant_text_turns": _num(metrics.get("assistant_text_turns")),
        "boundary_setting_count": _num(metrics.get("boundary_setting_count")),
        "user_abandonment_markers": _num(metrics.get("user_abandonment_markers")),
        "n_style_wrappers": _num(metrics.get("n_style_wrappers")),

        # provenance
        "git_commit": meta.get("git_commit"),
        "template_hash": meta.get("template_hash"),
        "controlled_user_hash": meta.get("controlled_user_hash"),
    }
    return row


# Metric dimension map, used by the profile analyzer and the report.
DIMENSIONS: dict[str, list[str]] = {
    "endpoint": ["safe_task_success", "local_proxy_success", "final_state_correct"],
    "tool": ["agent_tool_calls", "unique_tools", "read_calls", "write_calls", "tool_errors", "n_state_mutations"],
    "trajectory": [
        "tool_name_sequence_norm_distance",
        "critical_argument_sequence_norm_distance",
        "mutation_sequence_norm_distance",
    ],
    "policy": ["policy_failure_any", "n_policy_failures", "mutation_before_evidence", "required_fact_coverage"],
    "efficiency": ["tokens_total", "input_tokens", "output_tokens", "agent_tool_calls", "duration_s", "self_repair_count"],
    "conversation": ["boundary_setting_count", "user_abandonment_markers", "assistant_text_turns"],
}
