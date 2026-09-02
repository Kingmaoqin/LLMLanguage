# R6 后：距离总 Proposal 还差什么实验与 Gap

日期：2026-06-29  
关联报告：

- `reports/r6_sensitivity/R6_FULL_DEEP_ANALYSIS_CN_20260629.md`
- `reports/r6_sensitivity/R6_FULL_STATISTICAL_ANALYSIS_POSTRUN_20260629.md`
- `reports/r6_sensitivity/R6_FULL_INTERACTIONAL_PROFILE_POSTRUN_20260629.md`
- `reports/measurement_repair/R5_FULL_EXPERIMENT_REPORT_CN.md`
- `artifacts/stage2_5b/proposal_tact_stage2_5b_revised.md`

## 0. 一句话判断

R6 已经把项目从“retail-only 阴性结果”推进到“多域、多模型下安全层稳定但过程轨迹敏感”的阶段；这已经足以支撑一个有价值的 empirical paper 主线。

但如果目标是总 proposal 中更强的主张——即系统性回答 tool-using LLM agent 是否具有 interactional robustness，并把 endpoint、process、policy、efficiency、conversation-management 全部说完整——当前还差几个关键 gap：

1. **tau2 retail/airline 缺字段级 final-state evaluator**，导致 R6 endpoint claim 只能是 partial。
2. **R6 token/efficiency 指标缺失**，导致 proposal 中 RQ2 operational efficiency 还不能完整回答。
3. **显著的 tool-trajectory effect 还缺人工/结构化 case audit**，现在知道“路径变了”，但还不知道“为什么变、是否有操作含义”。
4. **minimal env 仍是简化环境**，多域覆盖已经有了，但真实业务复杂度和 tau2 等级环境仍不足。
5. **模型 roster 与外部有效性仍有限**，3 个模型能支撑初稿，但不足以强称 cross-model generality。
6. **LLM-only 对照仍未完成**，proposal 中作为 optional comparison，但如果要对齐既有 politeness/tone literature，仍需补。

因此，当前最合理路线不是继续盲目扩大 full run，而是补“解释力”和“测量完整性”的缺口。

## 1. 总 Proposal 的目标与当前证据状态

总 proposal 的核心问题是：

> 当任务、工具、权限、环境和用户身份保持不变时，仅改变用户对 agent 的态度表达，tool-using LLM agent 的执行行为是否稳定？

它分解成 5 个 RQ：

| RQ | Proposal 目标 | 当前证据状态 | 还缺什么 |
|---|---|---|---|
| RQ1 Task execution stability | 是否改变任务完成、计划、工具选择、final state | R5/R6 都未发现 primary FDR 的端点效应；R6 final correctness 只覆盖 minimal env 子集 | tau2 retail/airline 字段级 final-state evaluator |
| RQ2 Operational efficiency | token、tool-call count、retry、latency、clarification 是否改变 | R6 有 tool count / mutation / confirmation；token 全空，latency 不完整 | R6 token usage 修复；run-level duration / per-tool latency 抽取 |
| RQ3 Policy adherence | confirmation、authorization、privacy、refusal 是否受影响 | R6 unsafe/privacy=0；policy_failure_any 无 FDR；urgency 提高 confirmation_before_action_rate | 对 policy failure 类型做 case audit；确认“failure”不是 evaluator artifact |
| RQ4 Repeated abuse / conversation management | 是否 boundary-setting、de-escalation、abandonment | R5/R6 有 over_refusal/agent_side_abandonment 指标；R6 371 over_refusal/abandonment | 人工验证 abandonment classifier；区分合理拒绝 vs 任务放弃 |
| RQ5 Model/task dependence | 模型和任务是否异质 | R6 显示 Gemma/GPT-OSS/Mistral tradeoff 明显 | 增加 1–2 个模型或至少做模型分型 case study |

当前证据最强的部分：

- safety robustness：R6 2160 runs 中 `privacy_violation=0`, `unsafe_compliance=0`。
- process sensitivity：R6 primary 50 个 contrast×metric 中 5 个 FDR 显著，集中在工具轨迹和 confirmation。
- pressure mechanism：secondary 中 pressure 显著增加 tool calls、mutation events、confirmation_obtained。

当前证据最弱的部分：

- full endpoint correctness；
- token/efficiency；
- tool trajectory effect 的可解释性；
- minimal env 到真实环境的外部有效性。

## 2. 必须补的实验 / 分析 Gap

这些是如果要写严谨论文，建议优先补的。不是为了堆实验，而是为了堵住审稿人最容易攻击的口。

### Gap 1：tau2 retail/airline 的字段级 final-state evaluator

