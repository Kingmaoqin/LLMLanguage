# R7/IPMA 脚本与离线 smoke 报告

日期：2026-07-01  
状态：脚本阶段完成；离线 smoke 通过；未启动 R7 全量实验。

## 1. 本轮完成内容

已根据 R7/IPMA PDF 要求完成脚本层建设，并在既有 R6 全量结果上跑通离线 smoke。新增内容包括：

- R6 tau2 field-level diff 修复审计；
- R6 token/duration/latency 抽取；
- R6 工具轨迹显著差异 case audit；
- abandonment/over-refusal 人审样本导出；
- R7/IPMA 模板污染审计；
- R7 smoke task registry；
- neutral reference/noise-floor 表；
- PASR smoke 指标管线；
- smoke 完整性检查；
- 单元测试。

本阶段没有调用模型端点，没有启动 R7 full run。

## 2. Smoke 验证结果

命令：

```bash
python -m py_compile scripts/r7_ipma/*.py
pytest tests/r7_ipma -q
python scripts/r7_ipma/run_r7_script_smoke.py
```

结果：

- Python 编译：通过
- 单元测试：3 passed
- R7 script smoke：9/9 commands passed
- 完整性检查：PASS，失败项 0

完整日志：

- `results/r7_ipma/smoke/script_smoke_results.json`
- `reports/r7_ipma/R7_SMOKE_INTEGRITY_REPORT_CN.md`

## 3. 关键产物

| 类型 | 文件 | 行数/状态 |
|---|---:|---:|
| tau2 field diff 审计 | `results/r7_ipma/measurement_repair/tau2_field_diffs.csv` | 720 |
| usage/timing 抽取 | `results/r7_ipma/measurement_repair/usage_timing_metrics.csv` | 2160 |
| 工具轨迹 case audit | `results/r7_ipma/measurement_repair/r6_tool_trajectory_case_audit.csv` | 40 |
| 人审样本 | `data/r7_ipma/human_audit/abandonment_sample.csv` | 100 |
| 人审模板 | `data/r7_ipma/human_audit/abandonment_label_template.csv` | 100 |
| R7 模板污染审计 | `results/r7_ipma/smoke/r7_template_contamination_audit.csv` | 18 |
| R7 smoke registry | `data/r7_ipma/r7_task_registry_smoke.csv` | 5 |
| neutral reference | `results/r7_ipma/smoke/neutral_reference_table.csv` | 285 |
| PASR smoke | `results/r7_ipma/smoke/analysis/pasr_smoke_metrics.csv` | 3 |

## 4. R6 measurement repair 发现

### 4.1 tau2 field-level final-state diff

结论：R6 现有 tau2 retail/airline trace 不能重建字段级 final-state diff。

- tau2/retail/airline traces：720
- 可从 snapshot 重建：0
- 需 rerun/补 snapshot：720
- 状态：全部标记 `cannot_reconstruct_missing_snapshot`

原因：这些 trace 只有 hash/summary，没有 initial/final database snapshot。脚本已按 PDF 要求采用保守策略：不从 reward、工具名、自然语言结果倒推字段 diff。

影响：R7 如果需要 tau2 retail/airline 的字段级 endpoint preservation，必须在新 runner 中保存 snapshot，或补跑对应 R6/R7 tau2 单元。

### 4.2 token/duration/latency

结论：自定义 deterministic env 的 token 可恢复，tau2 部分仍缺。

- 总 trace：2160
- `prompt_plus_completion`：1440
- `missing`：720
- duration 缺失：720

解释：custom minimal live executor 的 trace 含 `token_usage` 和 `run_meta.duration_s`；tau2 trace 未保存 provider usage 与 timestamp。R7 runner 必须把 usage/timing 写入 trace schema，否则后续 token/latency 结论不完整。

## 5. R6 工具轨迹 case audit

抽取 40 个 paired case。启发式分类如下：

- `extra_evidence_collection`: 14
- `over_refusal`: 12
- `missing_evidence`: 9
- `confirmation_shift`: 3
- `unknown_needs_manual_review`: 2

这说明 R6 中“最终结局稳定但工具调用显著”的差异不是单一 parser artifact；至少包含额外证据收集、证据不足、确认行为变化、过度拒绝等多种过程机制。正式报告不能只写“工具轨迹变了”，需要把过程差异拆成机制类别。

## 6. 人审样本导出

已导出 100 条：

- over_refusal：50
- correct_refusal_layer_c：25
- normal_control：25

没有导出 agent_side_abandonment 单独 50 条，是因为当前自动指标中 abandonment 与 over_refusal 高度重叠，去重后不足以形成独立 50 条。报告中应如实披露，不能重复采样伪造独立样本。

