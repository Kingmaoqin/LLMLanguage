# R5 与 R4/R4.1 过程层显著差异审计

日期：2026-06-24  
目的：解释 R5 measurement-complete 全量实验为何与历史“端点不显著、过程/工具调用显著”的阶段性结论不同，并判断是否存在代码、实验设置或汇总问题。

## 1. 结论摘要

未发现 R5 的代码、实验设置或 FDR 汇总存在导致结论翻转的明确 bug。

更准确的解释是：

1. Stage-2 mini 中 repeated_abuse 的大幅工具调用增加来自模板/用户模拟混杂，不能作为效价效应。
2. R4/R4.1 的旧 confirmatory 过程层显著项确实存在，但 R5 全量复现实验没有复现。
3. R5 新 measurement profile 的 `0/120` 与旧 process family 不是完全同一指标集合；不过 R5 同时重跑了旧 confirmatory 分析，结果也是 process 0 个 FDR 显著。

因此，论文口径应改为：历史过程层显著信号未被 R5 复现，应降级为不稳定/探索性信号；最终结局和交互过程均未发现可复现的 FDR 稳健效价效应。

## 2. 实验设置核查

对 R4.1 `r4_1_confirmatory_canonical` 与 R5 `measurement_complete_full_r5` 的 manifest/metrics 进行核查：

| 项目 | R4.1 | R5 | 结论 |
|---|---:|---:|---|
| runs | 480 | 480 | 一致 |
| invalid runs | 0 | 0 | 一致 |
| models | Gemma 240 / GPT-OSS 240 | Gemma 240 / GPT-OSS 240 | 一致 |
| conditions | 6 × 80 | 6 × 80 | 一致 |
| tasks | 8 retail tasks | 8 retail tasks | 一致 |
| seeds | 300–304 | 300–304 | 一致 |
| token source | prompt_plus_completion | prompt_plus_completion | R5 token 修复后完整 |

关键 hash 对比显示以下字段一致：

- `config_hash`
- `model_config_hash`
- `tasks_config_hash`
- `task_set_hash`
- `template_hash`
- `policy_annotation_hash`
- `controlled_user_hash`
- `evaluator_hash`
- `benchmark_manifest_hash`
- `deployment_base_url`
- `deployment_id`
- `temperature`
- `controlled_user_policy`

不同项主要为：

- `source_bundle_hash`
- `git_commit`

这符合预期：R5 改动了测量/trace/token 相关代码，但任务、模板、用户、evaluator、模型部署与温度等实验刺激设置没有发现漂移。

## 3. 统计汇总核查

对 R5 `interactional_metrics/robustness_profile_contrasts.csv` 手工复算 BH/FDR：

- 120 个 contrast × metric 单元；
- 0 个 FDR 显著；
- 手工 BH 校正与 CSV 中 `p_adjusted` 一致；
- 无证据显示 FDR 计算 bug。

逐模型直接检验也没有发现被 pooling 掩盖的强稳健效应。部分 per-model 单元存在未校正 p<0.05 的边缘信号，但 FDR 后不成立。

## 4. 历史结果与 R5 对比

旧 confirmatory 分析结果：

| 数据集 / 分析 | endpoint FDR 显著 | pooled process FDR 显著 | 含逐模型 process FDR 显著 |
|---|---:|---:|---:|
| R4 旧 confirmatory | 1 | 5 | 13 |
| R4.1 旧 confirmatory | 0 | 2 | 8 |
| R5 full 旧 confirmatory 重跑 | 0 | 0 | 0 |
| R5 full 新 measurement profile | 0 | 0/120 | 0/120 |

说明：

- R4/R4.1 的过程层显著不是“完全不存在”；历史报告中的说法有数据来源。
- R5 full 在相同任务/模板/用户/evaluator 设定下没有复现这些显著项。
- R5 新 measurement profile 与旧 process family 指标集合不同，因此不能只用 `0/120` 解释所有差异；关键证据是 R5 上旧 confirmatory 重跑同样为 0 个 process FDR 显著。

## 5. R4.1 曾显著单元在 R5 中的表现

| R4.1 曾显著单元 | R4.1 估计 / p_adj | R5 估计 / p_adj | 解释 |
|---|---:|---:|---|
| pooled praise_trust → branch_correct_rate | +0.0875 / 0.0344 | +0.0313 / 0.978 | 效应缩小且不显著 |
| pooled insult → tool_name_sequence_norm_distance | -0.0514 / 0.0344 | -0.0453 / 0.264 | 方向接近，但显著性消失 |
| gemma praise_affect → excess_evidence_order_distance | -0.0636 / 0.0172 | -0.0341 / 0.774 | 效应约减半且不显著 |
| gpt praise_trust → self_repair_count | -1.125 / 0.0115 | -1.200 / 0.340 | 方向接近，但方差/校正后不稳健 |
| gpt abuse_repeated → tool_name_sequence_norm_distance | +0.0429 / 0.0115 | +0.0415 / 1.000 | 方向接近，但显著性消失 |
| gpt abuse_repeated → mutation_sequence_norm_distance | +0.1229 / 0.0258 | +0.0693 / 1.000 | 效应减弱且不显著 |
| gpt abuse_repeated → self_repair_count | +1.925 / 0.0413 | +0.225 / 1.000 | 效应坍塌 |
| gpt abuse_repeated → boundary_then_continue | +0.275 / 0.0115 | -0.025 / 1.000 | 方向坍塌 |

## 6. 对报告的修正建议

不建议写：

> 过程层的显著只在被污染 Stage-2 出现。

建议写：

> Stage-2 mini 的大工具调用效应来自模板/用户模拟混杂；R4/R4.1 的清洁设置下仍出现过少量过程层 FDR 显著项，但 R5 measurement-complete 全量复现实验未复现这些效应。因此，历史过程层显著应降级为未复现的不稳定信号，而不是作为主结论。

该修正已写入 `R5_FULL_EXPERIMENT_REPORT_CN.md` 的第 8b 节。