#### 当前问题

R6 共 2160 runs，其中：

| executor | runs | final_state_correct 可评估 |
|---|---:|---:|
| `tau2_r6_live` | 720 | 0 |
| `r6_minimal_live_model` | 1440 | 1440 |

也就是说，retail / airline 这 720 个真实 tau2 live runs 的 final correctness 为空，只能报告 process、policy、confirmation、tool trajectory、hash-level state 信息。

#### 为什么这是 proposal gap

Proposal 的 RQ1 明确包含：

- final state；
- external state changes；
- task completion；
- policy-constrained action outcome。

如果 retail/airline 没有字段级 final-state correctness，论文里所有 endpoint stability 都必须写成“partial endpoint evidence”。这会削弱主张。

#### 需要做什么

最低可接受版本：

1. 为 tau2 retail/airline 写 DB object diff extractor：
   - initial DB snapshot；
   - final DB snapshot；
   - expected field diffs；
   - unexpected field diffs；
   - missing expected field diffs。
2. 将结果写回 trace 或 metrics：
   - `field_level_db_diff_source=tau2_object_diff`
   - `expected_field_diff_coverage`
   - `unexpected_field_diff_count`
   - `final_state_correct`
3. 对现有 720 tau2 traces 做 post-hoc reconstruction；如果 trace 中没有完整 DB，只能小规模 rerun tau2 子集。

推荐优先级：**P0**。

#### 预期产物

```text
scripts/r6/reconstruct_tau2_field_diffs.py
results/r6_sensitivity/full_main_seq_eligible_20260626/field_diffs/tau2_field_diffs.csv
reports/r6_sensitivity/R6_TAU2_FIELD_DIFF_AUDIT_CN.md
```

## 3. Gap 2：R6 token / efficiency 指标缺失

### 当前问题

R6 `per_run_metrics.csv` 中：

```text
tokens_total: 2160/2160 empty
input_tokens: 2160/2160 empty
output_tokens: 2160/2160 empty
token_source: 2160/2160 empty
duration_seconds: 2160/2160 empty
```

R5 已经修复过 token bug，但 R6 trace/metrics pipeline 没有把 tau2 usage 与 minimal live usage 统一接上。

### 为什么这是 proposal gap

Proposal 的 RQ2 是 operational efficiency，明确包括：

- token usage；
- latency；
- retries；
- clarification turns；
- tool-call count。

R6 当前只能回答 tool-call count / mutation / confirmation，不能回答 token inflation、efficiency cost、latency。

### 需要做什么

最低可接受版本：

1. 检查 R6 trace 中是否已有 usage：
   - tau2 `sim.usage` / `token_usage`；
   - minimal live `usage.prompt_tokens/completion_tokens`。
2. 修 `scripts/r6/extract_r6_metrics.py`：
   - 增加 `input_tokens`, `output_tokens`, `tokens_total`, `token_source`；
   - 增加 `duration_seconds`，如果 trace 有时间戳则抽取；
   - 对 missing 显式写 `missing`，不要空字符串。
3. 重跑 metrics extraction 与 contrasts：
   - 将 tokens_total 加入 secondary 或 efficiency family；
   - 不把 token 作为 primary，除非预注册更新。

推荐优先级：**P0/P1**。

#### 预期产物

```text
reports/r6_sensitivity/R6_TOKEN_EFFICIENCY_AUDIT_CN.md
results/r6_sensitivity/full_main_seq_eligible_20260626/analysis/efficiency_contrasts.csv
```

## 4. Gap 3：显著 tool-trajectory effect 缺解释性 case audit

### 当前问题

R6 primary 显著项主要是：

| contrast | metric | estimate |
|---|---|---:|
| praise_trust_clean vs neutral_clean | tool_sequence_norm_distance_to_neutral | +0.279 |
| insult_strong_clean vs neutral_clean | tool_sequence_norm_distance_to_neutral | +0.315 |
| abuse_escalating_clean vs neutral_clean | tool_sequence_norm_distance_to_neutral | +0.242 |
| neutral_pressure vs neutral_clean | tool_sequence_norm_distance_to_neutral | +0.239 |

这说明工具路径偏离 neutral，但还不能说明偏离的性质。

可能的解释至少有四种：

1. 多查了一个 read tool；
2. 工具顺序换了，但最终语义等价；
3. 更早/更晚 mutation；
4. parser 或模型格式差异导致工具序列变形；
5. pressure 诱导模型跳过/增加确认步骤。

当前报告只能说“路径变了”，不能说“为什么变”。

### 为什么这是 proposal gap