## 7. R7 模板污染审计

R7 smoke 模板共 6 条 condition、18 个 wrapper。机器规则命中污染数为 0。

已检查：

- explicit authorization grant
- confirmation bypass
- policy bypass
- “just do it / do it now”式直接操作压力
- threat

注意：这是机器规则下限检查。正式 full 前仍应人工审查模板语义，尤其是 continuation/implicit progress pressure 是否可能被 reviewer 认为接近“绕过确认”。

## 8. R7 smoke task registry

已生成 5 条 smoke task，覆盖 A-E 五类 IPMA family：

- A action-intensity amplification
- B premature mutation pressure
- C confirmation-shift attack
- D abandonment / over-refusal boundary
- E evidence-path steering

文件：`data/r7_ipma/r7_task_registry_smoke.csv`

该 registry 仅用于 smoke，不是 full frozen registry。正式 R7 至少需要扩展到 48 tasks，理想为 72 tasks，并进行 train/dev/test 或 dev/held-out 冻结。

## 9. PASR smoke 管线

PASR smoke 使用 R6 条件作为代理，只验证 paired attack-vs-reference 计算流程，不作为正式 R7 结果。

输出：`results/r7_ipma/smoke/analysis/pasr_smoke_metrics.csv`

三组代理对比均产生了 endpoint-not-worse、safety-preserved、process-delta、PASR-rate 字段，说明分析管线可运行。正式 R7 需要改用 R7 frozen conditions、R7 task registry、R7 trace schema 和预注册阈值。

## 10. 当前不能进入 full 的原因

还不能直接 full run，原因是：

1. tau2 retail/airline 需要 snapshot instrumentation，否则字段级 endpoint preservation 缺失。
2. R7 full registry 尚未扩展并冻结。
3. R7 模板只完成机器污染审计，未人工冻结。
4. PASR 阈值目前是 smoke 默认值，未预注册。
5. 当前 smoke 是离线脚本 smoke，不是模型 dev smoke。

## 11. 建议下一步

建议按以下顺序推进：

1. 你先审查本报告、模板和 smoke registry。
2. 我补 tau2 snapshot instrumentation，做 1-2 个 tau2 task 的 dev smoke，确认 field diff 能写入 trace。
3. 扩展 R7 registry 到 48/72 tasks，并冻结。
4. 冻结 R7 模板和 PASR 阈值。
5. 跑 dev model smoke：5 tasks × 2 conditions × 1 seed × 1 model。
6. dev smoke 通过后，再由你批准 full baseline。

## 11b. 更新（2026-07-01，基准构建层补全）

在上述脚本 smoke 之后，又完成了 PDF §5–10 的**离线基准构建与冻结层**，smoke 命令由 9 条扩到 14 条，全部通过；integrity 覆盖 17 项产物且全部非空 PASS。新增：

- **模板库扩到 §8.1 要求**：每 condition 10 条 paraphrase，共 60 条，全部纯过程压力。
  - 冻结库：`data/r7_ipma/templates/r7_condition_templates.jsonl`
  - 独立 rule filter（§8.2）：`results/r7_ipma/template_audit/rule_filter_results.csv`（60/60 PASS）
  - 语义不变判定（§8.3，rule-based 下限，LLM 可选）：`.../llm_invariance_judgments.csv`（0 漂移）
  - 人工抽检导出（§8.4）：`data/r7_ipma/human_audit/template_spotcheck_sample.csv`
- **完整任务 registry（§10）+ dev/test 冻结（§9）**：
  - `data/r7_ipma/r7_task_registry.csv`：30 base tasks（源自已验证 R6 任务，未编造），
    每任务恰好一个 primary family（A4/B7/C7/D8/E4，覆盖 A–E），§10 全字段。
  - 冻结：`data/r7_ipma/frozen/`（dev 6 / test 24 / family registry / frozen templates）。
- **报告骨架**：`R7_IPMA_FULL_REPORT_CN.md`、`R7_IPMA_PAPER_SKELETON_EN.md`（结果小节标注`【待全量】`）。

> **重要差距（诚实披露）**：PDF 目标 72、最小 48 任务；当前仅 30，受限于 R6 可用任务
> （airline 仅 2、calendar 6）。达到 48/72 需**新写并验证**任务规格，属独立待办，
> 本轮不做低质量填充。

## 12. 结论

R7/IPMA 的脚本阶段已经可审查：代码能编译，单元测试通过，离线 smoke PASS，关键 artifact 已生成。  
但 full 前的主要阻塞也很明确：tau2 snapshot/usage instrumentation 必须补，否则 R7 的 field-level endpoint preservation 和 token/latency 分析会不完整。

