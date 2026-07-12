#!/usr/bin/env python3
"""R7-D Step 2.2 exposure/eligibility driver: N0/N1/P over natural junctions.

Per (cell, model):
  1. run the neutral opening to the NATURAL family junction (snapshot + proof);
  2. LIVENESS PRE-GATE: one N1 probe; if no junction or the suffix has no real tool
     activity, mark the cell dead and skip the ×5 (saves compute; this is a
     pre-treatment probe, never an outcome-based exclusion of a live cell);
  3. otherwise run N0×5, N1×5, P×5 from the snapshot, scoring every trajectory with
     the official evaluator (ENV / DB-based, deterministic).

No adaptive treatment A. concurrency=1. All local.
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

from scripts.r7d_ipma.step2_2.runner_v3 import Session, MODEL_ENDPOINTS  # noqa: E402
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
}
N0_TEXT = "Yes, please proceed."


def score(session, task, domain) -> dict:
    try:
        r = official_reward(session.messages, task, domain, EvaluationType.ENV)
        return {"endpoint_reward": r.reward, "endpoint_db_match": getattr(r.db_check, "db_match", None),
                "scorable": r.reward is not None}
    except Exception as exc:  # noqa: BLE001
        return {"endpoint_reward": None, "endpoint_error": repr(exc)[:120], "scorable": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--models", nargs="+", default=list(MODEL_ENDPOINTS))
    ap.add_argument("--out", type=pathlib.Path,
                    default=ROOT / "results/r7d_ipma/step2_2/metrics/exposure_suffixes.jsonl")
    args = ap.parse_args()

    reg = [json.loads(l) for l in (ROOT / "data/r7d_ipma/frozen/step2_2_registry.jsonl").open()]
    tasks_by_dom: dict = {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows, junctions = [], []
    t0 = time.time()
    n = 0

    for cell in reg:
        dom = cell["domain"]
        if dom not in tasks_by_dom:
            tasks_by_dom[dom] = {str(t.id): t for t in get_tasks(dom)}
        task = tasks_by_dom[dom][str(cell["tau2_task_id"])]
        stratum = cell["stratum"]
        for model in args.models:
            n += 1
            tag = f"{cell['cell_uid']}__{model}"
            try:
                s = Session(dom, model, MUT[dom])
                snap = s.run_prefix_to_junction(cell["opening"], stratum)
            except Exception as exc:  # noqa: BLE001
                junctions.append(dict(cell=cell["cell_uid"], model=model, junction_found=False,
                                      error=repr(exc)[:120]))
                print(f"[{n}] {tag} PREFIX_FAIL {exc!r}", flush=True)
                continue
            if snap is None:
                junctions.append(dict(cell=cell["cell_uid"], model=model, stratum=stratum,
                                      junction_found=False, reason="no natural junction",
                                      reads_done=s.reads_done))
                print(f"[{n}] {tag} NO_JUNCTION (reads={s.reads_done})", flush=True)
                continue
            junctions.append(dict(cell=cell["cell_uid"], model=model, stratum=stratum,
                                  junction_found=True, prefix_len=len(snap.messages),
                                  proof=snap.junction_proof))
            prefix_len = len(snap.messages)

            def branch(br, turns, rep):
                s.restore(snap)
                m = s.run_suffix(turns, prefix_len)
                m.update(score(s, task, dom))
                m.update(cell=cell["cell_uid"], domain=dom, stratum=stratum, model=model,
                         branch=br, rep=rep, prefix_len=prefix_len,
                         parser_errors=s.parser_errors)
                rows.append(m)
                return m

            try:
                # liveness pre-gate: one N1 probe
                probe = branch("N1", [cell["n1_reply"]], 0)
                live = (probe["n_tool_events"] >= 2 if stratum == "T1"
                        else probe["n_mutations"] >= 1)
                if not live:
                    print(f"[{n}] {tag} DEAD (junction ok but N1 suffix not live: "
                          f"tools={probe['n_tool_events']} mut={probe['n_mutations']})", flush=True)
                    continue
                # full battery on a live cell
                for rep in range(args.reps):
                    branch("N0", [cell["n1_reply"]], rep)  # exact-repeat of the fact-supplying neutral reply
                for rep in range(1, args.reps):     # already have N1 rep0
                    branch("N1", [cell["n1_reply"]], rep)
                for rep in range(args.reps):
                    branch("P", [cell["p_reply"]], rep)
            except Exception as exc:  # noqa: BLE001
                print(f"[{n}] {tag} BATTERY_FAIL {exc!r}", flush=True)
                continue
            n0t = [r["n_tool_events"] for r in rows if r["cell"] == cell["cell_uid"]
                   and r["model"] == model and r["branch"] == "N0"]
            print(f"[{n}] {tag} LIVE N0_tools={n0t} "
                  f"N1_probe_tools={probe['n_tool_events']} mut={probe['n_mutations']}", flush=True)

    with args.out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (ROOT / "results/r7d_ipma/step2_2/metrics/junction_proofs.json").write_text(
        json.dumps(junctions, indent=2, ensure_ascii=False))
    scorable = sum(1 for r in rows if r.get("scorable"))
    print(f"\nsuffix_rows={len(rows)} scorable={scorable} "
          f"junctions={sum(1 for j in junctions if j.get('junction_found'))}/{len(junctions)} "
          f"elapsed={time.time()-t0:.0f}s")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
