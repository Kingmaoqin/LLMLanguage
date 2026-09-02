"""Minimal runtime ProcessGuard implementation for R7-B."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


PRESSURE_RE = re.compile(
    r"\b(urgent|time-sensitive|frustrating|frustrated|smooth|efficient|still here|standard process|same process)\b",
    re.I,
)


class PressureStripper:
    def strip(self, surface_text: str, clean_task_semantics: str) -> dict[str, Any]:
        return {
            "clean_task_semantics": clean_task_semantics,
            "pressure_removed": surface_text != clean_task_semantics and bool(PRESSURE_RE.search(surface_text)),
        }


class PolicyInvariantPlanner:
    def plan(self, task_policy: dict[str, Any], clean_task_semantics: str) -> dict[str, Any]:
        return {
            "requires_confirmation": bool(task_policy.get("requires_confirmation")),
            "allowed_mutation_tools": list(task_policy.get("allowed_mutation_tools") or []),
            "forbidden_mutation_tools": list(task_policy.get("forbidden_mutation_tools") or []),
            "basis": "policy_only_not_pressure",
        }


@dataclass
class EvidenceLedger:
    available_fields: set[str] = field(default_factory=set)

    def record(self, fields: list[str]) -> None:
        self.available_fields.update(fields)

    def has_required(self, required: list[str]) -> bool:
        return set(required).issubset(self.available_fields)


class MutationGate:
    def allow(self, *, tool_name: str, plan: dict[str, Any], confirmation_available: bool, evidence_ok: bool) -> tuple[bool, str]:
        if tool_name in set(plan.get("forbidden_mutation_tools") or []):
            return False, "forbidden_mutation_tool"
        if plan.get("requires_confirmation") and not confirmation_available:
            return False, "missing_confirmation"
        if not evidence_ok:
            return False, "missing_required_evidence"
        return True, "allowed"


@dataclass
class TrajectoryBudgetMonitor:
    max_tool_calls: int = 12
    max_repeated_same_tool: int = 3
    seen: list[str] = field(default_factory=list)

    def record_or_block(self, tool_name: str) -> tuple[bool, str]:
        if len(self.seen) >= self.max_tool_calls:
            return False, "trajectory_budget_exceeded"
        if self.seen.count(tool_name) >= self.max_repeated_same_tool:
            return False, "repeated_tool_budget_exceeded"
        self.seen.append(tool_name)
        return True, "within_budget"


class BoundaryContinuationRule:
    def decide(self, *, boundary_detected: bool, allowed_safe_subtask_exists: bool) -> str:
        if boundary_detected and allowed_safe_subtask_exists:
            return "refuse_disallowed_part_continue_allowed_subtask"
        if boundary_detected:
            return "safe_refusal"
        return "continue_normal_task"


@dataclass
class ProcessGuard:
    pressure: PressureStripper = field(default_factory=PressureStripper)
    planner: PolicyInvariantPlanner = field(default_factory=PolicyInvariantPlanner)
    ledger: EvidenceLedger = field(default_factory=EvidenceLedger)
    budget: TrajectoryBudgetMonitor = field(default_factory=TrajectoryBudgetMonitor)
    gate: MutationGate = field(default_factory=MutationGate)
    boundary: BoundaryContinuationRule = field(default_factory=BoundaryContinuationRule)

