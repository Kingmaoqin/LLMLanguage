# Candidate Task Audit

Scope:
- Domains scanned: retail=114, airline=50
- Selected structural candidates: 31
- Candidate CSV: `data/stage2_5b/candidate_tasks.csv`
- Full scan JSON: `artifacts/stage2_5b/candidate_task_scan.json`

Selection rule:
- Use only real tau2 tasks from the frozen local benchmark.
- Require at least one irreversible/write action, a multistage read/write reference workflow, and at least two evidence/branch proxy points.
- Do not use treatment outcomes or model success rates.

| domain | source_task_id | reward_basis | actions | writes | branch_proxy | fully_local | write_tools |
|---|---:|---|---:|---:|---:|---|---|
| retail | 21 | DB|NL_ASSERTION | 12 | 1 | 6 | false | modify_pending_order_items |
| retail | 23 | DB|NL_ASSERTION | 12 | 3 | 5 | false | exchange_delivered_order_items|modify_pending_order_items |
| retail | 30 | DB|NL_ASSERTION | 13 | 3 | 5 | false | cancel_pending_order|return_delivered_order_items |
| retail | 41 | DB|NL_ASSERTION | 10 | 1 | 6 | false | modify_pending_order_items |
| retail | 42 | DB|NL_ASSERTION | 10 | 1 | 6 | false | modify_pending_order_items |
| retail | 31 | DB|NL_ASSERTION | 12 | 2 | 4 | false | cancel_pending_order|return_delivered_order_items |
| retail | 32 | DB|NL_ASSERTION | 13 | 3 | 4 | false | cancel_pending_order|return_delivered_order_items |
| retail | 54 | DB|NL_ASSERTION | 12 | 3 | 4 | false | cancel_pending_order|return_delivered_order_items |
| retail | 55 | DB|NL_ASSERTION | 13 | 4 | 4 | false | cancel_pending_order|return_delivered_order_items |
| retail | 3 | DB|NL_ASSERTION | 12 | 1 | 4 | false | modify_pending_order_items |
| retail | 4 | DB|NL_ASSERTION | 13 | 2 | 4 | false | modify_pending_order_items |
| retail | 16 | DB|NL_ASSERTION | 9 | 3 | 5 | false | cancel_pending_order|return_delivered_order_items |
| retail | 49 | DB|NL_ASSERTION | 10 | 1 | 5 | false | exchange_delivered_order_items |
| retail | 2 | DB|NL_ASSERTION | 11 | 1 | 4 | false | return_delivered_order_items |
| retail | 28 | DB|NL_ASSERTION | 11 | 3 | 4 | false | return_delivered_order_items |
| retail | 64 | DB|NL_ASSERTION | 8 | 2 | 5 | false | exchange_delivered_order_items|modify_pending_order_items |
| retail | 20 | DB|NL_ASSERTION | 10 | 1 | 4 | false | modify_pending_order_items |
| retail | 35 | DB|NL_ASSERTION | 7 | 2 | 5 | false | modify_pending_order_items|return_delivered_order_items |
| retail | 26 | DB|NL_ASSERTION | 8 | 2 | 4 | false | return_delivered_order_items|transfer_to_human_agents |
| retail | 63 | DB|NL_ASSERTION | 7 | 1 | 5 | false | modify_pending_order_items |
| retail | 15 | DB|NL_ASSERTION | 7 | 1 | 4 | false | modify_pending_order_items |
| retail | 19 | DB|NL_ASSERTION | 7 | 1 | 4 | false | return_delivered_order_items |
| retail | 56 | DB|NL_ASSERTION | 7 | 1 | 4 | false | modify_pending_order_items |
| retail | 6 | DB|NL_ASSERTION | 6 | 1 | 4 | false | exchange_delivered_order_items |
| airline | 44 | DB|COMMUNICATE | 19 | 3 | 3 | false | update_reservation_flights |
| airline | 39 | DB|COMMUNICATE | 11 | 3 | 2 | false | cancel_reservation |
| airline | 42 | DB|COMMUNICATE | 10 | 2 | 2 | false | cancel_reservation |
| airline | 33 | DB|COMMUNICATE | 5 | 2 | 3 | false | update_reservation_baggages|update_reservation_flights |
| airline | 12 | DB|COMMUNICATE | 5 | 1 | 3 | false | update_reservation_baggages |
| airline | 32 | DB|COMMUNICATE | 5 | 2 | 3 | false | update_reservation_flights |
| airline | 7 | DB|COMMUNICATE | 5 | 3 | 2 | false | cancel_reservation|update_reservation_flights |

Calibration status:
- These are structural candidates only.
- Confirmatory inclusion still requires neutral-condition calibration with calibration seeds separated from confirmatory seeds.
- Tasks with text-judged reward components must keep `official_reward_basis_success` missing unless a frozen text evaluator is added.
