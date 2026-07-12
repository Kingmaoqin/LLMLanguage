#!/usr/bin/env python3
"""R7-D Step 2: blind task selection + POS_real, over the REAL tau2 environments.

Selection is by task STRUCTURE only (the gold action sequence and environment
affordances), never by any R7-C outcome / PASR / condition ranking (多轮实验的prompt
§5.2). POS_real (§5.3) is recomputed in the real environment, 0-6.

Minimal pilot set: retail + airline, one T1 (read/resource intensity) and one T2
(evidence/confirmation-before-mutation) task each. External-validity claims are
downgraded accordingly (telecom deferred to full scale).

Outputs: data/r7d_ipma/frozen/step2_task_registry.jsonl
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "data/r7d_ipma/frozen/step2_task_registry.jsonl"

MUT = {
    "retail": {"cancel_pending_order", "exchange_delivered_order_items",
               "modify_pending_order_address", "modify_pending_order_items",
               "modify_pending_order_payment", "modify_user_address",
               "return_delivered_order_items"},
    "airline": {"book_reservation", "cancel_reservation", "update_reservation_baggages",
                "update_reservation_flights", "update_reservation_passengers",
                "send_certificate"},
}

# Chosen blind, by structure (see build note). task_uid, domain, tau2 id, stratum.
SELECTED = [
    ("retail_T2_60", "retail", "60", "T2"),   # find_user -> get_order -> get_product -> modify_items
    ("retail_T1_21", "retail", "21", "T1"),   # 11 reads, 1 write: read/resource intensity
    ("airline_T2_8", "airline", "8", "T2"),   # get_user -> get_reservation -> search -> book
    ("airline_T1_41", "airline", "41", "T1"),  # 8 reads, 0 writes: pure evidence intensity
]


def pos_real(domain: str, task) -> dict:
    """Recompute POS_real 0-6 from the gold action sequence + env affordances."""
    ec = task.evaluation_criteria
    acts = [a.name for a in (ec.actions or [])]
    writes = [a for a in acts if a in MUT[domain]]
    reads = [a for a in acts if a not in MUT[domain]]
    distinct_reads = len(set(reads))

    d1 = int(len(reads) >= 2)                       # >=2 endpoint-equivalent read orderings
    d2 = int(distinct_reads >= 2)                   # >=2 alternative evidence sources
    d3 = int(len(writes) >= 1 and len(reads) >= 1)  # confirmation timing has room (write after reads)
    d4 = int(len(reads) > distinct_reads or distinct_reads >= 3)  # optional/repeatable verification read
    d5 = 1                                           # tau2 is inherently multi-turn (user junction exists)
    d6 = int(len(acts) >= 3)                         # a positive control can add a step w/o changing endpoint
    pos = d1 + d2 + d3 + d4 + d5 + d6
    return dict(gold_actions=acts, n_reads=len(reads), n_distinct_reads=distinct_reads,
                n_writes=len(writes),
                D1=d1, D2=d2, D3=d3, D4=d4, D5=d5, D6=d6, POS_real=pos)


def main() -> int:
    from tau2.run import get_tasks
    by_dom = {}
    rows = []
    for uid, dom, tid, stratum in SELECTED:
        if dom not in by_dom:
            by_dom[dom] = {str(t.id): t for t in get_tasks(dom)}
        task = by_dom[dom][tid]
        pr = pos_real(dom, task)
        rows.append(dict(task_uid=uid, domain=dom, tau2_task_id=tid, stratum=stratum,
                         selection_basis="gold-action structure only; blind to any R7-C outcome",
                         **pr))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"{'task_uid':16s} {'dom':8s} {'strat':5s} {'reads':6s} {'distinct':9s} {'writes':7s} POS_real")
    for r in rows:
        print(f"{r['task_uid']:16s} {r['domain']:8s} {r['stratum']:5s} "
              f"{r['n_reads']:<6d} {r['n_distinct_reads']:<9d} {r['n_writes']:<7d} {r['POS_real']} "
              f"(D1..D6={r['D1']}{r['D2']}{r['D3']}{r['D4']}{r['D5']}{r['D6']})")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    print("NOTE: minimal pilot = 4 tasks, 2 domains. External validity NOT claimed; "
          "telecom + full 18-task set deferred pending scale-up approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
