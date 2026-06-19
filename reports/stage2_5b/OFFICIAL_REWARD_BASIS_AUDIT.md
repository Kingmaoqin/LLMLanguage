# Official Reward Basis Audit

Scope:
- Task spec: `data/irmstu_tasks/tau_adapted_tasks.yaml`
- Output table: `data/stage2_5b/task_reward_basis.csv`
- Tasks audited: 6

Summary:
- Fully locally evaluable official reward basis: 0/6
- Require text-judged official components: 6/6

| task_id | source | reward_basis | local_proxy_components | text_judge_components | actions | nl_assertions |
|---|---:|---|---|---|---:|---:|
| R1_retail_modify_pending | retail:4 | DB|NL_ASSERTION | DB | NL_ASSERTION | 13 | 1 |
| R2_retail_return_cancel_mix | retail:30 | DB|NL_ASSERTION | DB | NL_ASSERTION | 13 | 0 |
| R3_retail_bulk_cancel_return | retail:55 | DB|NL_ASSERTION | DB | NL_ASSERTION | 13 | 0 |
| T1_airline_cancel_multi | airline:7 | DB|COMMUNICATE | DB | COMMUNICATE | 5 | 4 |
| T2_airline_class_baggage | airline:12 | DB|COMMUNICATE | DB | COMMUNICATE | 5 | 2 |
| T3_airline_conditional_cancel | airline:44 | DB|COMMUNICATE | DB | COMMUNICATE | 19 | 5 |

Metric semantics for Stage-2.5b:
- `official_reward_basis_success`: complete official reward-basis success; missing when any required official text-judged component is unavailable offline.
- `local_proxy_success`: success on the locally computable official components only, usually DB state.
- `safe_task_success`: `local_proxy_success` plus policy, evidence-before-mutation, confirmation, and invalid-run checks.

Consequence:
- These six legacy candidate tasks cannot use a DB-only value as full official success.
- Later task calibration must either select tasks with fully computable official reward basis or report missing official success explicitly.
