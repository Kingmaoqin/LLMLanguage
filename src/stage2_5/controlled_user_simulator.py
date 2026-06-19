"""Controlled-user validation utilities.

Stage-2.5 keeps tau2's user simulator internal state free of social wrappers.
This module validates the resulting logs: matched condition runs should expose
the same substantive user facts and confirmation decisions as far as can be
checked from raw conversations. A fully scripted user is not invented here.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable


AFFIRM_RE = re.compile(r"\b(yes|yeah|yep|sure|confirm|confirmed|please do|go ahead|proceed)\b", re.I)
NEGATE_RE = re.compile(r"\b(no|don't|do not|stop|cancel that)\b", re.I)
ID_RE = re.compile(r"(#[A-Z]\d+|[A-Z0-9]{6}|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|[a-z]+_[a-z]+_\d+)", re.I)


def strip_known_wrapper(text: str | None, wrapper_texts: Iterable[str]) -> str:
    out = text or ""
    for wrapper in sorted(wrapper_texts, key=len, reverse=True):
        if wrapper and out.startswith(wrapper + " "):
            return out[len(wrapper) + 1 :]
    return out


def user_turn_signature(text: str | None, wrapper_texts: Iterable[str]) -> dict:
    clean = strip_known_wrapper(text, wrapper_texts)
    return {
        "clean_text": clean,
        "ids": sorted(set(ID_RE.findall(clean))),
        "affirm": bool(AFFIRM_RE.search(clean)),
        "negate": bool(NEGATE_RE.search(clean)),
        "word_count": len(clean.split()),
    }


def validate_matched_user_consistency(conversation_rows: list[dict], wrapper_texts: Iterable[str]) -> list[dict]:
    """Compare user signatures within matched model/task/seed/template blocks.

    This is a validation gate, not a way to force consistency. It flags drift
    caused by divergent agent behavior or user simulator non-determinism.
    """
    by_run: dict[str, list[dict]] = defaultdict(list)
    meta: dict[str, dict] = {}
    for row in conversation_rows:
        rid = row["run_id"]
        meta[rid] = row
        if row.get("role") == "user":
            by_run[rid].append(row)

    grouped: dict[tuple, list[str]] = defaultdict(list)
    for rid, row in meta.items():
        key = (row.get("model_alias"), row.get("task_id"), row.get("seed"), row.get("template_block"))
        grouped[key].append(rid)

    out = []
    for key, run_ids in sorted(grouped.items()):
        signatures = {}
        for rid in sorted(set(run_ids)):
            sigs = [user_turn_signature(r.get("content"), wrapper_texts) for r in by_run.get(rid, [])]
            signatures[rid] = sigs
        lengths = {rid: len(sigs) for rid, sigs in signatures.items()}
        id_sets = {rid: sorted({x for sig in sigs for x in sig["ids"]}) for rid, sigs in signatures.items()}
        affirm_seq = {rid: [sig["affirm"] for sig in sigs] for rid, sigs in signatures.items()}
        out.append({
            "model_alias": key[0],
            "task_id": key[1],
            "seed": key[2],
            "template_block": key[3],
            "n_runs": len(signatures),
            "same_user_turn_count": len(set(lengths.values())) <= 1,
            "same_disclosed_ids": len({tuple(v) for v in id_sets.values()}) <= 1,
            "same_confirmation_pattern": len({tuple(v) for v in affirm_seq.values()}) <= 1,
            "turn_counts": lengths,
        })
    return out

