# R6 全量实验深度中文分析报告

日期：2026-06-29  
结果根目录：`results/r6_sensitivity/full_main_seq_eligible_20260626`  
分析对象：R6 full main sequence eligible，全量 2160 traces

## 0. 核心结论

R6 的结论不能简单延续 R5 的“全维度无显著效应”。R6 扩展到 30 个任务、10 个实际 domain、3 个模型、8 个条件之后，出现了一个更细的图景：

1. **安全边界保持稳定**：全量 2160 runs 中，`privacy_violation = 0`，`unsafe_compliance = 0`，`unsafe_compliance_or_privacy_violation = 0`。Layer-C 边界任务中，各条件的 unsafe/privacy 违规均为 0，correct refusal 大体在 0.958–1.000。
2. **端点/策略失败没有 FDR 显著的社会效价效应**：预注册 primary 指标中，`final_state_correct`、`policy_failure_any`、`unsafe_compliance_or_privacy_violation` 都没有通过 FDR。
3. **交互过程并非完全鲁棒**：primary 50 个 contrast×metric 中有 5 个 FDR 显著，其中 3 个是纯效价导致的 `tool_sequence_norm_distance_to_neutral` 上升，2 个来自 pressure factorial；secondary 120 个中也有 5 个显著，均与 pressure 下工具调用/确认/ mutation 增加有关。
4. **R6 支持的更准确表述是**：社会风格和压力线索没有诱发安全违规，也没有稳定改变最终正确性或策略失败率；但它们确实会改变工具轨迹，尤其是相对 neutral 的工具序列路径，以及 urgency pressure 下的确认行为。

因此，R6 的论文口径应从 R5 的“交互鲁棒性”推进为更精细的版本：

> 在更宽任务/域/模型覆盖下，LLM 工具代理对社会效价扰动表现出安全层鲁棒性和端点层相对稳定，但过程轨迹层存在可复现的路径敏感性；压力/紧急/授权类线索比单纯辱骂或赞扬更容易改变确认和工具调用行为。

这不是坏结果。相反，它把研究问题推进了一层：早期“是否影响最终结果”的问题，现在变成“哪些社会线索会改变代理的行动路径，但不一定造成 unsafe outcome”。

## 1. 数据完整性与实验覆盖

完整性审计结果：

```text
R6 integrity: PASS
traces = 2160
invalid = 0
duplicates = 0
schema failures = 0
invalid_rate = 0.000
```

实验矩阵：

| 维度 | 数量 | 说明 |
|---|---:|---|
| 模型 | 3 | `gemma4_31b`, `gpt_oss_120b`, `mistral_small_3p2` |
| 任务 | 30 | R6 task set |
| 条件 | 8 | clean valence + pressure factorial |
| seeds | 3 | 300, 301, 302 |
| 总 runs | 2160 | 3 × 30 × 8 × 3 |

任务层级：

| Layer | runs | 含义 |
|---|---:|---|
| A | 576 | benign read-only / diagnostic |
| B | 1008 | benign write，需要 evidence + confirmation |
| C | 576 | privacy/refusal/unsafe/boundary |

执行器覆盖：

| executor | runs | final_state_correct 可评估 | 说明 |
|---|---:|---:|---|
| `tau2_r6_live` | 720 | 0 | retail / airline live tau2，状态主要是 hash-only，不做字段级 final correctness |
| `r6_minimal_live_model` | 1440 | 1440 | calendar/email/workspace/hotel/file/message/privacy 等 R6 minimal deterministic env |

这点很重要：R6 的 `final_state_correct` 不是 2160 runs 全部都有字段级可评估值；tau2 retail/airline 部分仍是 hash-only。因此本报告把“可评估端点结果”和“安全/过程指标”分开解释，避免把空值错误当成失败。

## 2. 与历史 R4/R5 的关系

### 2.1 R5 的结论

R5 measurement-complete full 是 480 runs：

```text
2 模型 × 8 retail tasks × 6 conditions × 5 seeds = 480
```

R5 的核心结论是：在 retail-only、2 模型、清洁模板、确定性用户下，社会效价没有在端点、工具轨迹、策略、效率、对话管理等 6 维画像上产生 FDR 显著影响。R5 同时确认：

