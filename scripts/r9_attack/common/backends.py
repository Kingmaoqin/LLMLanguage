#!/usr/bin/env python3
"""LLM backends for the attacker's generator + the two reviewers (spec 15).

The two reviewers MUST sit on different endpoints from each other (spec 15), and both
must be different from... nothing in particular, but by convention we keep them off the
target model too. These helpers turn an `Endpoint` into the simple `(system, user)->text`
callable the attack layer expects, with tool access hard-disabled (spec 0.2: attacker /
reviewer tool access = none — enforced by never passing `tools`).
"""
from __future__ import annotations

from typing import Callable, Optional

from scripts.r9_attack.common.llm_client import Endpoint, InfraFailure, chat


def make_text_backend(endpoint: Endpoint, *, max_tokens: int = 256, seed: int = 0) -> Callable[[str, str], str]:
    """(_system, user_) -> completion text. No tools, temperature 0 (spec 17)."""

    def backend(system: str, user: str) -> str:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            result = chat(endpoint, messages, tools=None, max_tokens=max_tokens, seed=seed)
        except InfraFailure:
            # A reviewer we cannot reach must fail CLOSED, so return an empty string which
            # the parser turns into "all flags true" -> candidate rejected.
            return ""
        return result.content

    return backend


def wire_attack_backends(
    endpoints: dict[str, Endpoint],
    roles: dict[str, str],
    *,
    seed: int = 0,
) -> dict[str, Optional[Callable[[str, str], str]]]:
    """Build gen + reviewer backends from the roster's role mapping."""
    rev_a = roles.get("reviewer_a")
    rev_b = roles.get("reviewer_b")
    gen = roles.get("attacker")
    if rev_a and rev_b and rev_a == rev_b:
        raise ValueError("reviewer_a and reviewer_b must be different endpoints (spec 15)")
    return {
        "gen_backend": make_text_backend(endpoints[gen], seed=seed) if gen in endpoints else None,
        "reviewer_a": make_text_backend(endpoints[rev_a], seed=seed) if rev_a in endpoints else None,
        "reviewer_b": make_text_backend(endpoints[rev_b], seed=seed) if rev_b in endpoints else None,
    }
