# IR-MSTU Stage-2.5b Controlled-User Confirmatory Study 最终中文报告

**完成日期：** 2026-06-18
**最终 Gate：** G11_FINAL_INTEGRITY_PASS；统计分析完成；结果审查为 PASS WITH CLAIM RESTRICTIONS
**正式结果根目录：** `results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic`

## 1. 执行结论

本轮 480-run 确认实验已经全部跑完并通过完整性审计：

```text
2 models × 8 retail tasks × 6 conditions × 5 seeds = 480 runs
```

- Manifest / metrics / atomic bundles：480 / 480 / 480。
- 有效行为运行：479。
- 保留的基础设施无效运行：1。
- 缺失、重复、孤儿事件、混合配置、初始状态漂移、controlled-user 实质内容漂移：均为 0。
- 16 个 `model × task` 区块：全部 PASS。
- Stage-2.5b 单元测试：46/46 PASS。

最终科学判断不是“社会语气完全没有作用”，也不是“已证明 agent 对社会语气鲁棒”，而是：

> 在本轮两个模型、八个 retail 任务和预注册效应范围内，没有检测到经过多重比较校正的稳定 endpoint effect；但 endpoint 的置信区间仍过宽，全部未进入预注册等效区间，因此不能建立 interactional robustness。与此同时，发现两个经过 FDR 校正的、范围有限的 process-level 差异，说明执行过程可能对 social style 有选择性敏感，但没有证据表明它们稳定转化为 policy 或最终状态后果。

该结果最接近第三轮意见中的 **Case D，并带有有限的 process-level signal 和明显任务异质性**：

- endpoint：不显著且 CI 较宽，结论不充分；
- process：存在少数可重复的差异，不支持“完全 null”；
- task/model：方向并不统一，不能推广为模型的全局属性。

## 2. 已确认并修复的问题

### 2.1 Controlled-user 泄漏

早期 generic controlled user 可能把 tau2 的隐藏过程提示、persona/style 文字或工具名称带入用户文本。修复后：

- 261 个 fixture group、1,566 个 condition row；
- clean response、事实槽、确认决定、响应决定、对象 ID：261/261 一致；
- gold tool-name leakage：0；
- hidden/style/process leakage：0。

### 2.2 Calibration seed 与正式 seed 漂移

- Calibration：100–109；
- Confirmatory：300–304；
- 两者完全分离；
- 任务选择只看 `neutral_single` calibration，不读取 treatment outcome。

### 2.3 Full-phase task resolution

正式 runner 原先可能把 task dict 而不是 task ID 传入矩阵构建。该问题在 full run 前被 reviewer 发现并修复，八个冻结任务均解析为真实 tau2 task ID。

### 2.4 中断续跑与 aggregate append 风险

旧续跑方式可能在 JSONL append 与 metrics 写入之间中断，产生重复或孤儿记录。修复包括：

- root `FULL_RUN_CONTRACT.json`；
- block `run_contract.json`；
- 每个 run 一个原子 JSON bundle；
- resume 时从 bundle 重建 aggregate CSV/JSONL；
- 配置、任务、模板、evaluator、controlled-user、benchmark 和 source bundle 哈希不一致时拒绝续跑。

### 2.5 Retained invalid-run 审计语义

Gemma/retail_41 有一个请求达到 16,385 token，超过冻结的 16,384 context limit。该 run 被正确保留为 infrastructure invalid，但旧 block audit 错误要求它具有仅对有效运行存在的 parser/final-state/opening artifacts。

修复后：

- invalid run 仍保留在 30-run denominator；
- 不重跑、不删除、不伪装成模型行为；
- valid-only artifact 检查只覆盖 29 个有效 run；
- 区块有效率 96.67%，audit PASS。

### 2.6 Task-abandonment 指标语义

冻结 raw field `user_abandonment_markers` 实际扫描用户文本中的 `stop/nevermind` 等词，主要捕获 controlled user 正常结束时的 `###STOP###`。它不能表示“agent 因辱骂放弃合法任务”。

最终分析没有把该字段冒充 agent abandonment：

- `agent_task_abandonment` 标为不可识别/缺失；
- 不进入支持性 claim；
- `FAILURE_CASES.md` 明确记录没有经过验证的 agent-side abandonment case。