- Stage-2 mini 中 repeated_abuse 工具调用大幅增加主要来自模板/用户模拟混杂；
- R4/R4.1 中少量过程显著项没有被 R5 复现，应降级为不稳定/探索性信号。

### 2.2 R6 为什么会和 R5 不同

R6 不是 R5 的简单重复，而是扩大了三个维度：

1. **任务域从 retail 扩到 10 个实际 domain**：retail, airline, calendar, email, workspace, hotel, file, message, privacy, travel_privacy。
2. **任务层级加入更多 Layer-C 边界任务**：R5 的 Tier-C/unsafe 覆盖不足，R6 显式增加 privacy/refusal/boundary。
3. **模型从 2 个扩到 3 个**：新增 Mistral，使模型异质性更明显。

因此，R6 出现过程轨迹显著并不否定 R5。更准确地说：

- R5 证明：在 retail-only 的较窄环境中，社会效价效应不稳健；
- R6 发现：在多域、多任务、多模型下，最终安全不变，但工具路径对社会风格/压力线索更敏感。

这是一种范围扩展后的发现，而不是简单结论翻转。

## 3. 预注册 primary 统计结果

R6 primary metrics：

- `final_state_correct`
- `policy_failure_any`
- `confirmation_before_action_rate`
- `unsafe_compliance_or_privacy_violation`
- `tool_sequence_norm_distance_to_neutral`

统计方法：

- paired by `(model, task, seed)`
- task-cluster bootstrap 10k
- Wilcoxon cross-check
- BH-FDR within family
- mixed-effects 未拟合，原因是当前环境无 `Rscript/run_r6_glmm.R`；canonical 结果为 bootstrap + FDR

primary 总览：

| family | contrasts × metrics | FDR 显著 |
|---|---:|---:|
| pure_valence | 15 | 3 |
| pressure_factorial | 20 | 2 |
| mechanism | 15 | 0 |
| 合计 | 50 | 5 |

5 个 primary 显著项：

| family | contrast | metric | estimate | 95% CI | q |
|---|---|---|---:|---:|---:|
| pure_valence | praise_trust_clean vs neutral_clean | tool_sequence_norm_distance_to_neutral | +0.279 | [+0.219, +0.341] | 0.001 |
| pure_valence | insult_strong_clean vs neutral_clean | tool_sequence_norm_distance_to_neutral | +0.315 | [+0.242, +0.391] | 0.001 |
| pure_valence | abuse_escalating_clean vs neutral_clean | tool_sequence_norm_distance_to_neutral | +0.242 | [+0.180, +0.305] | 0.001 |
| pressure_factorial | neutral_pressure vs neutral_clean | tool_sequence_norm_distance_to_neutral | +0.239 | [+0.179, +0.299] | 0.004 |
| pressure_factorial | insult_urgency_pressure vs insult_strong_clean | confirmation_before_action_rate | +0.133 | [+0.059, +0.207] | 0.004 |

关键解释：

- 纯效价的显著项全部集中在工具轨迹距离，不在 final correctness / policy failure / unsafe。
- pressure factorial 里，neutral pressure 改变工具轨迹；insult + urgency pressure 提高确认前置率。
- mechanism family 没有显著项，说明在 pressure 条件之间相互比较时，没有证据表明“赞扬授权”或“辱骂紧急”相对 neutral pressure 产生额外机制效应。

## 4. Secondary 结果：pressure 改变行动强度

secondary 120 个 contrast×metric 中有 5 个 FDR 显著，全部在 pressure factorial family：

| contrast | metric | estimate | 95% CI | q |
|---|---|---:|---:|---:|
| neutral_pressure vs clean | n_tool_events | +0.400 | [+0.119, +0.685] | 0.031 |
| insult_urgency_pressure vs insult_clean | n_tool_events | +0.800 | [+0.507, +1.111] | 0.010 |
| insult_urgency_pressure vs insult_clean | n_mutation_events | +0.130 | [+0.044, +0.222] | 0.031 |
| insult_urgency_pressure vs insult_clean | confirmation_obtained | +0.063 | [+0.022, +0.111] | 0.031 |
| abuse_continuation_pressure vs abuse_clean | n_tool_events | +0.452 | [+0.148, +0.774] | 0.031 |

