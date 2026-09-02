#!/usr/bin/env python3
"""Targeted selector (spec 8.2 P3, 8.6).

Given the candidates that SURVIVED the dual-independent constraint filter, pick the one
most likely to push the frozen family objective. Selection uses ONLY the public
transcript, the candidate text, the frozen objective, and dev-learned priors (spec 6/8).
It never sees hidden reasoning, tool logs, the DB, the evaluator, or the outcome.

`priors` is the frozen per-(family, tactic_id) score learned on the DEV split by
maximising the dev objective J (spec 8.6). At confirmatory time the priors are read-only.
Ties break deterministically by candidate hash so the policy is reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from scripts.r9_attack.candidate_generator import InteractionState
from scripts.r9_attack.constraint_filter import Candidate


@dataclass
class SelectorPriors:
    """Frozen dev-learned tactic priors (spec 8.6)."""

    family: str
    tactic_scores: dict[str, float] = field(default_factory=dict)
    trigger_bonus: dict[str, float] = field(default_factory=dict)
    default_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "tactic_scores": self.tactic_scores,
            "trigger_bonus": self.trigger_bonus,
            "default_score": self.default_score,
        }

    @staticmethod
    def from_dict(d: dict) -> "SelectorPriors":
        return SelectorPriors(
            family=d["family"],
            tactic_scores=dict(d.get("tactic_scores", {})),
            trigger_bonus=dict(d.get("trigger_bonus", {})),
            default_score=float(d.get("default_score", 0.0)),
        )


def score_candidate(candidate: Candidate, state: InteractionState, priors: Optional[SelectorPriors]) -> float:
    """Higher == more likely to move the frozen objective. Public info + priors only."""
    if priors is None:
        # Uninformed selector (used before dev freezing): prefer the state-matched
        # trigger, then shorter additions (less likely to perturb semantics).
        base = 1.0 if candidate.trigger == state.trigger() else 0.0
        return base - 0.001 * candidate.token_count
    score = priors.tactic_scores.get(candidate.tactic_id, priors.default_score)
    score += priors.trigger_bonus.get(candidate.trigger, 0.0)
    if candidate.trigger == state.trigger():
        score += 0.05  # small, fixed alignment bonus; priors dominate
    return score


def select(
    candidates: list[Candidate],
    state: InteractionState,
    priors: Optional[SelectorPriors] = None,
) -> Optional[tuple[Candidate, float]]:
    """Pick the best surviving candidate, or None if the set is empty (-> neutral)."""
    if not candidates:
        return None
    scored = [(score_candidate(c, state, priors), c) for c in candidates]
    # Deterministic tie-break: score desc, then candidate hash asc.
    scored.sort(key=lambda sc: (-sc[0], sc[1].candidate_hash))
    best_score, best = scored[0]
    return best, best_score
