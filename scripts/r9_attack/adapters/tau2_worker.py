#!/usr/bin/env python3
"""R9v2 tau2-bench worker (runs in the tau2 venv: /home/xqin5/tau2_venv).

Subprocess-isolated, one process per job, mirroring `toolsandbox_worker.py`. Communicates
with the r9_bfcl-side `tau2_adapter.py` via a JSON job on argv and JSON events on stdout.

Commands:
  list-tasks   : per-domain task profiles (facts ledger + native read/write reference
                 trajectory from evaluation_criteria.actions + reward_basis). No server.
  run-episode  : run one scored episode via tau2's native LLMAgent (pointed at a local vLLM
                 OpenAI endpoint) + a ScriptedLedgerUser (frozen known_info facts for semantic
                 invariance) wrapped by the R9 attacker; capture tool calls (classified
                 read/write by native ToolType), native reward, and the process metrics.

Read/write classification is tau2-NATIVE (@is_tool(ToolType.WRITE/READ)); never a hand table.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

os.environ.setdefault("TAU2_DATA_DIR", "/home/xqin5/tau2-bench/data")

# tau2's registry prints an info blob to stdout on import; redirect all tau2 stdout noise to
# stderr and reserve the REAL stdout for our JSON protocol only.
_REAL_STDOUT = sys.stdout
sys.stdout = sys.stderr

_ENVCACHE: dict[str, Any] = {}


def _emit(payload: dict[str, Any]) -> None:
    _REAL_STDOUT.write(json.dumps(payload) + "\n")
    _REAL_STDOUT.flush()


def _log(msg: str) -> None:
    sys.stderr.write(f"[tau2_worker] {msg}\n")
    sys.stderr.flush()


def _env(domain: str):
    """Cached tau2 environment + toolkit for a domain."""
    if domain not in _ENVCACHE:
        from tau2.registry import registry
        _ENVCACHE[domain] = registry.get_env_constructor(domain)()
    return _ENVCACHE[domain]


def _tool_types(domain: str) -> dict[str, str]:
    env = _env(domain)
    tk = env.tools
    names = [t.name for t in env.get_tools()]
    out = {}
    for n in names:
        try:
            out[n] = str(tk.tool_type(n)).split(".")[-1]  # READ / WRITE / GENERIC
        except Exception:
            out[n] = "GENERIC"
    return out


def _tasks(domain: str) -> list:
    from tau2.registry import registry
    return registry.get_tasks_loader(domain)()


# --------------------------------------------------------------------------- profiles
def task_profile(domain: str, task: Any, tool_types: dict[str, str]) -> dict[str, Any]:
    """Reference profile: native read/write reference trajectory + facts ledger.

    - reference actions come from `evaluation_criteria.actions` (tau2's own reference), each
      classified read/write by native ToolType.
    - min_prereq_verification_calls = reads BEFORE the first write action (compression floor).
    - min_viable_total_verification_calls = total reads over the reference (inflation floor).
    - the facts ledger = structured `known_info` the user holds + reason_for_call (for the
      ScriptedLedgerUser to deliver deterministically -> semantic invariance).
    """
    us = task.user_scenario
    instr = us.instructions
    ec = task.evaluation_criteria

    actions = list(ec.actions or []) if ec else []
    reads_before_first_write = 0
    total_reads = 0
    seen_write = False
    mutating: list[str] = []
    read_names: list[str] = []
    flat: list[str] = []
    for a in actions:
        name = a.name
        flat.append(name)
        tt = tool_types.get(name, "GENERIC")
        if tt == "WRITE":
            seen_write = True
            if name not in mutating:
                mutating.append(name)
        elif tt == "READ":
            total_reads += 1
            if not seen_write:
                reads_before_first_write += 1
            if name not in read_names:
                read_names.append(name)

    known = getattr(instr, "known_info", None) or ""
    return {
        "task_id": str(task.id),
        "domain": domain,
        "reason_for_call": getattr(instr, "reason_for_call", "") or "",
        "known_info": known,
        "task_instructions": getattr(instr, "task_instructions", "") or "",
        "reward_basis": [str(r).split(".")[-1] for r in (ec.reward_basis or [])] if ec else [],
        "gt_path": flat,
        "mutating_tools": mutating,
        "read_tools": read_names,
        "has_mutation": bool(mutating),
        "n_reference_actions": len(actions),
        "n_distinct_tools": len(set(flat)),
        "min_prereq_verification_calls": max(1, reads_before_first_write),
        "min_viable_total_verification_calls": max(1, total_reads),
        # depth proxy: tau2 turns emerge at run time; use reference-action count as a floor.
        "n_reference_read_write": total_reads + len(mutating),
    }


def cmd_list_tasks(job: dict) -> dict[str, Any]:
    domains = job.get("domains") or ["airline", "retail"]
    out = []
    for domain in domains:
        tt = _tool_types(domain)
        for task in _tasks(domain):
            out.append(task_profile(domain, task, tt))
    return {"event": "done", "tasks": out, "n": len(out)}


# --------------------------------------------------------------------------- dispatch
def main() -> int:
    if len(sys.argv) < 2:
        _emit({"event": "error", "error": "usage: tau2_worker.py '<json-job>'"})
        return 2
    try:
        job = json.loads(sys.argv[1])
    except Exception as exc:
        _emit({"event": "error", "error": f"bad job json: {exc}"})
        return 2

    cmd = job.get("cmd")
    try:
        if cmd == "list-tasks":
            _emit(cmd_list_tasks(job))
        elif cmd == "run-episode":
            from tau2_episode import run_episode  # lazy: heavy imports only when scoring
            _emit(run_episode(job))
        else:
            _emit({"event": "error", "error": f"unknown cmd {cmd!r}"})
            return 2
    except Exception as exc:
        import traceback
        _emit({"event": "error", "error": str(exc), "trace": traceback.format_exc()[-1500:]})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
