# Benchmark Task Diff Audit

Generated: 2026-06-16T23:25:03.644311+00:00

Comparison ref: `origin/main`

No network fetch or automatic benchmark upgrade was performed. The comparison uses the local remote-tracking ref if present.

Evaluator files changed vs ref: `False`

| Task | Domain | Source ID | Task Text Changed | Reward Basis | Expected State Changed | Policy Changed | Known Issue Files |
|---|---|---:|---|---|---|---|---|
| R1_retail_modify_pending | retail | 4 | False | `DB,NL_ASSERTION` | False | False | task_4_issue_2b74ee61.json |
| R2_retail_return_cancel_mix | retail | 30 | False | `DB,NL_ASSERTION` | False | False | (none) |
| R3_retail_bulk_cancel_return | retail | 55 | False | `DB,NL_ASSERTION` | False | False | (none) |
| T1_airline_cancel_multi | airline | 7 | False | `DB,COMMUNICATE` | False | False | (none) |
| T2_airline_class_baggage | airline | 12 | False | `DB,COMMUNICATE` | False | False | (none) |
| T3_airline_conditional_cancel | airline | 44 | False | `DB,COMMUNICATE` | False | False | (none) |

## Interpretation

The six legacy task labels are audited here only to establish provenance. Stage-2.5b task calibration must still scan 10-15 benchmark tasks and freeze a new confirmatory set before treatment runs.
