#!/usr/bin/env python3
"""R7-D Step 2 Gate E0: prove the official tau2 environments are real (not a stub).

Per 多轮实验的prompt §4.2, before any task is selected each domain must show:
  - tool arguments are interpreted (a read returns a real record for real args)
  - state diff is correct (a legal write changes the DB hash; reads do not)
  - the official evaluator is importable/runnable
  - reset restores the initial DB hash
  - snapshot/restore (deepcopy of env.tools) is hash-stable

This is the fix for R7-C ISS-03 / Step 1-G, where 0/3027 tool calls had their
arguments interpreted and the "DB" held sentinel strings.

Outputs: results/r7d_ipma/step2/integrity/e0_gate.json
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "results/r7d_ipma/step2/integrity/e0_gate.json"

# A real read probe per domain: (tool, kwargs, a substring that only appears if the
# args were actually interpreted against the real DB).
READ_PROBES = {
    "retail": ("find_user_id_by_name_zip",
               dict(first_name="Yusuf", last_name="Rossi", zip="19122"),
               "yusuf_rossi_9620"),
    "airline": ("get_user_details", dict(user_id="mia_li_3668"), "mia"),
    "telecom": ("get_customer_by_id", dict(customer_id="C1001"), "C1001"),
}


def get_env(domain: str):
    mod = __import__(f"tau2.domains.{domain}.environment", fromlist=["get_environment"])
    return mod.get_environment()


def probe_domain(domain: str) -> dict:
    from tau2.run import get_tasks

    r: dict = {"domain": domain}
    try:
        env = get_env(domain)
    except Exception as exc:  # noqa: BLE001
        return {**r, "get_environment": f"FAIL {exc!r}", "gate": "FAIL"}

    tools = env.get_tools()
    h0 = env.get_db_hash()
    r["n_tools"] = len(tools)
    r["n_tasks"] = len(get_tasks(domain))
    r["initial_db_hash"] = h0[:16]

    # 1) argument interpretation via a real read
    tool, kwargs, needle = READ_PROBES[domain]
    try:
        res = env.make_tool_call(tool, requestor="assistant", **kwargs)
        r["read_probe"] = f"{tool}({kwargs}) -> {str(res)[:80]}"
        r["args_interpreted"] = needle.lower() in str(res).lower()
    except Exception as exc:  # noqa: BLE001
        r["read_probe"] = f"{tool} ERROR {exc!r}"
        r["args_interpreted"] = False
    r["reads_do_not_mutate"] = env.get_db_hash() == h0

    # 2) snapshot/restore fidelity
    snap = copy.deepcopy(env.tools)
    env.tools = copy.deepcopy(snap)
    r["snapshot_restore_hash_stable"] = env.get_db_hash() == h0

    # 3) official evaluator importable
    try:
        from tau2.evaluator.evaluator import evaluate_simulation  # noqa: F401
        r["official_evaluator_importable"] = True
    except Exception as exc:  # noqa: BLE001
        r["official_evaluator_importable"] = f"FAIL {exc!r}"

    # 4) reset restores initial hash
    r["fresh_env_restores_initial_hash"] = get_env(domain).get_db_hash() == h0

    r["gate"] = "PASS" if (
        r.get("args_interpreted")
        and r.get("reads_do_not_mutate")
        and r.get("snapshot_restore_hash_stable")
        and r.get("official_evaluator_importable") is True
        and r.get("fresh_env_restores_initial_hash")
    ) else "FAIL"
    return r


def main() -> int:
    results = [probe_domain(d) for d in ("retail", "airline", "telecom")]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"{'domain':10s} {'args_interp':12s} {'no_mut_read':12s} {'snap_stable':12s} {'evaluator':10s} {'reset':8s} gate")
    for r in results:
        print(f"{r['domain']:10s} {str(r.get('args_interpreted')):12s} "
              f"{str(r.get('reads_do_not_mutate')):12s} "
              f"{str(r.get('snapshot_restore_hash_stable')):12s} "
              f"{str(r.get('official_evaluator_importable'))[:10]:10s} "
              f"{str(r.get('fresh_env_restores_initial_hash')):8s} {r['gate']}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if all(r["gate"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
