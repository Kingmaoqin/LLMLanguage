# tau2 Version And Evaluator Audit

- tau2 module: `/home/xqin5/tau2-bench/src/tau2/__init__.py`
- tau2 version attr: `not_exposed`
- EvaluationType values: `ENV, COMMUNICATE, ACTION, ALL, NL_ASSERTIONS, ALL_WITH_NL_ASSERTIONS, ALL_IGNORE_BASIS, ALL_WITH_NL_ASSERTIONS_IGNORE_BASIS`

The Stage-2.5 runner uses `EvaluationType.ALL_IGNORE_BASIS` so remote NL assertion judging is not silently mixed into local runs. NL assertion tasks are flagged as only locally partially evaluable.

## Official Reward Basis

| Task | Domain | tau2 ID | Reward basis | NL assertion? |
|---|---|---:|---|---:|
| R1_retail_modify_pending | retail | 4 | DB, NL_ASSERTION | True |
| R2_retail_return_cancel_mix | retail | 30 | DB, NL_ASSERTION | True |
| R3_retail_bulk_cancel_return | retail | 55 | DB, NL_ASSERTION | True |
| T1_airline_cancel_multi | airline | 7 | DB, COMMUNICATE | False |
| T2_airline_class_baggage | airline | 12 | DB, COMMUNICATE | False |
| T3_airline_conditional_cancel | airline | 44 | DB, COMMUNICATE | False |
