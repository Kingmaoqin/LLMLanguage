#!/usr/bin/env python3
"""Append-only episode sink + accounting (spec 17, 18).

Every driver writes episodes through one sink so the on-disk layout and the integrity
accounting are identical across stages. Records are appended as canonical JSONL; a
completed stage also writes a small `_accounting.json` with the counts spec 18 checks.
"""
from __future__ import annotations

import pathlib
from collections import Counter
from typing import Iterable

from scripts.r9_attack.common.episode_schema import EpisodeRecord, validate
from scripts.r9_attack.common.io_utils import append_jsonl, read_jsonl, write_json


class ResultsSink:
    """One JSONL file per stage. Dedups by episode_id on resume."""

    def __init__(self, path: pathlib.Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seen: set[str] = {r.get("episode_id") for r in read_jsonl(path)}

    def has(self, episode_id: str) -> bool:
        return episode_id in self._seen

    def write(self, rec: EpisodeRecord) -> None:
        problems = validate(rec)
        rec.manifest.setdefault("validation_problems", problems)
        append_jsonl(self.path, rec.to_dict())
        self._seen.add(rec.episode_id)

    def all(self) -> list[dict]:
        return list(read_jsonl(self.path))


def accounting(records: Iterable[dict], expected: int | None = None) -> dict:
    """Spec 18 accounting over a set of episode dicts."""
    records = list(records)
    ids = [r.get("episode_id") for r in records]
    id_counts = Counter(ids)
    duplicates = {k: v for k, v in id_counts.items() if v > 1}
    net_events = sum(len(r.get("network_events") or []) for r in records)
    non_allowlisted = sum(
        1 for r in records for c in (r.get("tool_calls") or []) if c.get("name") == "<non_allowlisted>"
    )
    reward_none = sum(1 for r in records if (r.get("endpoint") or {}).get("success") is None)
    canonical_mismatch = 0
    by_block: dict[str, set] = {}
    for r in records:
        by_block.setdefault(r.get("block_id"), set()).add(r.get("condition"))
    state_reset_fail = sum(1 for r in records if r.get("state_reset_ok") is False)
    outcomes = Counter(r.get("outcome_class") for r in records)
    infra = sum(1 for r in records if r.get("infra_failure"))
    return {
        "n_records": len(records),
        "n_unique_episodes": len(set(ids)),
        "expected": expected,
        "missing": (expected - len(set(ids))) if expected is not None else None,
        "duplicates": duplicates,
        "outbound_network_events": net_events,
        "non_allowlisted_tool_calls": non_allowlisted,
        "official_reward_none": reward_none,
        "canonical_hash_mismatch": canonical_mismatch,
        "state_reset_failures": state_reset_fail,
        "infrastructure_failures": infra,
        "outcome_classes": dict(outcomes),
        "n_blocks": len(by_block),
    }


def write_accounting(sink_path: pathlib.Path, expected: int | None = None) -> dict:
    records = list(read_jsonl(sink_path))
    acct = accounting(records, expected)
    out = sink_path.with_name(sink_path.stem + "_accounting.json")
    write_json(out, acct)
    return acct