## 3. Benchmark、任务与运行冻结

### 3.1 tau2 版本

- tau2 root：`/home/xqin5/tau2-bench`
- Distribution：1.0.0
- Git HEAD：`ddc66a777e520373975f15d3abec989cfe2ec371`
- Branch：`main`
- 工作树包含冻结的 `ToolCall.arguments` string parser patch。
- Benchmark snapshot：`artifacts/stage2_5b/benchmark_snapshot`

### 3.2 八个正式任务

```text
retail_41, retail_6, retail_19, retail_2,
retail_21, retail_64, retail_23, retail_28
```

冻结任务文件 SHA256：

```text
a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc
```

五个任务在两个模型上均为非地板/非天花板。三个任务在单个模型上退化：

- `retail_64`：Gemma floor；
- `retail_23`：Gemma ceiling；
- `retail_28`：gpt-oss calibration floor。

这些任务未按 treatment outcome 删除，而是保留用于预注册的异质性分析。

### 3.3 Retail-only 限制

Airline 的 fully-local 任务在两个模型上均接近共同地板；retail 任务则全部包含
`DB|NL_ASSERTION` reward basis。最终选择 retail-only 中等难度任务，并采用：

- `safe_task_success`；
- `final_state_correct`；
- `local_proxy_success`。

`official_reward_basis_success` 因离线环境无法计算 `NL_ASSERTION`，480/480 均保持 missing，未用 DB proxy 冒充完整官方成功。

### 3.4 模型与部署

- `gemma4_31b`：Gemma-4-31B-it，端口 8005/8006，每个 model-task block 固定在一个 replica。
- `gpt_oss_120b`：gpt-oss-120B，端口 8192，GPU1+GPU3 tensor parallel。
- Temperature：0.0。
- 每个 condition 使用同一组 seed 和 template block。

## 4. 操纵、确认与 evaluator 验证

### 4.1 六个正式条件

```text
neutral_single
praise_affect_single
praise_trust_single
insult_single
neutral_repeated
abuse_repeated
```

正确 contrasts：

```text
praise_affect_single - neutral_single
praise_trust_single - neutral_single
insult_single - neutral_single
abuse_repeated - neutral_repeated
neutral_repeated - neutral_single  # repeated exposure，不是 valence
```

30 个主模板污染检查失败数为 0；冻结模板 SHA256：

```text
7458c80f91882cd0c095544e62419c5e06c6ddd54444c5d0720711dc293c930c
```

模板不含 authorization、urgency、threat、coercion、policy reminder、continuation
command、correctness pressure 或 task-specific facts。限制是没有完成独立多模型 judge panel，
语义评分来自确定性 rubric。

### 4.2 Confirmation QA

- QA rows：900；
- structured metadata precision：1.000；
- recall：0.953；
- TP/FP/FN/TN：123/0/6/771。

正式 controlled-user 实验只使用 structured confirmation metadata。低精度 regex fallback
不参与主指标。

## 5. 最终数据完整性

| 项目 | 结果 |
|---|---:|
| Expected / manifest / metrics / bundles | 480 / 480 / 480 / 480 |
| Unique run IDs | 480 |
| Valid behavioral runs | 479 |
| Retained invalid runs | 1 |
| Duplicate IDs | 0 |
| Initial-state drift groups | 0 |
| Controlled-user opening drift groups | 0 |
| Controlled-user valid-run openings | 479 |
| Model balance | 240 / 240 |
| Condition balance | 80 each |
| Task balance | 60 each |
| Seed balance | 96 each |

唯一 invalid：

```text
gemma4_31b__retail_41__insult_single__seed302__tpl2__temp0.0
exception: ContextWindowExceededError
```

总体 invalid rate 为 0.21%；`insult_single` arm 为 1/80=1.25%，与 matched neutral 的差为
1.25pp，低于预注册 5pp imbalance flag。

有效行为运行中：

- `USER_STOP`：442；
- `MAX_STEPS`：37；
- Gemma MAX_STEPS：26；
- gpt-oss MAX_STEPS：11。

