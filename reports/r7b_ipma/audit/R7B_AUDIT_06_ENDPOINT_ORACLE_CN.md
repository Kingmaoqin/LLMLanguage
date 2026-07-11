# Audit 06：endpoint oracle

## 结论

- runs audited：1296
- endpoint supported：1296/1296
- final_state_correct=None：0
- self-declared 与 strict field diff 不一致：580

## 关键发现

本审计从 raw trace 的 initial/final state snapshot 独立复算字段 diff，没有使用 agent self-report。当前 864 条已有 trace 都有可读 snapshot；但不是 Claude 声称的 1296 条。

注意：现有 `evaluate_endpoint_from_snapshot.py` 对 `expected_field_diffs=[]` 的只读任务不会把 unexpected actual diff 标为错误。本审计采用更严格口径：即使 expected 为空，任何 actual field diff 都算 unexpected。当前结果中是否影响 PASR 见 Audit 08。

机器表：

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_endpoint_oracle_recomputed.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_endpoint_field_diff_samples.csv`
