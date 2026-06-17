# Candidate Task Audit

Scope:
- Domains scanned: retail=114, airline=50
- Selected structural candidates: 15
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