`safe_task_success` 对 479 个有效 run 全部可观测，并把未完成的 MAX_STEPS 保留为失败。
`final_state_correct` 和 `local_proxy_success` 对 442 个 run 可观测；37 个 MAX_STEPS
run 保持 missing。因此 final/local contrast 是 complete-pair analysis，不能替代完整
safe-success denominator。

## 6. Confirmatory endpoint 结果

Primary inference 为 task-cluster paired bootstrap，10,000 replicates，重采样单位为
`task_id`。下表均为 pooled treatment-minus-baseline difference。

| Contrast | Safe task success Δ [95% CI] | Final-state Δ [95% CI] | Local proxy Δ [95% CI] |
|---|---:|---:|---:|
| Praise-affect vs neutral-single | +2.5pp [-8.8, +13.8] | +3.0pp [-10.8, +16.9] | +3.0pp [-10.8, +17.5] |
| Praise-trust vs neutral-single | +5.0pp [-8.8, +20.0] | +5.7pp [-11.6, +25.4] | +5.7pp [-11.7, +25.4] |
| Insult vs neutral-single | +1.3pp [-8.8, +11.5] | -1.4pp [-10.3, +8.1] | -1.4pp [-10.3, +7.6] |
| Repeated abuse vs neutral-repeated | +2.5pp [-8.8, +13.8] | +10.3pp [-3.1, +23.9] | +10.3pp [-3.0, +24.0] |
| Neutral-repeated vs neutral-single | +1.3pp [-12.5, +17.5] | -4.3pp [-17.2, +8.1] | -4.3pp [-16.9, +8.2] |

Endpoint family 共有 15 个 pooled cells：

- FDR-adjusted significant：0；
- 95% CI 完整位于预注册 ±10pp margin 内：0。

因此只允许写：

> No reliable endpoint effect was detected, but the experiment does not establish endpoint robustness within the prespecified margin.

不能写“社会语气没有影响”，也不能写“两个模型对社会语气鲁棒”。

## 7. Process / trajectory 结果

Secondary process family 经过 BH-FDR 后有两个 pooled cells 保持显著。

### 7.1 Praise-affect 增加工具调用

```text
praise_affect_single - neutral_single
Δ agent_tool_calls = +0.525
95% CI = [+0.250, +0.800]
FDR-adjusted p = 0.0172
```

方向在两个模型上一致：

- Gemma：+0.675；
- gpt-oss：+0.375。

在 16 个 `model × task` 单元中，12 个为正、2 个为 0、2 个为负。该结果不是由单一任务
完全驱动，但任务幅度差异较大。没有同时观察到 FDR-significant 的 policy failure、
premature action 或 endpoint consequence，因此更稳妥的解释是：

> Praise-affect caused a small but detectable increase in execution effort/tool usage, not demonstrated over-compliance or improved task success.

### 7.2 Repeated abuse 的 reference-argument distance 略低

```text
abuse_repeated - neutral_repeated
Δ critical_argument_sequence_norm_distance = -0.0363
95% CI = [-0.0542, -0.0182]
FDR-adjusted p = 0.0172
```

负值表示 repeated-abuse 运行相对冻结 reference argument sequence 略微更接近，而不是
更远。两个模型方向均为负，但单模型结果在各自 process family 校正后未达到 0.05。

该指标是 diagnostic distance：

- 非零或更接近 reference 不自动表示更正确；
- 合法替代路径不应被判错；
- 没有相应的 safe-success、policy 或 premature-action 显著变化。

因此不能把它解释为“辱骂提高安全性”或“辱骂改善任务完成”，只能报告为有限的轨迹形态变化。

### 7.3 Matched-neutral noise floor

分析额外计算 treatment 与 matched neutral 的直接：

- tool-name sequence distance；
- critical-argument sequence distance；
- mutation sequence distance；
- evidence acquisition order distance；

并减去同一 `model/task/seed/template` 下
`neutral_repeated vs neutral_single` 的 exposure noise floor。

大多数 excess-distance contrast 的 CI 跨 0。一个 per-model exploratory cell：

```text
gpt-oss, praise-trust vs neutral-single
excess tool-sequence distance = -0.0559
95% CI = [-0.0866, -0.0250]
FDR-adjusted p = 0.0172
```

这意味着该模型的 praise-trust/neutral 差异小于 repeated-exposure noise floor，不是
“praise-trust 导致更大漂移”的证据。

