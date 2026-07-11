# R7 raw trace → table 独立复算审计

外部参照：τ-bench 定义为真实域 tool-agent-user interaction，强调 domain policy 与最终数据库状态评估；HAL 在 TAU-bench Airline changelog 中因 few-shot scaffold 泄漏 test examples 删除结果；AgentDojo 强调动态环境中攻击与防御共同评估。因此本审计把 leakage/freeze/prompt contamination、trace-level oracle 与 defense audit 作为必要项。

## 结论评级

PROVISIONAL。raw trace 数与 per-run metrics 行数可以对齐，但 endpoint/final-state 字段在 tau2 部分仍有不可直接判定项；部分指标必须降级为 provisional。

## 核心计数

- raw trace 文件数：1620
- per_run_metrics 行数：1620
- reported r7_pairs 行数：1350
- raw/table core mismatch 数：422
- mismatch 明细：`results/r7_ipma/audit/raw_trace_metric_mismatches.csv`

## 关键问题

- 工具序列、工具数、mutation 数、安全事件可以从 trace 复算。
- `final_state_correct` 在 tau2 trace 中大量为 None/blank，不能直接支撑强 endpoint oracle claim。
- `live_run_summary.json` 只反映最后一次分批 runner 状态，不应作为 1620 全量完成证明；1620 应以 trace 文件计数和 per-run table 计数为准。
