# Audit 03：raw trace → metrics 独立复算

## 结论

- recomputed rows：1296
- existing per_run rows：1296
- mismatch rows：20693
- 涉及 reported PASR=1 attack run 的 mismatch：713

## mismatch by field

- n_read_events: 1296
- n_write_events: 1296
- first_tool_step: 1296
- confirmation_obtained: 1296
- confirmation_step_index: 1296
- confirmation_before_action_rate: 1296
- unsafe_compliance: 1296
- privacy_violation: 1296
- policy_critical_failure: 1296
- final_state_correct: 1296
- endpoint_oracle_supported: 1296
- tokens_total: 1296
- duration_seconds: 1296
- n_invalid_tool_calls: 1296
- n_retries: 1296
- first_mutation_step: 1253

## 解释

大量 mismatch 来自 existing `per_run_metrics.csv` 只包含 PASR 脚本所需字段，不包含审计要求的 `n_read_events/tokens_total/duration_seconds/n_retries` 等字段。这意味着这些 claim 不能从 existing table 自身验证，必须依赖 raw trace 复算。

机器表：

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_per_run_metrics_recomputed.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_metric_mismatches.csv`
