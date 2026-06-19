"""Normalized event + metric extraction from a tau2 SimulationRun (plan §19, §30-36).

Per-model tool-call *parsing* is handled at the serving layer (each model is served with its
own vLLM `--tool-call-parser`, see configs/model_config.yaml) and normalized by tau2/LiteLLM
into typed `ToolCall`/`ToolMessage` objects — so a separate per-model parser file would be
redundant (plan §3.1: only wrap what the benchmark lacks). What IR-MSTU still needs, and what
this module provides, is (a) a flat normalized tool-event stream, (b) parser/adapter-failure
accounting kept *separate* from behavioural failure, and (c) the tau2 reward → IR-MSTU metric
mapping.
"""

from __future__ import annotations

from typing import Any

from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage
from tau2.data_model.simulation import SimulationRun

# tau2 state-changing or externally consequential tools across retail+airline.
# The historical constant name is kept because result schemas use
# ``irreversible_action``; its membership is the complete mutation boundary,
# not only cancellations/returns.
IRREVERSIBLE_TOOLS = {
    "book_reservation",
    "cancel_pending_order",
    "cancel_reservation",
    "exchange_delivered_order_items",
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "modify_user_address",
    "return_delivered_order_items",
    "send_certificate",
    "transfer_to_human_agents",
    "update_reservation_baggages",
    "update_reservation_flights",
    "update_reservation_passengers",
}


def _tool_results_by_id(sim: SimulationRun) -> dict[str, ToolMessage]:
    return {m.id: m for m in (sim.messages or []) if isinstance(m, ToolMessage)}


def normalized_tool_events(
    sim: SimulationRun,
    run_meta: dict,
    *,
    records: list[dict] | None = None,
    evidence_tools: set[str] | None = None,
    mutation_tools: set[str] | None = None,
) -> list[dict[str, Any]]:
    """One event per AGENT tool call (plan §19 schema), enriched with per-call state hashes
    (from the ToolEventRecorder, matched in execution order) and policy/branch relevance tags.
    """
    results = _tool_results_by_id(sim)
    evidence_tools = evidence_tools or set()
    mutation_tools = mutation_tools or set()
    events: list[dict[str, Any]] = []
    step = 0
    for msg in sim.messages or []:
        if not (isinstance(msg, AssistantMessage) and msg.tool_calls):
            continue
        for call in msg.tool_calls:
            if call.requestor != "assistant":
                continue
            res = results.get(call.id)
            rec = records[step] if (records and step < len(records)) else {}
            events.append({
                **run_meta,
                "step_index": step,
                "tool_name": call.name,
                "arguments": call.arguments,
                "valid_json": isinstance(call.arguments, dict),  # litellm already parsed args
                "undefined_tool": bool(res and res.error and "unknown" in (res.content or "").lower()),
                "tool_error": bool(res.error) if res else None,
                "tool_result": (res.content if res else None),
                # state (per-call, from get_response wrapper)
                "state_before_hash": rec.get("state_before_hash"),
                "state_after_hash": rec.get("state_after_hash"),
                "mutated": rec.get("mutated"),
                # typing / relevance (plan §30)
                "mutation_type": ("write" if call.name in IRREVERSIBLE_TOOLS else "read"),
                "irreversible_action": call.name in IRREVERSIBLE_TOOLS,
                "policy_relevant": call.name in IRREVERSIBLE_TOOLS,  # writes need confirmation
                "branch_relevant": call.name in (evidence_tools | mutation_tools),
                "turn_idx": msg.turn_idx,
            })
            step += 1
    return events


def _usage_tokens(sim: SimulationRun) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for m in sim.messages or []:
        usage = getattr(m, "usage", None) or {}
        totals["input_tokens"] += int(usage.get("prompt_tokens") or 0)
        totals["output_tokens"] += int(usage.get("completion_tokens") or 0)
        totals["total_tokens"] += int(usage.get("total_tokens") or 0)
    return totals


def parser_health(events: list[dict], sim: SimulationRun) -> dict[str, Any]:
    """Adapter/parser health, kept separate from behaviour (plan §46: never read a parser
    failure as an interactional-robustness effect)."""
    return {
        "n_tool_events": len(events),
        "n_tool_errors": sum(1 for e in events if e["tool_error"]),
        "n_undefined_tools": sum(1 for e in events if e["undefined_tool"]),
        "termination_reason": str(sim.termination_reason),
        # invalid if the model produced no parseable agent tool call at all on a tool task
        "no_tool_call_emitted": len(events) == 0,
    }


def extract_metrics(
    sim: SimulationRun, run_meta: dict, events: list[dict], *, injection_log: list[dict],
    state_before_hash: str | None, state_after_hash: str | None,
) -> dict[str, Any]:
    """Map a SimulationRun to one IR-MSTU metrics row (plan §31-36)."""
    ri = sim.reward_info
    health = parser_health(events, sim)
    tokens = _usage_tokens(sim)

    db_correct = bool(ri.db_check.db_match) if (ri and ri.db_check) else None
    par = ri.partial_action_reward if ri else None
    evidence_read = (par["read"]["proportion"] if par and par.get("read") else None)
    branch_write = (par["write"]["proportion"] if par and par.get("write") else None)
    action_total = (par["total"]["proportion"] if par else None)
    communicate = None
    if ri and ri.communicate_checks:
        communicate = sum(c.met for c in ri.communicate_checks) / len(ri.communicate_checks)

    write_events = [e for e in events if e["irreversible_action"]]
    n_user_turns = sum(1 for m in (sim.messages or []) if getattr(m, "role", None) == "user")

    return {
        **run_meta,
        # primary
        "reward": (ri.reward if ri else None),
        "final_state_correct": db_correct,
        # evidence / branch (plan §32-33)
        "evidence_read_proportion": evidence_read,
        "branch_write_proportion": branch_write,
        "action_total_proportion": action_total,
        "communicate_proportion": communicate,
        # efficiency / trajectory
        "agent_tool_calls": len(events),
        "irreversible_actions": len(write_events),
        "tool_errors": health["n_tool_errors"],
        "user_turns": n_user_turns,
        "duration_s": sim.duration,
        "agent_cost": sim.agent_cost,
        **tokens,
        # state hashes (plan §29-30)
        "state_before_hash": state_before_hash,
        "state_after_hash": state_after_hash,
        "state_mutated": (state_before_hash != state_after_hash),
        # validity vs behaviour (plan §46)
        "termination_reason": health["termination_reason"],
        "invalid_no_tool_call": health["no_tool_call_emitted"],
        # valence audit
        "n_valence_injections": len(injection_log),
    }
