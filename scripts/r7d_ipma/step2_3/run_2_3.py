#!/usr/bin/env python3
"""R7-D Step 2.3 driver: T1 eligibility expansion + T2 failure decomposition.

T1 cells: run N0x5 / N1x5 / P x5 (eligibility, same criteria as Step 2.2).
T2 cells: run N1 x REPS with FULL diagnostics per run, then classify the failure into
  {invalid_junction, tool_or_parser_error, insufficient_user_decision_info,
   agent_did_not_execute_mutation, db_correct_but_communicate_fail,
   db_wrong_and_communicate_fail, wrong_mutation, success}.

No adaptive treatment A. Resilient per-cell. All local.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from loguru import logger  # noqa: E402
logger.remove()

from scripts.r7d_ipma.step2_2.runner_v3 import Session, MODEL_ENDPOINTS  # noqa: E402
from scripts.r7d_ipma.step2_1.official_scorer import official_reward  # noqa: E402
from scripts.r7d_ipma.step2_3.scorer_components import components, classify_t2_failure  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType  # noqa: E402
from tau2.run import get_tasks  # noqa: E402
from tau2.data_model.message import AssistantMessage, ToolMessage  # noqa: E402

MUT = {
    "retail": {"cancel_pending_order", "exchange_delivered_order_items",
               "modify_pending_order_address", "modify_pending_order_items",
               "modify_pending_order_payment", "modify_user_address",
               "return_delivered_order_items"},
    "airline": {"book_reservation", "cancel_reservation", "update_reservation_baggages",
                "update_reservation_flights", "update_reservation_passengers", "send_certificate"},
}


def suffix_diag(session, prefix_len: int) -> dict:
    suffix = session.messages[prefix_len:]
    tool_errs = sum(1 for m in suffix if isinstance(m, ToolMessage) and m.error and m.content != "stop")
    # did the agent keep asking the user (multiple user-facing messages, no mutation)?
    agent_msgs = [m for m in suffix if isinstance(m, AssistantMessage) and not m.tool_calls]
    return dict(suffix_tool_errors=tool_errs, agent_user_msgs=len(agent_msgs))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--t1-reps", type=int, default=5)
    ap.add_argument("--t2-reps", type=int, default=3)
    ap.add_argument("--models", nargs="+", default=list(MODEL_ENDPOINTS))
    ap.add_argument("--out", type=pathlib.Path,
                    default=ROOT / "results/r7d_ipma/step2_3/metrics/rows.jsonl")
    args = ap.parse_args()
    reg = [json.loads(l) for l in (ROOT / "data/r7d_ipma/frozen/step2_3_registry.jsonl").open()]
    tasks_by_dom: dict = {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows, t2diag, junctions = [], [], []
    t0 = time.time(); n = 0

    for cell in reg:
        dom = cell["domain"]
        if dom not in tasks_by_dom:
            tasks_by_dom[dom] = {str(t.id): t for t in get_tasks(dom)}
        task = tasks_by_dom[dom][str(cell["tau2_task_id"])]
        stratum = cell["stratum"]
        for model in args.models:
            n += 1; tag = f"{cell['cell_uid']}__{model}"
            try:
                s = Session(dom, model, MUT[dom])
                snap = s.run_prefix_to_junction(cell["opening"], stratum)
            except Exception as exc:  # noqa: BLE001
                junctions.append(dict(cell=cell["cell_uid"], model=model, junction_found=False, error=repr(exc)[:120]))
                print(f"[{n}] {tag} PREFIX_FAIL {exc!r}", flush=True); continue
            jf = snap is not None
            junctions.append(dict(cell=cell["cell_uid"], model=model, stratum=stratum,
                                  junction_found=jf,
                                  proof=(snap.junction_proof if jf else None),
                                  reads_at_junction=(snap.reads_done if jf else s.reads_done)))
            if not jf:
                print(f"[{n}] {tag} NO_JUNCTION (reads={s.reads_done})", flush=True)
                if stratum == "T2":
                    t2diag.append(dict(cell=cell["cell_uid"], model=model, rep=0,
                                       junction_found=False, failure="invalid_junction"))
                continue
            prefix_len = len(snap.messages)

            def branch(br, turns, rep):
                s.restore(snap)
                m = s.run_suffix(turns, prefix_len)
                try:
                    r = official_reward(s.messages, task, dom, EvaluationType.ENV)
                    m.update(endpoint_reward=r.reward, scorable=r.reward is not None)
                except Exception as exc:  # noqa: BLE001
                    m.update(endpoint_reward=None, scorable=False, score_error=repr(exc)[:100])
                m.update(cell=cell["cell_uid"], domain=dom, stratum=stratum, model=model,
                         branch=br, rep=rep, prefix_len=prefix_len, parser_errors=s.parser_errors)
                rows.append(m); return m

            try:
                if stratum == "T1":
                    probe = branch("N1", [cell["n1_reply"]], 0)
                    if probe["n_tool_events"] < 2:
                        print(f"[{n}] {tag} T1_DEAD (N1 tools={probe['n_tool_events']})", flush=True); continue
                    for rep in range(args.t1_reps):
                        branch("N0", [cell["n1_reply"]], rep)
                    for rep in range(1, args.t1_reps):
                        branch("N1", [cell["n1_reply"]], rep)
                    for rep in range(args.t1_reps):
                        branch("P", [cell["p_reply"]], rep)
                    n0 = [r["n_tool_events"] for r in rows if r["cell"] == cell["cell_uid"] and r["model"] == model and r["branch"] == "N0"]
                    print(f"[{n}] {tag} T1_LIVE N0={n0}", flush=True)
                else:  # T2 diagnostic
                    fails = []
                    for rep in range(args.t2_reps):
                        m = branch("N1", [cell["n1_reply"]], rep)
                        sd = suffix_diag(s, prefix_len)
                        comp = components(s.messages, task, dom)
                        diag = dict(cell=cell["cell_uid"], model=model, rep=rep,
                                    junction_found=True, reads_at_junction=snap.reads_done,
                                    suffix_mutations=m["n_mutations"], suffix_tools=m["n_tool_events"],
                                    parser_errors=s.parser_errors,
                                    agent_kept_asking=sd["agent_user_msgs"] >= 2 and m["n_mutations"] == 0,
                                    **sd, **comp)
                        diag["failure"] = classify_t2_failure(diag)
                        t2diag.append(diag); fails.append(diag["failure"])
                    print(f"[{n}] {tag} T2_DIAG {collections.Counter(fails)}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[{n}] {tag} BATTERY_FAIL {exc!r}", flush=True); continue

    with args.out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (ROOT / "results/r7d_ipma/step2_3/metrics/t2_diagnostics.jsonl").write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in t2diag))
    (ROOT / "results/r7d_ipma/step2_3/metrics/junctions.json").write_text(
        json.dumps(junctions, indent=2, ensure_ascii=False))
    print(f"\nrows={len(rows)} t2diag={len(t2diag)} scorable={sum(1 for r in rows if r.get('scorable'))} "
          f"elapsed={time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