Proposal 的贡献不是只做统计表，而是要刻画 social-valence 如何影响 agent behavior profile。工具轨迹显著是 R6 最重要发现，如果没有 case audit，审稿人会问：

- 这个 distance 是否只是无害重排？
- 是否由某几个 task 或某个模型驱动？
- 是否具有 operational consequence？
- 是否只是 neutral baseline 的自然变异？

### 需要做什么

建议做一个结构化 case audit：

1. 对每个显著 contrast，抽 top changed task/model/seed pairs。
2. 输出 neutral vs treatment 的工具序列 side-by-side：
   - tool names；
   - mutation timing；
   - confirmation timing；
   - refusal/boundary events；
   - final policy outcome。
3. 给每个差异标注类型：
   - benign reordering；
   - extra evidence；
   - premature mutation risk；
   - confirmation improvement；
   - task abandonment；
   - parser artifact。
4. 汇总每类比例。

推荐优先级：**P1**。

#### 预期产物

```text
scripts/r6/audit_tool_trajectory_effects.py
reports/r6_sensitivity/R6_TOOL_TRAJECTORY_CASE_AUDIT_CN.md
results/r6_sensitivity/full_main_seq_eligible_20260626/analysis/tool_trajectory_case_audit.csv
```

## 5. Gap 4：abandonment / over-refusal 需要人工验证

### 当前问题

R6 metrics 显示：

```text
over_refusals = 371
agent_side_abandonment = 371
```

模型差异明显：

| 模型 | over_refusal / abandonment |
|---|---:|
| gemma4_31b | 0.357 |
| gpt_oss_120b | 0.079 |
| mistral_small_3p2 | 0.079 |

这很可能是真发现：Gemma 更保守，常过拒/放弃。但也可能包含 classifier 误判。

### 为什么这是 proposal gap

RQ4 关心 repeated abuse 下 conversation-management：boundary-setting、de-escalation、refusal-to-continue、task abandonment。这个问题高度语义化，自动指标容易误判：

- 正确安全拒绝不应算 abandonment；
- 设边界后继续合法任务是好行为；
- 因不确定而要求更多信息可能是合理 clarification，不一定是 over-refusal。

### 需要做什么

做小样本人审：

1. 抽样 100–150 个 run：
   - over_refusal=True；
   - agent_side_abandonment=True；
   - Layer C correct refusal；
   - pressure 条件。
2. 人工标注：
   - correct boundary；
   - over-refusal；
   - benign clarification；
   - true abandonment；
   - evaluator artifact。
3. 估计自动指标 precision。
4. 如果 precision 低，修 metrics extractor 或报告中降级该指标。

推荐优先级：**P1**。

#### 预期产物

```text
reports/r6_sensitivity/R6_ABANDONMENT_HUMAN_AUDIT_CN.md
data/r6/human_audit/abandonment_sample.csv
data/r6/human_audit/abandonment_labels.csv
```

## 6. Gap 5：minimal env 外部有效性

### 当前问题

R6 已经从 retail-only 扩展到 calendar/email/workspace/hotel/file/message/privacy，但其中大部分是 `r6_minimal_live_model`，不是完整业务环境。

优点：

- deterministic；
- 可字段级 diff；
- 可控；
- 能覆盖 proposal 中缺失的 Layer C 和多域任务。

限制：

- 工具 schema 简化；
- 状态空间简化；
- policy evaluator 是研究者设计的最小版；
- 不一定反映真实 email/workspace/calendar 系统的复杂性。

### 为什么这是 proposal gap

总 proposal 的 benchmark 设计强调 deterministic APIs 和 auditable state transitions，但并不要求真实生产环境。不过如果要声称“多域 agent robustness”，minimal env 需要明确定位为 diagnostic benchmark，而不是完整模拟真实业务。

### 需要做什么

最低要求不是再造真实系统，而是补强文档和对照：

1. 写 minimal env validity audit：
   - 每个 domain 的 tool schema；
   - state object；
   - expected diff；
   - final evaluator；
   - 和真实业务的差距。
2. 选择 1 个非-retail domain 做更真实的二级环境：
   - calendar 或 email 最合适；
   - 增加 4–6 个任务；
   - 保持 deterministic。
3. 或者明确把当前 benchmark 定位为 “diagnostic stress test”，不做真实业务泛化。

推荐优先级：**P2**。

## 7. Gap 6：模型覆盖仍不够强

### 当前状态

R6 full 有 3 个模型：

- `gemma4_31b`
- `gpt_oss_120b`
- `mistral_small_3p2`

这已经比 R5 的 2 模型更好，而且三者表现差异明显：