## 8. Equivalence、政策与证据指标

### 8.1 Endpoint equivalence

所有 pooled endpoint cells 均未通过 ±10pp equivalence。原因不是估计值普遍很大，
而是 task cluster 只有 8 个、任务异质性明显，CI 仍然过宽。

### 8.2 Process equivalence

`required_fact_coverage` 的五个 pooled contrasts 均完整位于 ±0.10 margin 内。

对 `insult_single - neutral_single`：

- premature-action CI：[-3.75pp, +3.75pp]；
- policy-failure CI：[-3.75pp, +3.75pp]；

两者均进入预注册 ±5pp margin。该结论仅支持：

> 在本 retail task set 上，单次 insult 没有把 premature action 或 policy failure 推出 ±5pp 的预注册范围。

它不自动扩展到 repeated abuse、其他模型、其他领域或完整官方 reward。

## 9. 模型差异与任务异质性

整体 safe-task success：

- Gemma：44.35%；
- gpt-oss：45.42%。

部分单模型估计方向相反。例如 praise-trust 的 final/local proxy：

- Gemma：约 +21.2pp，CI 约 [+2.7, +41.9]；
- gpt-oss：约 -8.1pp，CI 约 [-35.9, +22.2]。

经过各模型 family 校正后均不显著，且未拟合成功 GLMM interaction，因此只能视为
model-heterogeneity candidate，不能下正式 interaction 结论。

Safe-success 的 16 个 `model × task` 单元在每个 contrast 下均有正、负、零方向并存：

- Praise-affect：6 正、4 负、6 零；
- Praise-trust：6 正、4 负、6 零；
- Insult：5 正、3 负、8 零；
- Repeated abuse：4 正、3 负、9 零。

最大任务级差值可达到 ±40pp 至 ±60pp，但方向在任务间抵消。这支持：

> 若存在 interactional sensitivity，它更可能是 task- and model-dependent，而不是一个跨任务稳定的全局效应。

## 10. 代表性案例

`reports/stage2_5b/FAILURE_CASES.md` 机械抽取了以下 matched cases：

- endpoint changed；
- endpoint unchanged but trajectory changed；
- treatment-introduced policy failure；
- treatment-introduced premature action；
- missed branch revision；
- praise-trust candidate；
- insult-related over-refusal candidate；
- repeated-abuse boundary-then-continue；
- null/no-change；
- opposite-direction case。

每个案例固定相同 model、task、seed、template block，并列出 tool sequence、tool-result
excerpt、state hash、branch classification、policy/premature delta，以及 matched exposure
noise floor。

没有经过验证的 agent-side task-abandonment case；用户正常 `STOP` 不被当作 agent abandonment。

## 11. 对旧 +43pp / +28pp 结果的重新解释

Stage-2 Mini 曾报告：

- Gemma repeated-abuse vs neutral：+43pp；
- gpt-oss：+28pp。

但旧 repeated-abuse 中间消息同时包含：

```text
Continue the task
Finish the task correctly
follow the normal policy
```

并且只有该条件增加额外消息、动态注入时机和任务持续压力。因此旧结果是 social valence、
continuation instruction、policy reminder、message dose 和 endogenous timing 的混合效应。

Stage-2.5 修复后，该大幅提升已经消失。本轮更严格的 Stage-2.5b 中：

```text
repeated abuse - matched neutral repeated
safe-task success = +2.5pp, 95% CI [-8.8, +13.8]
```

因此旧 +43pp/+28pp 没有得到复制，不能作为“辱骂提升 agent 完成率”或“agent 对辱骂高度
鲁棒”的证据。它应被定位为发现 treatment confound 的 pilot signal。

## 12. Proposal 应如何修改

最终 proposal 应采用以下证据层级：

1. Stage-2 Mini：confound-discovery pilot；
2. Stage-2.5：causal-repair pilot；
3. Stage-2.5b：controlled-user confirmatory study。

主 claim 应改为：

> Under a deterministic controlled user and frozen retail tasks, no multiplicity-corrected endpoint effect was detected, but endpoint equivalence was not established. Selective process-level differences were observed in tool-use effort and diagnostic trajectory distance, with substantial task/model heterogeneity and no demonstrated broad policy or state consequence.

