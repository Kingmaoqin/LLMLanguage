#!/usr/bin/env python3
"""R8-B correction item 4: disk-backed turn-0 canonical-payload cache.

R8-A regenerated the turn-0 payload per condition (temp-0 mistral under concurrent
vLLM) and got only 87.8% byte-identical C1/C3/C4 openings. R8-B REQUIRES 100%: the
turn-0 canonical semantic payload is generated ONCE per (domain, task_id, replicate)
and cached to disk; every condition/arm reads the SAME string, and style is wrapped
outside it. Turn 0 answers the FIXED greeting, so it is condition-independent by
construction; caching removes the residual LLM-nondeterminism gap.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import threading

CACHE_DIR = pathlib.Path(__file__).resolve().parents[2] / "data/r8b_attack/payload_cache"
_LOCK = threading.Lock()


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _path(domain: str, task_id: str, replicate: int) -> pathlib.Path:
    return CACHE_DIR / f"{domain}_{task_id}_rep{replicate}.json"


def get_or_make_turn0(domain: str, task_id: str, replicate: int, make_fn):
    """Return the cached turn-0 payload text, generating+persisting it once.

    make_fn() -> str is called only on a cache miss (must be deterministic-ish; we
    freeze whatever it returns the first time so all conditions share it verbatim)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = _path(domain, task_id, replicate)
    if p.exists():
        return json.loads(p.read_text())["payload"]
    with _LOCK:
        if p.exists():  # double-checked after acquiring lock
            return json.loads(p.read_text())["payload"]
        payload = make_fn()
        p.write_text(json.dumps({"domain": domain, "task_id": task_id, "replicate": replicate,
                                 "payload": payload, "payload_hash": _sha(payload)}, ensure_ascii=False))
        return payload


def cached_hash(domain: str, task_id: str, replicate: int):
    p = _path(domain, task_id, replicate)
    return json.loads(p.read_text())["payload_hash"] if p.exists() else None
