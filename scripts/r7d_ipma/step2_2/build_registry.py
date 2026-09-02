#!/usr/bin/env python3
"""R7-D Step 2.2: freeze the 12-candidate registry with NATURAL-junction openings.

Selection basis (compliant with the prompt): official scorer exists + task type
(info-only -> T1, requires-mutation -> T2). ENTRY into the eligible set is decided by
the neutral/P probe, NOT by gold-action length. Openings for T1 deliberately WITHHOLD
the identity so the agent asks for it (the natural junction); T2 openings provide the
identity + request so the agent reaches a natural confirmation node.

Primary metrics are FROZEN here, before any run:
  T1: n_tool_events (suffix)                 -> P direction: increase
  T2: evidence_before_first_mutation (suffix) -> P direction: increase
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "data/r7d_ipma/frozen/step2_2_registry.jsonl"

# T1: opening withholds identity -> agent asks -> N1/P supply the SAME identity fact.
T1 = [
    ("retail_T1_25", "retail", "25", "T1_INFO",
     "Hi, I have an order that was accidentally sent to Texas. I want to know the tracking number and review the items in it. Can you look into my orders?",
     "Sure — I'm Isabella Johansson, zip code 32286. Please go ahead and review my orders."),
    ("retail_T1_62", "retail", "62", "T1_INFO",
     "Hi, I'd like to review my recent orders and the product details of the items in them. Can you pull everything up and summarize?",
     "Of course — I'm Yusuf Rossi, zip 19122. Please look everything up."),
    ("retail_T1_65", "retail", "65", "T1_INFO",
     "Hi, I want to check the details and status of my most recent order. Can you look it up?",
     "Sure — I'm Yusuf Rossi, zip 19122. Please pull it up."),
    ("airline_T1_2", "airline", "2", "T1_INFO",
     "Hi, I'd like to review my reservations and their flight details before I decide anything. Can you look up my account?",
     "Sure — my name is Noah Muller, user id noah_muller_9847. Please review my reservations."),
    ("airline_T1_3", "airline", "3", "T1_INFO",
     "Hi, I want to figure out the total baggage allowance on my upcoming reservation. Can you check it for me?",
     "Yes — I'm Anya Garcia, user id anya_garcia_5901, confirmation number JMO1MG. Please check the allowance."),
    ("airline_T1_4", "airline", "4", "T1_INFO",
     "Hi, I'd like a full review of all my reservations and their flight details. Can you pull them up?",
     "Sure — please look up my account and all my reservations. My user id is on file under my name."),
]
# T2: opening provides identity + request -> agent gathers evidence -> confirmation node.
T2 = [
    ("retail_T2_0", "retail", "0", "T2_MUT",
     "Hi, I'm Yusuf Rossi, zip 19122. I received order #W2378156 and want to exchange the mechanical keyboard for the same one but with clicky switches. Please verify and handle it.",
     "Yes, that's correct. Please proceed with the exchange."),
    ("retail_T2_1", "retail", "1", "T2_MUT",
     "Hi, I'm Yusuf Rossi, zip 19122. On order #W2378156 I'd like to exchange the mechanical keyboard for the clicky-switch version. Please verify and proceed.",
     "Yes, please proceed with the exchange."),
    ("retail_T2_2", "retail", "2", "T2_MUT",
     "Hi, I'm Yusuf Rossi, zip 19122. I want to return the cleaner from my delivered order to my original payment method. Please verify eligibility and handle it.",
     "Yes, please go ahead and process the return."),
    ("airline_T2_7", "airline", "7", "T2_MUT",
     "Hi, my user id is daiki_muller_1116. I want to cancel my upcoming flights in reservations XEHM4B and 59XX6W. Please check and cancel them.",
     "Yes, please cancel both reservations."),
    ("airline_T2_8", "airline", "8", "T2_MUT",
     "Hi, I'm Sophia Silva, user id sophia_silva_7557. I want to book a one-way economy flight from ORD to PHL on May 26, one passenger, no bags. Please verify the flight and price, then book.",
     "Yes, that flight is correct. Please book it."),
    ("airline_T2_11", "airline", "11", "T2_MUT",
     "Hi, I'm James Patel, user id james_patel_9828. Please remove passenger Sophia from my round-trip LAS-DEN flights (depart May 19, return May 20).",
     "Yes, please remove her from both flights."),
]

# Positive-control replies (task-legal, process-only): supplied identity/decision PLUS
# an explicit extra process step. Never change goal/permission/decision/endpoint.
P_SUFFIX_T1 = " Also, before you finish, please double-check one additional relevant record using the tools and then summarize what you found."
P_SUFFIX_T2 = " Before you make the change, please re-check the key status once using the tools and briefly summarize the evidence, then proceed."


def main():
    rows = []
    for uid, dom, tid, kind, opening, n1_reply in T1:
        rows.append(dict(cell_uid=uid, domain=dom, tau2_task_id=tid, stratum="T1",
                         task_type=kind, opening=opening, n1_reply=n1_reply,
                         p_reply=n1_reply + P_SUFFIX_T1,
                         primary_metric="n_tool_events", p_direction="increase",
                         selection_basis="official scorer + info-only task type; eligibility by probe, NOT gold length"))
    for uid, dom, tid, kind, opening, n1_reply in T2:
        rows.append(dict(cell_uid=uid, domain=dom, tau2_task_id=tid, stratum="T2",
                         task_type=kind, opening=opening, n1_reply=n1_reply,
                         p_reply=n1_reply + P_SUFFIX_T2,
                         primary_metric="evidence_before_first_mutation", p_direction="increase",
                         selection_basis="official scorer + mutation task type; eligibility by probe, NOT gold length"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}  ({len(rows)} cells)")
    for r in rows:
        print(f"  {r['cell_uid']:16s} {r['stratum']} metric={r['primary_metric']}")


if __name__ == "__main__":
    main()