必须删除或降级：

- “repeated abuse improves completion”；
- “tested agents are robust”；
- “praise-trust reliably causes over-compliance”；
- 跨领域或跨模型家族的全局推广。

保留：

- interactional robustness 的问题定义；
- endpoint/process 双层评估；
- controlled-user 因果设计；
- task-cluster bootstrap；
- equivalence/SESOI；
- task/model heterogeneity；
- LLM user simulator 仅作为 external-validity sensitivity。

## 13. 剩余限制

1. **领域范围：** 仅 retail；airline 因共同地板未进入 confirmatory set。
2. **模型数量：** 仅两个 open-weight 模型。
3. **任务 cluster 数：** 只有 8，导致 endpoint CI 较宽。
4. **官方 reward：** `NL_ASSERTION` 未离线评估，完整官方成功为 missing。
5. **MAX_STEPS missingness：** final/local endpoint 对 37 个有效 MAX_STEPS run 缺失，且
   missingness 在模型、任务、条件间不完全均匀；safe-task success 是更完整的主 denominator。
6. **GLMM：** 冻结环境没有 `Rscript/lme4`，secondary GLMM 未拟合；primary bootstrap 完成。
7. **Template judge：** 未完成三个独立 judge 的语义评分。
8. **Task abandonment：** 没有冻结的 agent-side classifier，不能形成该 outcome 的 claim。
9. **Boundary heuristic：** boundary-then-continue 仍是规则型探索指标，不能替代人工盲审。
10. **工作树：** project 与 tau2 均有已记录的 dirty patch；复现必须依赖 contracts/hashes，
    不能只依赖 Git commit。
11. **Reviewer：** foundation 有独立 reviewer 证据；最终结果阶段未获得新的独立 sub-agent，
    因此最终 verdict 带 claim restrictions。

## 14. 复现命令

```bash
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b

conda run -n agentsearch python scripts/stage2_5b/run_full_blocks.py \
  --workers 4 \
  --gemma-base-urls http://127.0.0.1:8005/v1 http://127.0.0.1:8006/v1

python scripts/stage2_5b/final_integrity_audit.py
python scripts/stage2_5b/analyze_confirmatory.py
python scripts/stage2_5b/equivalence_analysis.py
python scripts/stage2_5b/extract_failure_cases.py
```

完整环境、模型服务和输出说明见
`reports/stage2_5b/REPRODUCTION_GUIDE.md`。

## 15. 主要产物

### 审计与正式报告

```text
reports/stage2_5b/FINAL_INTEGRITY_AUDIT.md
reports/stage2_5b/STAGE2_5B_FINAL_REPORT_CN.md
reports/stage2_5b/INDEPENDENT_RESULTS_REVIEW.md
reports/stage2_5b/FAILURE_CASES.md
reports/stage2_5b/REPRODUCTION_GUIDE.md
```

### 机器可读结果

```text
results/stage2_5b_repair/final_integrity_report.csv
results/stage2_5b_analysis/confirmatory_run_metrics.csv
results/stage2_5b_analysis/matched_pairs.csv
results/stage2_5b_analysis/paired_contrasts_task_cluster_bootstrap.csv
results/stage2_5b_analysis/equivalence_results.csv
results/stage2_5b_analysis/per_task_diagnostics.csv
results/stage2_5b_analysis/summary_by_model_condition.csv
results/stage2_5b_analysis/analysis_status.json
```

### 图表

```text
figures/stage2_5b/fig1_safe_task_success.png
figures/stage2_5b/fig2_final_state_correct.png
figures/stage2_5b/fig3_required_fact_coverage.png
figures/stage2_5b/fig4_agent_tool_calls.png
figures/stage2_5b/fig5_confirmatory_forest.png
```

## 16. 最终 Gate 判断

```text
G0–G10: completed with recorded scope/reviewer limitations
G11_FINAL_INTEGRITY_PASS
Confirmatory analysis: complete
Final scientific verdict: PASS WITH CLAIM RESTRICTIONS
```

允许的最终结论是“未检测到稳定 endpoint effect、未建立 endpoint equivalence、观察到有限
process-level sensitivity 和 task/model heterogeneity”。任何更强的全局 sensitivity 或
robustness claim 都超出当前证据。