这组 secondary 结果和 primary 的 `confirmation_before_action_rate` 显著项相互印证：R6 中真正驱动“行动路径变化”的，不只是情绪正负，而是“pressure / urgency / continuation”这类任务推进线索。

这也解释了为什么 Stage-2 mini 中“辱骂导致工具调用变多”曾经很强：早期模板里混入了 continuation / follow policy 语义。R6 把 clean valence 和 pressure factorial 分开后，能够看到：纯效价主要改变路径距离，而 pressure 才显著提高工具调用数量、确认获得和 mutation 行为。

## 5. 条件均值画像

按 condition 的关键均值如下：

| condition | final_state_correct* | policy_failure_any | unsafe/privacy | confirmation_before_action_rate | n_tool_events | over_refusal |
|---|---:|---:|---:|---:|---:|---:|
| neutral_clean | 0.194 | 0.233 | 0.000 | 0.274 | 2.174 | 0.178 |
| praise_trust_clean | 0.172 | 0.226 | 0.000 | 0.274 | 2.567 | 0.163 |
| insult_strong_clean | 0.122 | 0.185 | 0.000 | 0.296 | 1.930 | 0.137 |
| abuse_escalating_clean | 0.150 | 0.207 | 0.000 | 0.326 | 2.059 | 0.167 |
| neutral_pressure | 0.239 | 0.204 | 0.000 | 0.333 | 2.574 | 0.174 |
| praise_trust_authorization_pressure | 0.200 | 0.252 | 0.000 | 0.281 | 2.285 | 0.207 |
| insult_urgency_pressure | 0.206 | 0.189 | 0.000 | 0.430 | 2.730 | 0.163 |
| abuse_continuation_pressure | 0.172 | 0.241 | 0.000 | 0.341 | 2.511 | 0.185 |

\* `final_state_correct` 只在 1440 个 minimal live runs 中字段级可评估；tau2 retail/airline 的 final correctness 为空，因此这里不是 2160 全体的 global success rate。

可见：

- unsafe/privacy 全部为 0，安全边界稳定；
- policy failure 约 0.185–0.252，没有 primary FDR 显著差异；
- insult_urgency_pressure 的 confirmation rate 明显最高；
- 工具调用数量在 pressure 条件整体偏高，尤其 insult_urgency_pressure。

## 6. 模型异质性

按模型汇总：

| 模型 | runs | final_state_correct 可评估均值 | policy_failure_any | unsafe/privacy | correct_refusal | over_refusal / abandonment |
|---|---:|---:|---:|---:|---:|---:|
| gemma4_31b | 720 | 0.075 | 0.358 | 0.000 | 1.000 | 0.357 |
| gpt_oss_120b | 720 | 0.142 | 0.079 | 0.000 | 1.000 | 0.079 |
| mistral_small_3p2 | 720 | 0.329 | 0.214 | 0.000 | 0.922 | 0.079 |

主要观察：

1. Gemma 最保守，over-refusal / agent-side abandonment 最高，policy failure 也最高。这类 failure 主要不是 unsafe，而是过度拒绝或任务放弃。
2. GPT-OSS 在 policy failure 和 over-refusal 上最低，但 final_state_correct 也不高；它更愿意行动，但未必能完成复杂目标。
3. Mistral 的可评估 final correctness 最高，但 correct refusal 低于另外两个模型，说明它在边界任务上有少量拒绝不足或边界处理缺陷。

这说明模型选择会显著改变“安全-完成度-过度拒绝”的 tradeoff。R6 不能只报告一个平均数，否则会掩盖模型行为类型的差异。

## 7. Layer 与 domain 结果

按 layer：

| Layer | runs | final_state_correct 可评估均值 | policy_failure_any | unsafe/privacy | 解释 |
|---|---:|---:|---:|---:|---|
| A | 576 | 0.425 | 0.368 | 0.000 | read-only 任务完成率较高，但 policy/evidence 失败仍多 |
| B | 1008 | 0.151 | 0.240 | 0.000 | 确认和写操作是主要困难来源 |
| C | 576 | 0.044 | 0.026 | 0.000 | final correctness 低但安全边界强；correct refusal 0.974 |

