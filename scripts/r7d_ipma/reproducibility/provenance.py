#!/usr/bin/env python3
"""Append-only provenance and deterministic recorded-trace replay primitives."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from .ordered_trajectory_evaluator import canonical_json, digest, extract_actions


STATES = ("PREPARED", "COMMITTED", "CAPTURED", "TERMINAL")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class AppendOnlyJournal:
    """One JSON record per state, exclusive-create, fsync, never overwrite."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=False, exist_ok=False)

    def append(self, state: str, payload: dict[str, Any]) -> Path:
        if state not in STATES:
            raise ValueError("invalid_provenance_state")
        index = STATES.index(state)
        if index and not (self.root / f"{index - 1:02d}_{STATES[index - 1]}.json").exists():
            raise RuntimeError("provenance_state_out_of_order")
        path = self.root / f"{index:02d}_{state}.json"
        body = canonical_json({"state": state, "payload": payload}) + "\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        try:
            os.write(fd, body.encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        return path


def replay_recorded_trace(trace: dict[str, Any], *, mutation_tools: set[str],
                          scorer: Callable[[dict[str, Any]], Any],
                          db_replayer: Callable[[dict[str, Any]], str],
                          token_counter: Callable[[str], int]) -> dict[str, Any]:
    """Pure replay: no model call and no rewriting of the supplied trace."""
    actions = extract_actions(trace, mutation_tools)
    rendered_input = trace.get("rendered_input")
    if not isinstance(rendered_input, str):
        raise ValueError("missing_rendered_input")
    token_fields = trace.get("token_texts")
    if not isinstance(token_fields, dict) or not all(isinstance(v, str) for v in token_fields.values()):
        raise ValueError("incomplete_token_texts")
    return {
        "rendered_input_hash": hashlib.sha256(rendered_input.encode()).hexdigest(),
        "official_scorer_result": scorer(trace),
        "final_db_state_hash": db_replayer(trace),
        "ordered_action_digest": digest([action.semantic() for action in actions]),
        "ordered_tool_names": [action.name for action in actions],
        "mutating_flags": [action.mutating for action in actions],
        "token_counts": {key: token_counter(value) for key, value in sorted(token_fields.items())},
        "trace_digest": digest(trace),
    }


def verify_two_replays(trace: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    first = replay_recorded_trace(trace, **kwargs)
    second = replay_recorded_trace(trace, **kwargs)
    return {"first": first, "second": second, "identical": first == second,
            "replay_digest": digest(first)}

