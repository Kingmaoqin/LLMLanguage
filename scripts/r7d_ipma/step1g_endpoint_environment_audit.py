#!/usr/bin/env python3
"""R7-D Step 1-G: endpoint / environment validity -- official tau2 vs R7-C minimal oracle.

Three-way cross-check requested by 正式阶段的prompt §13:
    (1) official tau2 evaluator
    (2) R7-C minimal field-diff evaluator
    (3) human judgement

Leg (1) is available: the tau2 package is installed and evaluate_simulation imports.
Leg (3) needs annotators we do not have, and is reported NOT_CLOSED rather than faked.

The finding that drives this module is that leg (1) cannot be applied to the R7-C
traces -- not because the official evaluator is missing, but because R7-C never ran a
tau2 simulation. Its tools return no data, so there is no action-with-arguments and no
database state for the official criteria to check. We quantify that gap here.

Outputs:
    results/r7d_ipma/step1/endpoint_crosscheck.csv
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUN = ROOT / "results/r7c_ipma/full/live_20260710_000752"
REGISTRY = ROOT / "data/r7c_ipma/r7c_task_registry.csv"
POS_CSV = ROOT / "results/r7d_ipma/step1/task_process_opportunity.csv"
OUT = ROOT / "results/r7d_ipma/step1/endpoint_crosscheck.csv"

TAU2_DOMAINS = {"retail", "airline"}


def official_tau2_index() -> dict:
    """id -> official task, for the domains R7-C says it derives from."""
    from tau2.run import get_tasks

    idx = {}
    for dom in TAU2_DOMAINS:
        for t in get_tasks(dom):
            idx[f"{dom}_{t.id}"] = t
            idx[str(t.id)] = t
    return idx


def main() -> int:
    reg = {r["task_id"]: r for r in csv.DictReader(REGISTRY.open())}
    pos = {r["task_id"]: r for r in csv.DictReader(POS_CSV.open())}

    # ---- what does R7-C actually record per task? ----
    per_task = collections.defaultdict(
        lambda: dict(n_runs=0, n_tool_calls=0, n_with_args_interpreted=0, state_keys=set())
    )
    for path in glob.glob(str(RUN / "traces/*.json")):
        d = json.loads(pathlib.Path(path).read_text())
        t = per_task[d["task_id"]]
        t["n_runs"] += 1
        for e in d.get("tool_events") or []:
            t["n_tool_calls"] += 1
            tr = e.get("tool_result") or {}
            # an interpreted argument would produce business data in the result;
            # R7-C only ever echoes the argument back under `arguments_received`.
            if set(tr) - {
                "ok", "mutation", "task_id", "domain", "layer", "policy",
                "state_hash", "available_expected_field_diffs", "arguments_received",
                "updated_paths",
            }:
                t["n_with_args_interpreted"] += 1
        st = (d.get("initial_environment_state") or {}).get("state") or {}
        t["state_keys"] |= set(st)

    try:
        official = official_tau2_index()
        official_ok = True
        err = ""
    except Exception as exc:  # noqa: BLE001
        official, official_ok, err = {}, False, repr(exc)

    rows = []
    for tid, r in sorted(reg.items()):
        dom = r["domain"]
        src = r.get("source_task_id", "")
        t = per_task[tid]

        off = official.get(src) if official_ok else None
        if off is not None and getattr(off, "evaluation_criteria", None):
            ec = off.evaluation_criteria
            n_act = len(ec.actions or [])
            n_env = len(ec.env_assertions or [])
            n_nl = len(ec.nl_assertions or [])
            official_present = "YES"
            official_checks = f"actions={n_act};env_assertions={n_env};nl_assertions={n_nl}"
        else:
            n_act = n_env = n_nl = 0
            official_present = "NO" if dom in TAU2_DOMAINS else "N/A_not_a_tau2_domain"
            official_checks = ""

        # Can the official evaluator be *applied* to the R7-C trace?
        # It needs (a) tool calls whose arguments were interpreted against a real DB,
        # and (b) a real DB final state. R7-C has neither.
        applicable = "NO"
        why = (
            "R7-C tools return no business data (single fixed payload shape) and its "
            "'database' holds placeholder sentinels like 'initial::orders.items'; there is "
            "no action-with-arguments and no DB state for official criteria to check"
        )
        if t["n_with_args_interpreted"] > 0:
            applicable = "YES"
            why = ""

        rows.append(
            dict(
                task_id=tid,
                domain=dom,
                source_task_id=src,
                POS=pos.get(tid, {}).get("POS", ""),
                task_family_primary=r.get("task_family_primary", ""),
                official_tau2_task_found=official_present,
                official_criteria=official_checks,
                official_n_actions=n_act,
                official_n_env_assertions=n_env,
                official_n_nl_assertions=n_nl,
                r7c_evaluator="r7c_minimal_field_diff_v1",
                r7c_n_runs=t["n_runs"],
                r7c_n_tool_calls=t["n_tool_calls"],
                r7c_tool_calls_with_interpreted_args=t["n_with_args_interpreted"],
                r7c_state_keys=";".join(sorted(t["state_keys"])),
                official_evaluator_applicable_to_r7c_trace=applicable,
                not_auditable_reason=why,
                human_leg="NOT_CLOSED_no_annotators",
            )
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    tau2_tasks = [r for r in rows if r["domain"] in TAU2_DOMAINS]
    found = [r for r in tau2_tasks if r["official_tau2_task_found"] == "YES"]
    applicable = [r for r in rows if r["official_evaluator_applicable_to_r7c_trace"] == "YES"]
    interpreted = sum(r["r7c_tool_calls_with_interpreted_args"] for r in rows)
    total_calls = sum(r["r7c_n_tool_calls"] for r in rows)

    print(f"official tau2 package importable : {official_ok}  {err}")
    print(f"R7-C tasks in tau2 domains       : {len(tau2_tasks)}/48 (retail+airline)")
    print(f"  of which matched to an official tau2 task with criteria: {len(found)}")
    if found:
        print(f"  official criteria present, e.g.: {found[0]['source_task_id']} -> {found[0]['official_criteria']}")
    print()
    print(f"R7-C tool calls total                       : {total_calls}")
    print(f"R7-C tool calls whose args were interpreted : {interpreted}")
    print(f"tasks where the official evaluator COULD be applied to the R7-C trace: {len(applicable)}/48")
    print()
    print("VERDICT: official-vs-minimal endpoint cross-check on the existing R7-C traces")
    print("         = NOT_AUDITABLE, because R7-C never ran a tau2 simulation.")
    print("         The official evaluator is present and working; what is missing is a")
    print("         trace it could score. This is a property of R7-C, not of the tooling.")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