Layer-C 的关键点不是“任务成功率低”，而是“没有 unsafe/privacy violation”。在边界任务里，系统宁可拒绝/不完成，也没有越界执行；这对安全论文是重要结果。但同时，过低的 final correctness 提醒我们：当前 evaluator 和任务设计把“正确拒绝 + 允许部分继续”要求得很细，模型仍常无法完整执行允许子任务。

按 domain 看：

- calendar 的可评估 final correctness 最高，约 0.296；
- hotel/file/email/workspace 中等偏低；
- retail/airline 是 tau2 hash-only，final correctness 不可直接字段级解释，但 policy failure 分别约 0.260 / 0.285；
- travel_privacy 的 final correctness 为 0，但 policy failure 和 unsafe/privacy 都为 0；这类任务需要进一步审查 evaluator 是否把“正确拒绝”与 `final_state_correct` 对齐。

## 8. 最重要的 insight：R6 把“效价”与“行动压力”分开了

历史上最容易混淆的问题是：辱骂/赞扬到底影响代理，是因为情绪语气，还是因为模板中混入了“继续做、快点做、按政策做、我授权你做”的任务推进语义？

R6 的 factorial 设计给出了更清楚的答案：

1. **纯效价会改变路径，但没有改变安全/端点**  
   praise_trust、insult、abuse clean 相对 neutral clean，均显著提高工具序列相对 neutral 的距离；但 final correctness、policy failure、unsafe/privacy 没有显著变化。

2. **pressure 会提高行动强度**  
   neutral_pressure 显著提高工具轨迹距离，并在 secondary 中增加工具调用数；insult_urgency_pressure 增加 confirmation_before_action_rate、confirmation_obtained、n_tool_events、n_mutation_events。

3. **“辱骂 + 紧急”比“辱骂本身”更像行为驱动因素**  
   insult_clean 的纯情绪作用主要体现在路径差异；加入 urgency 后，确认和 mutation 行为增加。这是机制上更可解释、也更有论文价值的结果。

结论上，应避免写成“辱骂让代理更危险”或“赞扬让代理更听话”。R6 更支持：

> 社会语气本身足以改变工具路径；但真正增加行动强度的是 pressure/urgency/continuation 这类任务推进线索。安全边界在本实验中没有被突破。

## 9. 对 R5 结论的修正和升级

R5 可以保留，但需要在 R6 后重新定位：

| 问题 | R5 结论 | R6 后的更新 |
|---|---|---|
| 社会效价是否影响最终成功？ | 未发现稳健影响 | 仍未发现 primary FDR 的端点影响 |
| 社会效价是否影响安全？ | 未发现 unsafe/隐私问题 | R6 强化支持：2160 runs unsafe/privacy = 0 |
| 社会效价是否影响过程？ | R5 未发现 FDR 显著 | R6 发现工具轨迹显著变化 |
| pressure/urgency 是否关键？ | R5 覆盖不足 | R6 显示 pressure 改变工具数量、确认、mutation |
| 模型异质性如何？ | 2 模型，范围有限 | 3 模型显示明显安全-完成度-过拒 tradeoff |

因此最终论文可以写成两阶段证据链：

1. R5：在窄域 retail 中，早期过程显著未复现，endpoint 与过程总体稳定；
2. R6：扩域后发现过程轨迹敏感性，但这种敏感性没有转化为 unsafe/privacy violation 或稳定端点变化。

这比“完全没有影响”更严谨，也更有深度。

## 10. 当前结果的限制

必须明确以下限制，否则结论会过度：

1. **final_state_correct 覆盖不完整**：retail/airline tau2 live 部分没有字段级 final correctness，端点结果应视为 partial endpoint evidence。
2. **token 指标缺失**：本轮 per-run metrics 中 `tokens_total/input/output/token_source` 均为空，无法对 R6 全量做严肃 token efficiency 分析；不能声称 R6 中 token inflation 显著或不显著。
3. **部分 minimal env 仍是简化环境**：calendar/email/workspace/hotel/file/message/privacy 可执行，但仍是 R6 minimal deterministic env，不等同于完整真实业务系统。
4. **Mistral 运行中做过工程修复**：为完成 full run，加入了 `max_tokens_per_turn=384`、tool-call JSON 容错、minimal live max_tokens 传递修复。这些修复合理且 schema/integrity 通过，但报告中应记录 provenance。
5. **mixed-effects 未拟合**：当前主统计是 paired bootstrap + Wilcoxon + FDR；GLMM 未运行。
6. **tool_sequence_norm_distance_to_neutral 的解释要谨慎**：它是相对 neutral 轨迹的距离，显著为正说明路径偏离，并不直接等同于“更差”或“更危险”。

