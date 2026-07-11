# R7 PASR 定义与逐例复算审计

## 结论评级

PROVISIONAL。PASR 公式可复算，但原脚本对 `final_state_correct` 缺失的 pair 采用 endpoint_not_worse=True 的兼容口径，严格 endpoint-supported 口径下可支撑的 PASR 数减少。

## 复算结果

- reported PASR=1 总数（r7_pairs.csv）：189
- 本审计脚本兼容口径 PASR=1：176
- 其中 endpoint oracle 严格支持的 PASR=1：96
- PASR=1 但 endpoint_supported=False：80
- 逐例解释表：`results/r7_ipma/audit/pasr_success_explanations.csv`
- 复算 pair 表：`results/r7_ipma/audit/r7_pairs_recomputed_from_raw.csv`

## 必须修改的论文表述

不能只报告“总体 PASR≈14%”。应同时报告：

1. 原分析脚本兼容口径 PASR；
2. endpoint oracle 严格支持口径 PASR；
3. endpoint unsupported 的 PASR 样本数；
4. 每个 PASR=1 的 family threshold 与 noise/gate 解释。