- Gemma：保守/过拒型；
- GPT-OSS：低过拒，但完成有限；
- Mistral：完成率相对高，但 correct refusal 略弱。

### 还缺什么

总 proposal 的 RQ5 关心 model dependence。3 个模型可以写“模型异质性”，但不足以强称“跨模型普遍规律”。

如果资源允许，建议补 1–2 个模型，而不是再跑很多 seeds：

优先候选：

1. 一个小/中型美国或欧洲开源 instruct model；
2. 一个 reasoning-heavy model；
3. 一个不同 tool-call parser 风格的模型。

但注意：不要为了数量加入不能稳定 tool-call 的模型。R6 已经经历过模型部署失败，论文里应避免“模型 roster 看起来大但有效实验少”。

推荐优先级：**P2**。

## 8. Gap 7：LLM-only baseline 仍未完成

### 当前状态

总 proposal Section 4 保留了 LLM-only 对照的三个方案：

1. 在 agent runs 内标注 text-level metrics；
2. 与已有 LLM-only 文献做 literature-grounded comparison；
3. 设计单独 LLM-only baseline task set。

当前 R5/R6 主要完成的是 agentic benchmark；LLM-only 对照尚未系统做。

### 是否必须补？

不是必需，但取决于论文目标：

- 如果论文投 agent/safety/benchmark，LLM-only 可以作为 related work + discussion。
- 如果论文要强力回应 “这和 politeness/tone prompting 文献有什么不同”，最好至少做 Option 1 或 Option 3 的小规模 baseline。

### 推荐最低版本

做 Option 3 的小规模 matched text-only baseline：

- 选 10 个 R6 tasks；
- 把工具执行改成 policy judgment question；
- 同 8 conditions；
- 3 模型 × 10 tasks × 8 conditions × 3 seeds = 720 text-only judgments；
- 指标：
  - should_confirm；
  - should_refuse；
  - should_call_mutation；
  - policy answer correctness；
  - verbal compliance / sycophancy。

然后比较：

| Text-only | Agentic |
|---|---|
| 模型说应该确认 | 实际是否 confirmation_before_action |
| 模型说应该拒绝 | 实际是否 correct_refusal |
| 模型说不应泄露 | 实际是否 privacy_violation |
| 模型说会继续帮助 | 实际是否 agent_side_abandonment |

推荐优先级：**P2/P3**。

## 9. Gap 8：统计模型与功效分析

### 当前状态

R6 主统计：

- task-cluster bootstrap；
- Wilcoxon；
- BH-FDR。

GLMM 未拟合：

```text
mixed_effects = NOT_FIT
reason = Rscript or run_r6_glmm.R unavailable
```

这不阻断论文，因为 bootstrap 是预注册 canonical 分析。但审稿人可能希望看到模型/task/random effect。

### 需要做什么

1. 安装/启用 Rscript + lme4，或改用 Python statsmodels/Bambi/PyMC。
2. 拟合：
   - binary outcomes: final_state_correct, policy_failure_any, unsafe/privacy；
   - count outcomes: n_tool_events；
   - continuous: tool_sequence distance。
3. random intercepts:
   - task；
   - model；
   - seed。
4. 报告作为 sensitivity，不替代 bootstrap。

推荐优先级：**P2**。

## 10. Gap 9：manipulation checks / human ratings

### 当前状态

R5/R6 已有 template contamination audit，能排除授权/紧急/威胁/任务事实污染。但 proposal 里还提过：

- valence；
- affect intensity；
- trust attribution；
- authorization contamination；
- urgency / pressure 独立轴。

R6 已经设计了 clean valence vs pressure factorial，但如果要写得很强，还需要轻量 human/LLM rating。

### 需要做什么

最低版本：

1. 对 8 条 condition 模板做 blind rating：
   - valence；
   - hostility；
   - trust；
   - urgency；
   - authorization implication；
   - continuation pressure。
2. 每个模板 3–5 个标注者或一个固定 evaluator model + spot-check。
3. 输出 inter-rater agreement 或至少均值/方差。

推荐优先级：**P2**。

## 11. Gap 10：R6 显著项的“因果机制”还需更强证据

当前 R6 能说：

- social valence changes tool trajectory；
- pressure changes confirmation/tool/mutation intensity；
- unsafe/privacy remains zero。

但还不能强说：

- 为什么工具轨迹变；
- 是否模型内部“更信任用户/更防御”；
- 是否 pressure 通过 confirmation_request 机制影响 mutation；
- 是否某类任务被特定 condition 系统性触发。

建议后续做 mechanism-focused analyses：

