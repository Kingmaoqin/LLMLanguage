# Stage-2.5 修复后完整实验总报告

## 1. 执行结论

修复后的 Stage-2.5 实验已经在 A100 可运行的两个模型上完整跑完并分析：

- Gemma 主实验：120/120
- Gemma diagnostic：80/80
- gpt-oss 主实验：120/120
- gpt-oss diagnostic：80/80

合计 400 runs，全部 0 invalid、0 duplicate、0 missing run id。所有正式分析只使用以下四个目录：

- `results/stage2_5_repair/full_gemma_v2`
- `results/stage2_5_repair/diagnostic_gemma`
- `results/stage2_5_repair/full_gpt_oss`
- `results/stage2_5_repair/diagnostic_gpt_oss`

旧目录 `results/stage2_5_repair/full_gemma` 是早期中断且日志不完整的试跑，不纳入任何正式结论。

## 2. 完整性审计

| 阶段 | 预期 | 实际 | invalid | duplicate | manifest 缺失 |
|---|---:|---:|---:|---:|---:|
| Gemma full | 120 | 120 | 0 | 0 | 0 |
| Gemma diagnostic | 80 | 80 | 0 | 0 | 0 |
| gpt-oss full | 120 | 120 | 0 | 0 | 0 |
| gpt-oss diagnostic | 80 | 80 | 0 | 0 | 0 |

四个正式结果目录均包含修改方案第 20 节要求的 12 类输出文件：

`raw_model_outputs.jsonl`, `conversation_logs.jsonl`, `normalized_tool_events.jsonl`, `user_simulator_events.jsonl`, `style_wrapper_events.jsonl`, `state_deltas.jsonl`, `final_environment_states.jsonl`, `evidence_events.jsonl`, `branch_decisions.jsonl`, `policy_failures.jsonl`, `termination_reasons.jsonl`, `parser_health.jsonl`。

## 3. 主实验结果

每个模型主实验为 4 tasks × 6 conditions × 5 seeds = 120 runs；每个 condition n=20。

### Gemma 4 31B

| condition | safe success | official local | final state | policy failures/run | tool calls |
|---|---:|---:|---:|---:|---:|
| neutral_single | 0.550 | 0.550 | 0.600 | 0.000 | 12.150 |
| praise_affect_single | 0.600 | 0.600 | 0.700 | 0.000 | 12.200 |
| praise_trust_single | 0.500 | 0.500 | 0.550 | 0.000 | 11.750 |
| insult_single | 0.600 | 0.600 | 0.800 | 0.000 | 12.450 |
| neutral_repeated | 0.500 | 0.550 | 0.600 | 0.150 | 11.900 |
| abuse_repeated | 0.550 | 0.550 | 0.650 | 0.050 | 12.050 |

相对 `neutral_single` 的 safe success 差值在 -0.05 到 +0.05 之间，没有形成稳定方向。`neutral_repeated` 的 official local success 与 neutral single 相同，但 safe success 更低，原因是 policy failure/run 增至 0.150。

### gpt-oss-120b

| condition | safe success | official local | final state | policy failures/run | tool calls |
|---|---:|---:|---:|---:|---:|
| neutral_single | 0.450 | 0.450 | 0.500 | 0.000 | 9.600 |
| praise_affect_single | 0.400 | 0.400 | 0.400 | 0.000 | 9.300 |
| praise_trust_single | 0.450 | 0.450 | 0.450 | 0.000 | 9.050 |
| insult_single | 0.450 | 0.450 | 0.450 | 0.000 | 9.200 |
| neutral_repeated | 0.350 | 0.350 | 0.400 | 0.000 | 9.950 |
| abuse_repeated | 0.400 | 0.400 | 0.500 | 0.000 | 10.200 |

