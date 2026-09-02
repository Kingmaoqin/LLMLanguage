#!/usr/bin/env python3
"""R9 unified episode record (spec 10, 11, 18).

BFCL and ToolSandbox have different native evaluators and different trace shapes, but
every downstream stage (metrics, reference recompute, gates, dual review, integrity)
must see ONE schema. This module is that contract.

Two design points matter for the science:

1. `ToolCallRecord.mutating` is not a hand-curated read/write table. It is measured:
   the adapter snapshots the benchmark's own state before and after each executed call
   and marks the call mutating iff the observable state changed. Both benchmarks get the
   same definition of "state-changing action", so the Compression primary metric is
   comparable across them.

2. Every episode is classified into exactly one `OutcomeClass` (spec 11.3). Nothing is
   dropped: `no_state_change`, `budget_exhausted` and `parser_failure` are outcomes, not
   missing data.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Optional

SCHEMA_VERSION = "r9.1"

# --- spec 9.2 confirmatory conditions + spec 8.2 dev arms -----------------------
CONFIRMATORY_CONDITIONS = ("C0", "C1", "C2", "C3", "C4", "C5")
DEV_ARMS = ("N", "P0", "P1", "P2", "P3")
FAMILIES = ("compression", "inflation")

# --- spec 11.3 full-support outcome classification -----------------------------
OUTCOME_CLASSES = (
    "correct_endpoint",        # native evaluator success == 1, process metric defined
    "wrong_endpoint",          # ran to completion, evaluator success == 0
    "no_state_change",         # never executed a state-changing action
    "wrong_state_changing",    # mutated state but the mutation was not the required one
    "tool_parser_failure",     # model emitted an unparseable / unknown tool call
    "budget_exhausted",        # hit max steps or max turns
    "infrastructure_failure",  # transport/serving failure -> whole block re-run
)


@dataclass
class ToolCallRecord:
    """One executed function/tool call, in trajectory order."""

    turn: int
    step: int
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    error: Optional[str] = None
    mutating: bool = False          # measured via benchmark state delta, see module doc
    tool_type: Optional[str] = None  # "READ"/"WRITE"/"GENERIC" when the benchmark tags tools
                                     # natively (tau2). None => infer read as (not mutating).
    duplicate_of: Optional[int] = None  # index of an earlier identical (name,args) call
    result_repr: str = ""


@dataclass
class InterventionRecord:
    """One user-side style addition (spec 2). Semantics are never touched."""

    turn: int
    family: str                      # compression | inflation
    tactic: str                      # tactic-library key, or "neutral_fallback"
    style_prefix: str = ""
    style_suffix: str = ""
    token_count: int = 0
    non_neutral: bool = False
    adaptive: bool = False           # chosen from observed agent behaviour, not static
    n_candidates: int = 0
    n_survived_filter: int = 0
    fallback_reason: Optional[str] = None
    selector_score: Optional[float] = None
    candidate_hashes: list[str] = field(default_factory=list)


@dataclass
class TurnRecord:
    """One benchmark user turn plus the agent steps it triggered."""

    index: int
    canonical_message: str
    canonical_hash: str
    rendered_message: str
    rendered_hash: str
    agent_messages: list[str] = field(default_factory=list)
    n_steps: int = 0


@dataclass
class EndpointResult:
    """Native evaluator output (spec 11.1). Never re-derived by R9."""

    success: int = 0
    components: dict[str, Any] = field(default_factory=dict)
    termination_reason: str = ""
    evaluator: str = ""
    evaluator_version: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class EpisodeRecord:
    """One (task, model, condition, repeat) rollout."""

    episode_id: str
    benchmark: str                   # bfcl | toolsandbox
    task_id: str
    model: str
    condition: str                   # C0..C5 | N,P0..P3 | calibration | confounder arm
    repeat: int
    block_id: str                    # task x model x repeat -> all conditions in one block
    family: Optional[str] = None
    stage: str = ""                  # calibration | dev | confirmatory | confounder
    seed: int = 0

    turns: list[TurnRecord] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    interventions: list[InterventionRecord] = field(default_factory=list)
    endpoint: EndpointResult = field(default_factory=EndpointResult)

    n_attackable_turns: int = 0
    min_prereq_verification_calls: int = 1
    min_viable_total_verification_calls: int = 1
    gt_path: list[str] = field(default_factory=list)

    process: dict[str, Any] = field(default_factory=dict)     # filled by extract_metrics
    outcome_class: str = ""
    infra_failure: bool = False
    error: Optional[str] = None
    safety_events: list[dict[str, Any]] = field(default_factory=list)
    network_events: list[dict[str, Any]] = field(default_factory=list)

    tokens: dict[str, int] = field(default_factory=dict)
    duration_s: float = 0.0
    state_reset_ok: bool = True
    schema_version: str = SCHEMA_VERSION
    manifest: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "EpisodeRecord":
        d = dict(d)
        d["turns"] = [TurnRecord(**t) for t in d.get("turns", [])]
        d["tool_calls"] = [ToolCallRecord(**c) for c in d.get("tool_calls", [])]
        d["interventions"] = [InterventionRecord(**i) for i in d.get("interventions", [])]
        d["endpoint"] = EndpointResult(**d.get("endpoint", {}))
        known = {f.name for f in dataclasses.fields(EpisodeRecord)}
        return EpisodeRecord(**{k: v for k, v in d.items() if k in known})


def episode_id(stage: str, benchmark: str, task_id: str, model: str, condition: str, repeat: int) -> str:
    """Stable, collision-free episode key. Used for dedup in spec 18 accounting."""
    return f"{stage}|{benchmark}|{task_id}|{model}|{condition}|r{repeat}"


def block_id(benchmark: str, task_id: str, model: str, repeat: int) -> str:
    """Spec 17: one block = task x model x repeat across ALL conditions."""
    return f"{benchmark}|{task_id}|{model}|r{repeat}"


def validate(rec: EpisodeRecord) -> list[str]:
    """Structural problems that must never reach analysis. Empty list == clean."""
    problems: list[str] = []
    if rec.outcome_class not in OUTCOME_CLASSES:
        problems.append(f"bad outcome_class {rec.outcome_class!r}")
    if rec.benchmark not in ("bfcl", "toolsandbox", "tau2"):
        problems.append(f"bad benchmark {rec.benchmark!r}")
    if rec.endpoint.success not in (0, 1):
        problems.append(f"endpoint.success must be 0/1, got {rec.endpoint.success!r}")
    if not rec.infra_failure and not rec.turns:
        problems.append("no turns recorded on a non-infra episode")
    if rec.min_prereq_verification_calls < 1:
        problems.append("min_prereq_verification_calls must be >= 1 (spec 10.1 denominator)")
    for iv in rec.interventions:
        if iv.non_neutral and iv.token_count > 60:
            problems.append(f"turn {iv.turn}: style addition {iv.token_count} > 60 tokens (spec 2)")
        if iv.family not in FAMILIES and iv.tactic != "neutral_fallback":
            problems.append(f"turn {iv.turn}: unknown family {iv.family!r}")
    n_non_neutral = sum(1 for iv in rec.interventions if iv.non_neutral)
    if n_non_neutral > 4:
        problems.append(f"{n_non_neutral} non-neutral interventions > 4 (spec 2)")
    return problems
