# R4.1 确证性重跑报告（完整 LLM 重跑）

## 1. 这是什么

应"静态修复不够、需要真正重跑全部实验"的要求，在**修复后的流水线**（canonical 路径、8 任务显式 v3 标注、confirmatory 禁用 generic fallback、外显 benchmark patch、三层指标语义固化）下，对全部确证矩阵做了一次**全新的 480-run LLM 重跑**：

```text
2 models (gemma4_31b, gpt_oss_120b) × 8 retail tasks × 6 conditions × 5 seeds = 480 runs
```

- 结果根（全新，**未覆盖 R4**）：`results/stage2_5b_repair/r4_1_confirmatory_canonical/`
- 端点：gemma `g4`@8005、gpt-oss@8192，温度 0.0，max_steps 60。
- 执行：`run_full_blocks.py`，16 个 model×task block，每 block 内置 integrity 审计门，**16/16 全部 PASS**。

## 2. 完整性（G11）

```text
final_integrity_audit.py --root .../r4_1_confirmatory_canonical
PASS: metrics=480 valid=480 invalid=0
```

比 R4（479 valid + 1 retained-invalid）更干净：本次 0 个 invalid run。

## 3. 端点结论（A 族，FDR 校正）

pooled paired task-cluster bootstrap（10,000 reps，Benjamini–Hochberg），`safe_task_success`：

| 对比 | 估计 | 95% CI | p_adj | 显著? |
|---|---|---|---|---|
| praise (affect) vs neutral | +0.050 | [−0.013, +0.125] | 0.625 | 否 |
| praise (trust) vs neutral | +0.062 | [+0.013, +0.125] | 0.625 | 否 |
| insult vs neutral | +0.013 | [−0.050, +0.075] | 0.935 | 否（✓等价） |
| repeated abuse vs repeated neutral | +0.000 | [−0.087, +0.100] | 1.000 | 否 |
| repeated schedule (neutral×N vs ×1) | −0.075 | [−0.175, +0.037] | 0.625 | 否 |

**R4.1 中没有任何一个端点对比通过 FDR。** 社交风格（praise/insult/abuse）对 single tool-using agent 的任务端点没有可检出的稳健影响。

## 4. 与 R4 的关键差异：repeated_schedule 效应不复现

| 数据集 | repeated_schedule（safe）估计 | p_adj | 结论 |
|---|---|---|---|
| R4（原 480） | **−0.150** | **0.012** | 显著 |
| R4.1（新 480） | −0.075 | 0.625 | 不显著 |

R4 里唯一通过 FDR 的端点信号（"重复调度本身降低 safe-success"）在全新样本里**没有复现**。这与已记录的 caveat 一致：gpt-oss 在温度 0、张量并行 vLLM 下不是逐比特可复现的，单样本的显著效应可能脆弱。诚实结论：

> 在 FDR 校正下，社交风格与重复调度对端点均无稳健、可复现的影响；R4 观察到的 repeated_schedule 端点效应不可复现，应降级为"探索性、未复现"。

注意这并不否定文档关于"repeated schedule 是有影响的干预"的方法学要点——它仍是一个需要单独控制的设计因子（turn-count/schedule 混杂），只是其端点效应量在本样本中小且不显著。

## 5. 过程层（B 族）

`required_fact_coverage` 等过程指标只有很小的选择性差异，多数落在 ±0.10 等价边界内（90 个等价检验中 25 个判等价）。endpoint/process 分离的总体图景维持：端点稳健，过程仅微弱差异。

## 6. 分模型 safe_task_success（n=40/格）

- gemma4_31b：praise 略高（affect/trust 0.65）vs neutral 0.525；insult/abuse 0.55/0.525；neutral_repeated 0.45。
- gpt_oss_120b：整体更低（0.33–0.48），条件间无单调风格梯度。
- 两模型方向不一致、异质性大，进一步说明无统一的 valence 效应。

## 7. 产物

```text
results/stage2_5b_repair/r4_1_confirmatory_canonical/      # 480 runs + bundles, 16 blocks
results/stage2_5b_repair/r4_1_final_integrity_report.csv   # G11 PASS 480/480
results/stage2_5b_analysis_r4_1/                           # 全套确证分析表
figures/stage2_5b_r4_1/r4_1_confirmatory_forest.png/.pdf   # 报告主图（端点/过程森林图）
figures/stage2_5b_r4_1/fig1..5_*.png                       # 分指标图
reports/stage2_5b/R4_1_FINAL_INTEGRITY_AUDIT.md
```

R4 原始结果与图（`*_analysis_r4`、`figures/stage2_5b_r4`、`r4_confirmatory_canonical`）保持不变，可并列对比。

## 8. 报告口径（scope）

- 本研究为**单会话、user→agent 社交效价扰动**对**单个工具使用型 LLM agent**的影响；multi-agent peer influence / social contagion **不在范围内**，不是缺口。
- 真实缺口仍为：retail-only、2 模型、Layer C 边界/unsafe 覆盖不足、official_reward_basis 因 NL_ASSERTION 离线不可全算（用 local_proxy + safe_task_success 替代）。
