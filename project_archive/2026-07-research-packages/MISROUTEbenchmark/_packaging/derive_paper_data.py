#!/usr/bin/env python3
"""INTERNAL build tool (not shipped in the public repo).

Reads the frozen private R8 native traces and derives the MISROUTE public-schema
episode records (data/paper/trajectories/*.jsonl). Only structural fields needed
to reproduce the paper are emitted: ordered tool calls (name + raw arguments +
error flag), official reward, state hashes, condition/model/task labels, and
aggregate (non-text) user-turn statistics. User message *text* is never exported.

Internal condition/model labels are renamed to public semantic IDs.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

# ---------------------------------------------------------------------------
# Deterministic, GLOBAL, equality-preserving pseudonymization of argument
# string values. Argument *keys* (field names) are kept; every distinct string
# VALUE maps to a stable opaque token. Because trajectory distances and mutation
# signatures depend only on whether two argument strings are equal, this removes
# all synthetic-but-identifying content (names, emails, addresses) while leaving
# every reproduced number bit-for-bit unchanged.
# ---------------------------------------------------------------------------
_VALUE_MAP: dict[str, str] = {}
_PSEUDONYMIZE = True


def _tok(value: str) -> str:
    key = "s:" + value
    if key not in _VALUE_MAP:
        _VALUE_MAP[key] = "v_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return _VALUE_MAP[key]


def _clean(obj):
    if not _PSEUDONYMIZE:
        return obj
    if isinstance(obj, str):
        return _tok(obj)
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj  # numbers / bool / None kept verbatim (not identifying)

SRC = pathlib.Path("/home/xqin5/llmlanguage/ir_mstu_stage2/results/r8_full_episode/traces")
OUT = pathlib.Path("/home/xqin5/llmlanguage/MISROUTEbenchmark/misroute-github/data/paper/trajectories")

CONDITION_MAP = {
    "C0": "native_baseline",
    "C1": "matched_neutral",
    "C2": "static_urgency",
    "C3": "adaptive_urgency",
    "C4": "frustration",
}
MODEL_MAP = {
    "gemma4_31b": "model_a",
    "gpt_oss_120b": "model_b",
    "mistral_small_3p2": "model_c",
}
BENCHMARK_VERSION = "1.0.0-paper"


def derive(path: pathlib.Path) -> dict:
    r = json.loads(path.read_text())
    err = {x.get("id") for x in r.get("tool_results", []) if x.get("error")}
    calls = []
    n_user = 0
    user_chars = 0
    for m in r.get("native_messages") or []:
        role = m.get("role")
        if role == "user":
            n_user += 1
            user_chars += len(m.get("content") or "")
        elif role == "assistant":
            for tc in m.get("tool_calls") or []:
                calls.append(
                    {
                        "index": len(calls),
                        "tool_name": tc.get("name") or "",
                        "arguments": _clean(tc.get("arguments") or {}),
                        "error": tc.get("id") in err,
                    }
                )
    domain = r["domain"]
    task_id = f"{domain}:{r['task_id']}"
    condition = CONDITION_MAP[r["condition"]]
    model = MODEL_MAP[r["model"]]
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "episode_id": None,  # filled by schema.finalize (stable hash)
        "task_id": task_id,
        "domain": domain,
        "model_id": model,
        "condition_id": condition,
        "repeat_id": int(r["replicate"]),
        "seed": r.get("seed"),
        "initial_state_hash": r.get("initial_db_hash"),
        "final_state_hash": r.get("final_db_hash"),
        "official_reward": float(r["official_reward"]),
        "termination_reason": str(r.get("termination_reason", "")).replace("TerminationReason.", ""),
        "tool_calls": calls,
        "metadata": {
            "task_family": r.get("task_type"),
            "n_user_messages": n_user,
            "n_user_chars": user_chars,
            "tokens_total": r.get("tokens_total"),
            "duration_seconds": r.get("duration_seconds"),
            "policy_hash": r.get("policy_hash"),
            "tool_schema_hash": r.get("tool_schema_hash"),
            "model_config_hash": r.get("model_config_hash"),
            "user_policy_hash": r.get("user_policy_hash"),
        },
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    by_domain: dict[str, list] = {}
    n = 0
    for p in sorted(SRC.rglob("rep_*.json")):
        if p.name.endswith(".error.json"):
            continue
        rec = derive(p)
        by_domain.setdefault(rec["domain"], []).append(rec)
        n += 1
    for domain, recs in sorted(by_domain.items()):
        recs.sort(key=lambda r: (r["task_id"], r["model_id"], r["condition_id"], r["repeat_id"]))
        fp = OUT / f"{domain}.jsonl"
        with open(fp, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"wrote {len(recs)} -> {fp}")
    print(f"total {n} episodes")


if __name__ == "__main__":
    sys.exit(main())