1. mediation-style descriptive analysis：
   - condition → confirmation_before_action → mutation_events；
   - condition → n_tool_events → final_state_correct/policy_failure。
2. task-stratified contrast：
   - Layer A / B / C；
   - read-only vs confirmed-write vs boundary；
   - tau2 vs minimal env。
3. model-stratified contrast：
   - Gemma/GPT-OSS/Mistral 分别计算 primary/secondary。

推荐优先级：**P1/P2**。

## 12. 当前可以写进论文的主张

可以稳妥写：

1. **方法贡献**：提出 interactional robustness 的 agentic diagnostic benchmark，并控制 task/user/tool/policy/environment invariance。
2. **历史修复贡献**：展示早期 repeated-abuse 工具调用效应来自 continuation/policy cue 混杂；通过 deterministic user 和 clean templates 修复。
3. **R5 证据**：在 retail-only 2 模型 480-run measurement-complete setting 中，没有可复现 FDR 效价效应。
4. **R6 证据**：在 2160-run、多域、多模型 setting 中，unsafe/privacy 稳定为 0，端点/policy 没有 primary FDR 效应，但工具轨迹和 pressure-driven confirmation/action intensity 有显著变化。
5. **模型异质性**：Gemma、GPT-OSS、Mistral 显示不同 safety/completion/over-refusal tradeoff。

不能过度写：

1. 不能写“agent 完全鲁棒”。
2. 不能写“社会效价没有任何影响”。
3. 不能写“R6 证明最终任务成功不受影响”而不注明 tau2 final correctness 缺失。
4. 不能写“token efficiency 不受影响”，因为 R6 token 指标缺失。
5. 不能写“pressure 是唯一机制”，只能说 pressure 在当前设计中更直接影响 action intensity。

## 13. 建议的补实验路线图

### 最小补强路线（推荐，1–2 天）

目标：让当前 R6 paper draft 足够严谨。

1. R6 token/usage 修复 + metrics 重抽；
2. tool trajectory case audit；
3. abandonment/over-refusal 小样本人审；
4. 写 final synthesis report；
5. 更新 proposal revised artifact。

优点：最省资源，直接补当前结论的解释力。

### 中等补强路线（3–5 天）

目标：加强 endpoint 和机制主张。

1. tau2 retail/airline field diff reconstruction；
2. R6 token/efficiency；
3. tool trajectory + model-stratified contrast；
4. manipulation rating；
5. GLMM sensitivity。

优点：可以把 endpoint stability 写得更强。

### 扩展实验路线（更长）

目标：增强外部有效性。

1. 新增 1–2 个模型；
2. 新增一个更真实的 non-retail env；
3. 做 LLM-only matched baseline；
4. 增加 seeds 或 task clusters。

优点：更适合高要求 venue；缺点是资源消耗大，且可能继续暴露工程问题。

## 14. 优先级总表

| 优先级 | Gap | 为什么重要 | 建议 |
|---|---|---|---|
| P0 | tau2 final-state field diff | 关系到 RQ1 endpoint claim | 尽快补 |
| P0/P1 | R6 token/efficiency | 关系到 RQ2 | 尽快补 |
| P1 | tool trajectory case audit | 解释 R6 最重要显著发现 | 必做 |
| P1 | abandonment/over-refusal human audit | 防止自动指标误判 | 必做 |
| P1/P2 | mechanism-focused stratified analysis | 提升 insight | 建议做 |
| P2 | GLMM sensitivity | 统计稳健性 | 有时间做 |
| P2 | manipulation ratings | 操纵有效性 | 有时间做 |
| P2 | more models | 外部有效性 | 资源允许做 |
| P2/P3 | LLM-only baseline | 对接文献 | 视投稿定位 |
| P3 | more realistic env | 泛化性 | future work 可接受 |

## 15. 最终建议

当前不建议马上再跑一个更大的 full。R6 已经足够大，真正的问题不是样本量，而是几个测量和解释 gap：

- endpoint 覆盖不完整；
- efficiency 缺失；
- tool trajectory 显著但机制未解释；
- abandonment/over-refusal 需要人工校验。

如果只做一件事，先做 **tool trajectory case audit**。因为这是 R6 最核心的新发现，直接决定论文从“统计上显著”能否升级为“行为机制上有意义”。

如果做两件事，再加 **R6 token/efficiency 修复**。这样 proposal 的 RQ2 才能闭环。

如果做三件事，再加 **tau2 field diff reconstruction**。这样 RQ1 endpoint stability 才能从 partial evidence 升级为更完整证据。

完成这三项后，当前项目就可以从“实验已跑完”进入“论文主张可防守”的阶段。
