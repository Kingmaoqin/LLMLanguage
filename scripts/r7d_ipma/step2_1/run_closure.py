#!/usr/bin/env python3
"""R7-D Step 2.1 closure driver: produce G1(real-suffix)/G2/G3/G4 evidence.

For each constructible cell (task,stratum) x model:
  * run the neutral prefix to a FAMILY-SPECIFIC junction, emit the junction proof (G2);
  * from that snapshot run N0 x R0 (exact neutral repeat -> reproducibility, G3),
    N1 x R1 (matched neutral), P x RP (explicit positive control, G4);
  * officially score every full trajectory with evaluate_simulation (G1 real-suffix,
    no mutation proxy).

No adaptive treatment A. concurrency=1 (one rollout at a time per model). All local.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from loguru import logger  # noqa: E402
logger.remove()

from scripts.r7d_ipma.step2_1.runner_v2 import Session, MODEL_ENDPOINTS  # noqa: E402
from scripts.r7d_ipma.step2_1.official_scorer import official_reward  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType  # noqa: E402
from tau2.run import get_tasks  # noqa: E402

MUT = {
    "retail": {"cancel_pending_order", "exchange_delivered_order_items",
               "modify_pending_order_address", "modify_pending_order_items",
               "modify_pending_order_payment", "modify_user_address",
               "return_delivered_order_items"},
    "airline": {"book_reservation", "cancel_reservation", "update_reservation_baggages",
                "update_reservation_flights", "update_reservation_passengers", "send_certificate"},
    "telecom": {"suspend_line", "resume_line", "send_payment_request", "make_payment",
                "reboot_device", "refuel_data"},
}

# Frozen neutral openings (pre-seed T2 decision facts so a mutation IS reachable).
OPENINGS = {
    "retail_T1_21": "Hi. I'm Yusuf Rossi, zip 19122. Please review my account and all of my orders and their items in detail, and tell me the full status. Take your time to check everything.",
    "retail_T2_60": "Hi. You want to change your wireless earbuds in order #W5061109 to the blue variant (item 6077640618), same price $242.92 or lower, and want the price verified explicitly. You are Chen Johnson from Houston TX, 77004.",
    "airline_T1_41": "Hi, this is a review request. Please look up my user details and all of my reservations and their flight details thoroughly and summarize them. My user id is on file under my name.",
    "airline_T2_8": "Hi, my name is Sophia Silva, user id sophia_silva_7557. I want to book the exact same one-way flight as my recent May 10 ORD to PHL flight, on May 26, economy, one passenger, no bags. Please verify the flight and price before booking.",
    "telecom_T2_overdue": "Hi. My line was suspended because of an overdue bill. I want to pay the overdue amount and get my line resumed. Please check my account and handle the payment and resume.",
}

N1_TURNS = ["Yes, that's right. Please continue with the required process.",
            "Understood. Please proceed as appropriate."]
P_TURNS_T1 = ["Before continuing, please re-check the relevant details once using the tools, then proceed.",
              "Thanks. Please continue."]
P_TURNS_T2 = ["Before you make the change, please briefly summarize the evidence you have gathered using the tools, then proceed.",
              "Understood. Please proceed."]
N0_TEXT = "Yes, please proceed with the required process."


def score(session, task, domain) -> dict:
    try:
        r = official_reward(session.messages, task, domain, EvaluationType.ENV)
        return {"endpoint_reward": r.reward, "endpoint_db_match": getattr(r.db_check, "db_match", None),
                "scorable": r.reward is not None}
    except Exception as exc:  # noqa: BLE001
        return {"endpoint_reward": None, "endpoint_error": repr(exc)[:150], "scorable": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--r0", type=int, default=5)   # N0 exact repeats (G3)
    ap.add_argument("--r1", type=int, default=2)   # N1
    ap.add_argument("--rp", type=int, default=2)   # P
    ap.add_argument("--models", nargs="+", default=list(MODEL_ENDPOINTS))
    ap.add_argument("--out", type=pathlib.Path,
                    default=ROOT / "results/r7d_ipma/step2_1/metrics/closure_suffixes.jsonl")
    args = ap.parse_args()

    reg = [json.loads(l) for l in (ROOT / "data/r7d_ipma/frozen/step2_1_task_registry.jsonl").open()
           if json.loads(l).get("tau2_task_id")]
    tasks_by_dom: dict = {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "results/r7d_ipma/step2_1/traces").mkdir(parents=True, exist_ok=True)

    rows = []
    junctions = []
    t0 = time.time()
    n = 0
    for cell in reg:
        dom = cell["domain"]
        if dom not in tasks_by_dom:
            tasks_by_dom[dom] = {str(t.id): t for t in get_tasks(dom)}
        task = tasks_by_dom[dom][str(cell["tau2_task_id"])]
        opening = OPENINGS[cell["cell_uid"]]
        stratum = cell["stratum"]
        for model in args.models:
            n += 1
            tag = f"{cell['cell_uid']}__{model}"
            try:
                s = Session(dom, model, MUT[dom], gold_reads=cell["gold_reads"])
                snap = s.run_prefix_to_junction(opening, stratum)
            except Exception as exc:  # noqa: BLE001
                junctions.append(dict(cell=cell["cell_uid"], model=model, junction_found=False,
                                      error=repr(exc)[:150]))
                print(f"[{n}] {tag} PREFIX_FAIL {exc!r}", flush=True)
                continue
            if snap is None:
                junctions.append(dict(cell=cell["cell_uid"], model=model, stratum=stratum,
                                      junction_found=False, reads_done=s.reads_done,
                                      mutations_done=s.mutations_done,
                                      reason="no valid family junction reachable"))
                print(f"[{n}] {tag} NO_JUNCTION (reads={s.reads_done} mut={s.mutations_done})", flush=True)
                continue
            junctions.append(dict(cell=cell["cell_uid"], model=model, stratum=stratum,
                                  junction_found=True, prefix_len=len(snap.messages),
                                  proof=snap.junction_proof))
            prefix_len = len(snap.messages)
            p_turns = P_TURNS_T1 if stratum == "T1" else P_TURNS_T2

            def run_branch(branch, turns, rep):
                s.restore(snap)
                m = s.run_suffix(turns, prefix_len)
                sc = score(s, task, dom)
                m.update(sc)
                m.update(cell=cell["cell_uid"], domain=dom, stratum=stratum, model=model,
                         branch=branch, rep=rep, prefix_len=prefix_len,
                         junction_reason=snap.junction_reason)
                rows.append(m)
                return m

            for rep in range(args.r0):
                run_branch("N0", [N0_TEXT], rep)
            for rep in range(args.r1):
                run_branch("N1", N1_TURNS[:1], rep)
            for rep in range(args.rp):
                run_branch("P", p_turns, rep)
            n0tools = [r["n_tool_events"] for r in rows if r["cell"] == cell["cell_uid"]
                       and r["model"] == model and r["branch"] == "N0"]
            print(f"[{n}] {tag} OK junction={snap.junction_reason[:22]} "
                  f"N0_tools={n0tools} scorable={all(r['scorable'] for r in rows[-(args.r0+args.r1+args.rp):])}",
                  flush=True)

    with args.out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (ROOT / "results/r7d_ipma/step2_1/metrics/junction_proofs.json").write_text(
        json.dumps(junctions, indent=2, ensure_ascii=False))
    scorable = sum(1 for r in rows if r.get("scorable"))
    print(f"\nsuffixes={len(rows)} scorable={scorable} junctions_found="
          f"{sum(1 for j in junctions if j.get('junction_found'))}/{len(junctions)} "
          f"elapsed={time.time()-t0:.0f}s")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
