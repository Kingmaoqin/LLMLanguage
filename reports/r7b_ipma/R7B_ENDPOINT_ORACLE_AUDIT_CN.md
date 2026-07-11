# R7-B endpoint oracle 审计

- runs evaluated: 288
- endpoint unsupported: 0
- output: `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/main/endpoint/endpoint_oracle_per_run.csv`

规则：`endpoint_oracle_supported=False` 或 `final_state_correct` 空值不得进入 confirmatory PASR。
