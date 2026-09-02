#!/usr/bin/env python3
"""R9 benchmark adapter contract (spec 3, 11.1).

An adapter owns exactly three responsibilities and nothing else:

  * expose the benchmark's OWN tasks with their OWN canonical user messages (spec 7),
  * roll one episode out against a local model, letting a `UserHook` decide the
    *rendered* text of every user turn while the canonical payload stays verbatim,
  * score the finished rollout with the benchmark's OWN native evaluator (spec 11.1).

Adapters never compute process metrics and never decide success themselves; that keeps
the native evaluator authoritative and keeps `extract_metrics` / `reference_metrics`
able to recompute everything from the stored trace.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from scripts.r9_attack.common.episode_schema import EpisodeRecord, InterventionRecord


@dataclass
class TaskSpec:
    """One frozen benchmark task, benchmark-agnostic."""

    benchmark: str
    task_id: str
    n_user_turns: int
    canonical_messages: list[str] = field(default_factory=list)
    canonical_hashes: list[str] = field(default_factory=list)
    n_distinct_tools: int = 0
    n_reference_actions: int = 0
    min_prereq_verification_calls: int = 1
    min_viable_total_verification_calls: int = 1
    gt_path: list[str] = field(default_factory=list)
    n_milestones: int = 0
    categories: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def complexity_ok(self) -> bool:
        """Spec 6.2 calibration complexity floor (benchmark-aware).

        Spec 6.2 asks for >=2 user turns, >=4 tool/function actions, >=2 distinct tools,
        and for ToolSandbox >=2 milestones. ToolSandbox's `n_reference_actions` counts the
        milestone-referenced tools (typically 2-3), so for ToolSandbox the milestone count
        is the intended complexity signal, not the >=4 action count meant for BFCL.
        """
        if self.benchmark == "toolsandbox":
            return self.n_milestones >= 2 and self.n_distinct_tools >= 1
        return (
            self.n_user_turns >= 2
            and self.n_reference_actions >= 4
            and self.n_distinct_tools >= 2
        )


class UserHook(Protocol):
    """Decides what the user actually says at one turn.

    Receives the canonical payload plus the PUBLIC transcript only (spec 2: the attacker
    may not read hidden reasoning, hidden tool results, the DB or the evaluator) and
    returns the rendered message together with the intervention it applied.
    """

    def __call__(
        self,
        *,
        turn_index: int,
        canonical_message: str,
        public_transcript: list[dict[str, str]],
        slot: Optional[str] = None,
    ) -> tuple[str, InterventionRecord]: ...


def neutral_hook(
    *,
    turn_index: int,
    canonical_message: str,
    public_transcript: list[dict[str, str]],
    slot: Optional[str] = None,
) -> tuple[str, InterventionRecord]:
    """C0: the native benchmark message, untouched."""
    return canonical_message, InterventionRecord(
        turn=turn_index, family="none", tactic="native_neutral", non_neutral=False
    )


class BenchmarkAdapter(Protocol):
    name: str

    def load_tasks(self, task_ids: Optional[list[str]] = None) -> list[TaskSpec]: ...

    def run_episode(
        self,
        task: TaskSpec,
        *,
        model_alias: str,
        condition: str,
        repeat: int,
        stage: str,
        user_hook: Callable[..., tuple[str, InterventionRecord]],
        seed: int = 0,
    ) -> EpisodeRecord: ...

    def manifest(self) -> dict[str, Any]: ...
