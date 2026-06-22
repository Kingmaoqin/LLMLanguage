"""Branch-decision adjudication for IR-MSTU Stage-2 (plan §33).

Turns a run's ordered tool events + the task's forced-replanning-points into one
branch_decision per (run, branch), classified as:

    not_reached       - the agent never reached the branch's trigger (abandoned / failed early)
    premature_action  - an irreversible mutation happened before the required evidence was
                        complete (acted before gathering the facts the branch depends on)
    correct_revision  - branch reached, evidence-first, and the gated write matched gold
    missed_revision   - branch reached, evidence-first, but the gated write did not match gold
    reached_unscored  - branch reached and evidence-first, but no gold write maps to it

This is a deterministic, rule-based first pass driven entirely by observed tool order and tau2's
own per-action gold match. It uses an explicit per-branch `trigger_tool` (the read whose result
forces the replanning) and `gated_writes` (the mutation(s) the branch decides) when the spec
provides them, falling back to task-level evidence/mutation sets otherwise. Subtler "did the
agent revise *for the right reason*" judgements are left to an optional LLM-judge pass, not
claimed here.
"""

from __future__ import annotations

from typing import Any, Optional


def write_match_by_tool(reward_info: Any) -> dict[str, float]:
    """Per write-tool gold-match proportion from tau2 action_checks (ToolType.WRITE)."""
    out: dict[str, list[float]] = {}
    for ac in (getattr(reward_info, "action_checks", None) or []):
        if getattr(ac, "tool_type", None) is not None and str(ac.tool_type).endswith("WRITE"):
            out.setdefault(ac.action.name, []).append(1.0 if ac.action_match else 0.0)
    return {name: sum(v) / len(v) for name, v in out.items()}


def adjudicate_branches(
    events: list[dict],
    branches: list[dict],
    *,
    required_evidence: set[str],
    write_matches: dict[str, float],
) -> list[dict[str, Any]]:
    """Classify each forced-replanning-point for one run."""
    called = [e["tool_name"] for e in events]
    first_mut_step = next((e["step_index"] for e in events if e.get("mutation_type") == "write"), None)
    evidence_before_mut = {
        e["tool_name"] for e in events
        if e["tool_name"] in required_evidence and (first_mut_step is None or e["step_index"] < first_mut_step)
    }
    evidence_complete = bool(required_evidence) and required_evidence.issubset(evidence_before_mut)

    decisions = []
    for b in branches:
        trigger: Optional[str] = b.get("trigger_tool")
        reached = (trigger in called) if trigger else (first_mut_step is not None or bool(evidence_before_mut))
        if not reached:
            cls = "not_reached"
        elif first_mut_step is not None and required_evidence and not evidence_complete:
            cls = "premature_action"
        else:
            gated = b.get("gated_writes") or []
            ms = [write_matches[w] for w in gated if w in write_matches]
            if not ms:
                cls = "reached_unscored"
            else:
                cls = "correct_revision" if (sum(ms) / len(ms)) >= 0.5 else "missed_revision"
        decisions.append({"branch_id": b["branch_id"], "trigger_tool": trigger,
                          "reached": reached, "classification": cls})
    return decisions
