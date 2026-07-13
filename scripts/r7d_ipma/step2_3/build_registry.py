#!/usr/bin/env python3
"""R7-D Step 2.3: expanded blind candidate pool (T1=8, T2=12) with openings built
from each task's OWN structured scenario (reason_for_call + known_info).

Selection: official scorer + task type (info-only=T1 / mutation=T2). NOT by PASR or
any mid-phase result. T2 pool deliberately includes several SINGLE-ACTION mutation
tasks (retail 36; airline 11/15/19/20) to test whether "task too complex" explains the
T2 failure.

Openings:
  T1 -> withhold identity so the agent asks (natural junction); N1 reply supplies the
        identity from known_info.
  T2 -> provide identity + request; N1 reply confirms; P adds a task-legal process step.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "data/r7d_ipma/frozen/step2_3_registry.jsonl"

SEL = {
    ("retail", "T1"): ["25", "62", "65", "67"],
    ("airline", "T1"): ["1", "2", "3", "4"],
    ("retail", "T2"): ["0", "5", "13", "36", "37", "38"],
    ("airline", "T2"): ["8", "11", "15", "19", "20", "12"],
}
P_SUFFIX_T1 = " Also, before you finish, please double-check one additional relevant record using the tools and then summarize what you found."
P_SUFFIX_T2 = " Before you make the change, please re-check the key status once using the tools and briefly summarize the evidence, then proceed."


def clean(s: str) -> str:
    return " ".join((s or "").split())


def main():
    from tau2.run import get_tasks
    rows = []
    for (dom, stratum), ids in SEL.items():
        tmap = {str(t.id): t for t in get_tasks(dom)}
        for tid in ids:
            t = tmap[tid]
            ins = t.user_scenario.instructions
            reason = clean(getattr(ins, "reason_for_call", ""))[:400]
            known = clean(getattr(ins, "known_info", ""))[:200]
            uid = f"{dom}_{stratum}_{tid}"
            if stratum == "T1":
                # withhold identity -> agent asks -> N1 supplies it
                opening = f"Hi. {reason} Can you look this up for me?"
                n1 = f"Sure — {known} Please go ahead and proceed."
                p = n1 + P_SUFFIX_T1
                metric = "n_tool_events"
            else:
                opening = f"Hi. {known} {reason} Please verify and handle it."
                n1 = "Yes, that's correct. Please proceed with the change."
                p = n1 + P_SUFFIX_T2
                metric = "evidence_before_first_mutation"
            rows.append(dict(cell_uid=uid, domain=dom, tau2_task_id=tid, stratum=stratum,
                             opening=opening, n1_reply=n1, p_reply=p,
                             primary_metric=metric, p_direction="increase",
                             known_info=known, reason=reason,
                             selection_basis="official scorer + task type; blind, NOT PASR/mid-phase"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    n1 = sum(1 for r in rows if r["stratum"] == "T1")
    print(f"wrote {OUT}  ({len(rows)} cells: T1={n1} T2={len(rows)-n1})")


if __name__ == "__main__":
    main()
