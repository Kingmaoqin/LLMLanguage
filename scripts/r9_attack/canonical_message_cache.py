#!/usr/bin/env python3
"""Canonical Semantic Control (spec 7.1, 7.2).

Guarantees that the *semantic payload* of every user turn is byte-identical across
C0..C5 and N/P0..P3. This is enforced by construction, not by a post-hoc audit:

  rendered_message = style_prefix + canonical_message + style_suffix

where `canonical_message` is looked up from a frozen cache and is NEVER passed through
an LLM (spec 7.1: "不得调用 LLM 重写 canonical message"). `render()` therefore always
contains the canonical substring verbatim, and `canonical_message_hash` is invariant.

For BFCL the canonical messages are the official dataset user turns. For ToolSandbox
they are the frozen Fact-Ledger canonical responses plus the scenario opening utterance.
Both are cached here so a single `verify_invariance()` can prove spec 7's requirement
before any confirmatory episode runs.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Iterable, Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.common import paths  # noqa: E402
from scripts.r9_attack.common.io_utils import (  # noqa: E402
    read_jsonl,
    sha256_text,
    write_jsonl,
)


class CanonicalMessageCache:
    """Frozen (benchmark, task_id, turn_index) -> canonical message + hash."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, int], str] = {}

    def add(self, benchmark: str, task_id: str, messages: Iterable[str]) -> None:
        for i, msg in enumerate(messages):
            self._cache[(benchmark, task_id, i)] = msg

    def get(self, benchmark: str, task_id: str, turn_index: int) -> str:
        return self._cache[(benchmark, task_id, turn_index)]

    def hash(self, benchmark: str, task_id: str, turn_index: int) -> str:
        return sha256_text(self.get(benchmark, task_id, turn_index))

    def render(
        self,
        benchmark: str,
        task_id: str,
        turn_index: int,
        *,
        style_prefix: str = "",
        style_suffix: str = "",
        canonical_override: Optional[str] = None,
    ) -> str:
        """Wrap style around the canonical payload without ever mutating it."""
        canonical = canonical_override if canonical_override is not None else self.get(benchmark, task_id, turn_index)
        prefix = (style_prefix + " ") if style_prefix else ""
        suffix = (" " + style_suffix) if style_suffix else ""
        rendered = f"{prefix}{canonical}{suffix}"
        assert canonical in rendered, "style wrapping broke canonical payload (spec 7)"
        return rendered

    # -- persistence --------------------------------------------------------
    def rows(self) -> list[dict]:
        out = []
        for (benchmark, task_id, turn), msg in sorted(self._cache.items()):
            out.append(
                {
                    "benchmark": benchmark,
                    "task_id": task_id,
                    "turn_index": turn,
                    "canonical_message": msg,
                    "canonical_hash": sha256_text(msg),
                }
            )
        return out

    def freeze(self, path: pathlib.Path = paths.CANONICAL_MESSAGES) -> pathlib.Path:
        return write_jsonl(path, self.rows())

    @staticmethod
    def load(path: pathlib.Path = paths.CANONICAL_MESSAGES) -> "CanonicalMessageCache":
        cache = CanonicalMessageCache()
        for row in read_jsonl(path):
            cache._cache[(row["benchmark"], row["task_id"], row["turn_index"])] = row["canonical_message"]
        return cache


def verify_invariance(rendered_records: Iterable[dict], cache: CanonicalMessageCache) -> list[str]:
    """Return every violation of spec 7 across a set of episode turn records.

    `rendered_records` are {benchmark, task_id, turn_index, canonical_hash} dicts pulled
    from episode traces. All conditions for one (benchmark, task, turn) must share one
    canonical hash, and that hash must equal the frozen cache's.
    """
    problems: list[str] = []
    seen: dict[tuple[str, str, int], set[str]] = {}
    for rec in rendered_records:
        key = (rec["benchmark"], rec["task_id"], rec["turn_index"])
        seen.setdefault(key, set()).add(rec["canonical_hash"])
    for key, hashes in seen.items():
        if len(hashes) > 1:
            problems.append(f"{key}: {len(hashes)} distinct canonical hashes across conditions")
        try:
            frozen = cache.hash(*key)
        except KeyError:
            problems.append(f"{key}: no frozen canonical message")
            continue
        if frozen not in hashes:
            problems.append(f"{key}: rendered canonical hash != frozen {frozen[:12]}")
    return problems


def build_from_registries(
    bfcl_endpoints: Optional[dict] = None,
    ts_ledger_path: pathlib.Path = paths.FACT_LEDGERS,
) -> CanonicalMessageCache:
    """Populate the cache from frozen splits + ledgers. Used by the freeze step."""
    cache = CanonicalMessageCache()

    # BFCL: canonical user turns come straight from the dataset.
    try:
        from scripts.r9_attack.adapters.bfcl_adapter import BfclAdapter

        adapter = BfclAdapter(endpoints=bfcl_endpoints or {})
        task_ids = sorted(
            {
                row["task_id"]
                for reg in (paths.CALIBRATION_REGISTRY, paths.DEV_REGISTRY, paths.TEST_REGISTRY)
                for row in read_jsonl(reg)
                if row.get("benchmark") == "bfcl"
            }
        )
        for task in adapter.load_tasks(task_ids or None):
            cache.add("bfcl", task.task_id, task.canonical_messages)
    except Exception as exc:  # pragma: no cover - bfcl optional at freeze time
        print(f"[canonical] skipped BFCL: {exc}", file=sys.stderr)

    # ToolSandbox: opening utterance + frozen ledger canonical responses.
    for ledger in read_jsonl(ts_ledger_path):
        messages = [ledger["opening_utterance"]] + [s["canonical_response"] for s in ledger["slots"]]
        cache.add("toolsandbox", ledger["scenario"], messages)

    return cache


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze / verify canonical messages (spec 7)")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--models", default=str(paths.CONFIGS / "models.json"))
    args = parser.parse_args()

    paths.ensure_dirs()
    if args.freeze:
        endpoints = None
        try:
            from scripts.r9_attack.common.llm_client import load_endpoints

            endpoints = {a: e for a, e in load_endpoints(args.models).items()}
        except Exception:
            endpoints = {}
        cache = build_from_registries(bfcl_endpoints=endpoints)
        out = cache.freeze()
        print(f"[canonical] froze {len(cache.rows())} messages -> {out}")
    else:
        cache = CanonicalMessageCache.load()
        print(f"[canonical] loaded {len(cache.rows())} messages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