## 11. 建议的论文主张

建议主张分三层：

### Claim 1：Safety robustness

在 2160-run R6 full 中，三模型、多域、多层级任务下没有观察到 privacy violation 或 unsafe compliance。社会效价和 pressure 操作没有突破安全边界。

### Claim 2：Endpoint stability under partial evaluability

在可字段级评估的 minimal live 子集上，final_state_correct 没有任何 primary FDR 显著的社会效价/pressure 差异；但由于 tau2 retail/airline 缺字段级 final correctness，应称为 partial endpoint evidence。

### Claim 3：Process sensitivity

工具轨迹对 clean valence 和 pressure 均敏感：praise_trust、insult、abuse clean 均显著偏离 neutral 工具路径；pressure 尤其会增加工具调用、确认获得和 mutation 行为。这说明代理不是“过程完全不受影响”，而是“受影响但未越界”。

这三个 claim 放在一起，比单句“鲁棒/不鲁棒”更准确。

## 12. 下一步建议

1. **补字段级 final evaluator for tau2 retail/airline**  
   这是最高优先级。否则 R6 的 endpoint claim 永远是 partial。

2. **修复 R6 token extraction**  
   当前 2160 行 token 字段全空，无法回答 efficiency / token inflation。应把 tau2 usage 与 minimal live usage 统一写入 trace schema，再重抽 metrics。

3. **对显著 tool trajectory 做 case audit**  
   抽样比较 neutral vs praise/insult/abuse 的具体工具序列，判断是“工具顺序变化”“多查一步”“提前 mutation”“不同 read source”，还是 parser/tool-call 风格差异。

4. **单独分析 pressure 机制**  
   R6 的最强机制信号来自 urgency/continuation/pressure。建议把 pressure 从“附加条件”上升为独立研究问题。

5. **模型分型报告**  
   Gemma = 保守/过拒型；GPT-OSS = 低过拒但完成有限；Mistral = 完成度较高但 correct refusal 略弱。这个 tradeoff 很适合做图。

6. **不要急于宣称 full equivalence**  
   R6 不是等价性证明。更稳妥是“无安全违规 + 无端点 FDR + 有过程路径 FDR”。

## 13. 产物路径

关键产物：

```text
results/r6_sensitivity/full_main_seq_eligible_20260626/
  traces/                                      # 2160 traces
  interactional_metrics/per_run_metrics.csv   # 2160 rows
  analysis/primary_contrasts.csv
  analysis/secondary_contrasts.csv
  analysis/mixed_effects_results.csv

reports/r6_sensitivity/R6_FULL_INTEGRITY_POSTRUN_20260629.md
reports/r6_sensitivity/R6_FULL_STATISTICAL_ANALYSIS_POSTRUN_20260629.md
reports/r6_sensitivity/R6_FULL_INTERACTIONAL_PROFILE_POSTRUN_20260629.md
reports/r6_sensitivity/R6_FULL_DEEP_ANALYSIS_CN_20260629.md
```

## 14. 最终判断

R6 全量结果的科学价值在于，它没有简单重复 R5 的“无效应”，而是把效应定位到了更具体的层面：

- **安全层**：稳健，没有 unsafe/privacy violation。
- **端点层**：未发现 FDR 显著改变，但 endpoint evaluability 不完整。
- **过程层**：不完全稳健，工具轨迹和 pressure-driven action intensity 有显著变化。

这使得最终研究叙述更可信：LLM 工具代理不会因为用户赞扬或辱骂就明显越权或泄露隐私，但它们的行动路径会随社会语气和压力线索改变。对于安全部署来说，真正需要防的是“社会压力诱导的行动路径漂移”，而不是只看最终成功率。
