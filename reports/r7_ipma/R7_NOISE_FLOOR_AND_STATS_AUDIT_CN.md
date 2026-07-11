# R7 noise floor 与统计审计

## 结论评级

PROVISIONAL。PASR 均值可复算；工具调用 Wilcoxon/FDR 基本可复核。但“显著高于 neutral noise floor”不能只用总体 PASR CI>0 表达，必须逐 family/metric 说明 threshold 与 neutral floor 的关系。

## 复算统计

详见：`results/r7_ipma/audit/stats_recomputed_from_raw_pairs.csv`

## 原 primary_pasr_contrasts

- 行数：5
- 条件：['urgency_pressure', 'trust_pressure', 'frustration_pressure', 'continuation_pressure', 'implicit_progress_pressure']

## 注意

主报告中 continuation 的 q=0.057 属边缘，不应写成 FDR 显著；可以写方向性最强、未过 0.05 FDR。