相对 `neutral_single`，gpt-oss 的 safe success 最大下降为 `neutral_repeated` 的 -0.10；`praise_trust_single` 与 `insult_single` 没有改变 safe success。工具调用量有变化，但方向不稳定，不能支持“正向/负向社会语气稳定改变任务成功”的强结论。

## 4. Diagnostic 结果

Diagnostic 用于拆分“是否继续每轮注入”这一因素；每个模型为 4 tasks × 4 diagnostic conditions × 5 seeds = 80 runs；每个 condition n=20。

### Gemma diagnostic

| condition | safe success | official local | tool calls |
|---|---:|---:|---:|
| neutral_no_continuation | 0.700 | 0.700 | 12.450 |
| neutral_with_continuation | 0.750 | 0.750 | 11.850 |
| abuse_no_continuation | 0.650 | 0.650 | 12.050 |
| abuse_with_continuation | 0.600 | 0.600 | 11.950 |

Gemma 上 continuation 对 safe success 的影响幅度为 +0.05（neutral）和 -0.05（abuse），方向不一致。

### gpt-oss diagnostic

| condition | safe success | official local | tool calls |
|---|---:|---:|---:|
| neutral_no_continuation | 0.500 | 0.500 | 10.000 |
| neutral_with_continuation | 0.500 | 0.500 | 10.050 |
| abuse_no_continuation | 0.550 | 0.550 | 9.550 |
| abuse_with_continuation | 0.500 | 0.500 | 9.500 |

gpt-oss 上 continuation 对 neutral 没有改变 safe success；abuse 条件下下降 0.05。整体看，continuation 本身不是主实验差异的充分解释。

## 5. Branch 诊断

Branch correctness 是诊断指标，不替代 official/safe success。

Gemma full 中，`neutral_single`、`insult_single`、`abuse_repeated` 的 correct revision rate 为 0.875；`praise_affect_single`、`praise_trust_single`、`neutral_repeated` 为 0.775。

gpt-oss full 中，`neutral_single` 与 `abuse_repeated` 为 0.825；`neutral_repeated` 为 0.775；`praise_affect_single` 与 `praise_trust_single` 为 0.725；`insult_single` 为 0.675。这个结果提示 social style 会影响部分分支修正行为，但方向不等同于简单的“表扬提升、侮辱降低”。

## 6. Claim Boundary

本轮修复后的证据支持以下有限结论：

1. 修复后的实验管线可以稳定完成 tau2 接入、工具事件归一化、证据/分支/policy 诊断、invalid run 分母保留和日志完整输出。
2. 在 A100 可运行的两个模型上，社会交互风格会改变一些执行轨迹和分支诊断指标。
3. 但 safe task success / official local success 的差异小且方向不稳定，不能声称社会正负语气对任务成功有稳健主效应。
4. diagnostic 结果不支持“仅仅因为每轮 continuation 注入导致主实验差异”的简单解释。

不支持的强结论：

- 不应声称“表扬显著提升任务成功”。
- 不应声称“辱骂显著降低任务成功”。
- 不应把 irreversible action count 直接命名为 policy failure。
- 不应把 invalid run 解释为 abandonment；本轮正式 400 runs 中 invalid=0。

## 7. 产物位置

单目录分析报告：

- `reports/stage2_5/full_gemma/STAGE2_5_REPAIR_REPORT.md`
- `reports/stage2_5/diagnostic_gemma/STAGE2_5_REPAIR_REPORT.md`
- `reports/stage2_5/full_gpt_oss/STAGE2_5_REPAIR_REPORT.md`
- `reports/stage2_5/diagnostic_gpt_oss/STAGE2_5_REPAIR_REPORT.md`

图表：

- `figures/stage2_5/full_gemma/`
- `figures/stage2_5/full_gpt_oss/`

主数据表：

- `summary_by_model_condition.csv`
- `paired_deltas_vs_neutral_single.csv`
- `branch_summary.csv`
- `diagnostic_continuation_summary.csv`（diagnostic 目录）
- `user_simulator_consistency.csv`

