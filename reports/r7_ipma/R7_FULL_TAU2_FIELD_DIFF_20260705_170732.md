# R6 tau2 field-level diff 修复审计

- 输入根目录：`results/r7_ipma/main/full_20260702_043032`
- tau2/retail/airline traces：540
- 可由 trace snapshot 重建：540
- 需要 rerun/补 snapshot：0
- 输出 CSV：`results/r7_ipma/main/full_20260702_043032/measurement_repair/tau2_field_diffs.csv`
- 输出 JSONL：`results/r7_ipma/main/full_20260702_043032/measurement_repair/tau2_field_diffs.jsonl`

判定原则：仅在 trace 同时包含 initial/final state snapshot 时重建字段级 diff；缺 snapshot 一律标记为 `cannot_reconstruct_missing_snapshot`，不从 reward、工具名或自然语言结果倒推。
