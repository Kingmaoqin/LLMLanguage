# R6 token/duration/latency 修复报告

- 输入根目录：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r6_sensitivity/full_main_seq_eligible_20260626`
- trace 数：2160
- token 缺失：720（缺失率 33.3%）
- duration 缺失：720（缺失率 33.3%）
- 输出：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7_ipma/measurement_repair/usage_timing_metrics.csv`

提取优先级：provider reported total / prompt+completion / missing。缺失值使用 `MISSING`，timestamp 缺失使用 `missing_no_timestamp`，避免空字符串进入后续统计。

> ⚠️ PDF §2.2 规则 7：token 或 duration 缺失率超过 10%，**不能做 efficiency / latency claim**。当前 tau2 traces 缺 provider usage 与 timestamp，R7 runner 必须写入 usage/timing 后方可对这部分做效率结论。
