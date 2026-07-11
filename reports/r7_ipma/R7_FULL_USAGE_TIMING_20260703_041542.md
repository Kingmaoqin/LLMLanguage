# R6 token/duration/latency 修复报告

- 输入根目录：`results/r7_ipma/main/full_20260702_043032`
- trace 数：0
- token 缺失：0（缺失率 0.0%）
- duration 缺失：0（缺失率 0.0%）
- 输出：`results/r7_ipma/main/full_20260702_043032/measurement_repair/usage_timing_metrics.csv`

提取优先级：provider reported total / prompt+completion / missing。缺失值使用 `MISSING`，timestamp 缺失使用 `missing_no_timestamp`，避免空字符串进入后续统计。
