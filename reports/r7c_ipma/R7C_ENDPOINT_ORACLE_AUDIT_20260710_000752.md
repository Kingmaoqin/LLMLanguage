# R7-B endpoint oracle 审计

- runs evaluated: 2592
- endpoint unsupported: 0
- output: `results/r7c_ipma/full/live_20260710_000752/endpoint/endpoint_oracle_per_run.csv`

规则：`endpoint_oracle_supported=False` 或 `final_state_correct` 空值不得进入 confirmatory PASR。
