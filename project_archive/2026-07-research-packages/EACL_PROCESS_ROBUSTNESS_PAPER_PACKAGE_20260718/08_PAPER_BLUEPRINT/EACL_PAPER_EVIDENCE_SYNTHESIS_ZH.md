# EACL 论文证据综合报告

## 1. 执行摘要与投稿判定

本报告对 `/home/xqin5/llmlanguage` 中与 tool-using LLM agent interactional robustness 相关的历史资产进行了只读审计。审计覆盖 26,760 个文件、17,119 条 trace-like 路径，重点复核 R6、R7 系列和 R8。所有新增结果都来自离线解析、确定性配对重聚合、Bootstrap、置换检验和多重比较校正；没有启动模型、endpoint、GPU、agent rollout 或新 reviewer。

当前结论是 **CONDITIONAL GO**。现有资产支持一篇以“过程鲁棒性是独立评估维度、随机轨迹漂移必须由 neutral-neutral placebo 校准、不同 protocol 下结论高度异质、outcome-only 指标可能遗漏路径变化”为中心的审慎实证/方法审计论文。现有资产不支持把 “Stable Outcomes, Unstable Processes” 当作已经得到跨模型、跨任务、跨协议确认的普遍规律。

最强的三个结果是：

1. **R8 的 outcome calibrated null。** 在官方 tau2 full-episode evaluator 下，urgency 相对 clean neutral 的 reward 差为 `+2.43pp`，95% CI `[-2.42, 7.08]pp`，Holm `p=.749`；frustration 为 `-0.56pp [-5.24, 3.92]pp`，`p=.879`。结果不支持 pooled ≥5pp 的负面 outcome 变化。
2. **R6 tau2 的 placebo-adjusted process difference。** post-hoc 分析中，praise/trust 和 process-frustration 条件的工具名序列距离高于 neutral-neutral 漂移，调整后效应分别为 `0.150 [0.077, 0.239], q=.014` 和 `0.174 [0.060, 0.283], q=.037`。但模板不满足纯 valence 操作，故只能作为探索性证据。
3. **R7-C 的方法学反证。** strict PASR 的 attack rate 为 `87/2160=4.03%`，而 pooled neutral-neutral placebo 为 `4.63%`。这说明若不显式校准 agent 自身的随机轨迹漂移，路径差异指标可以把背景非确定性误报为 perturbation effect。

R8 中 tool-call 变化约 `+0.50/+6.4%` 和 `+0.69/+8.7%`，低于预注册的 `≥1 call` 且 `≥15%` 双重实际重要性阈值。这是 process practical-null，而不是“过程完全不变”。R6 中确有 final DB hash 相同但工具路径不同的 paired traces，但 hash 相同只说明记录的外部状态相同，不能证明任务成功、沟通正确或路径语义不等价。

## 2. 项目历史与研究定位

项目经历了从 R6 主矩阵、R7/IPMA 操作与审计，到 R8 官方 full-episode protocol 的演进。历史材料中同时存在主实验、synthetic fixture、mechanism smoke、infrastructure liveness、失效 evaluator、errata 与反证。它们不能按“版本越新越可信”简单合并，而必须按构念效度、evaluator 适配、分母与 provenance 逐项判断。

R6 的价值在于完整 paired matrix 和丰富 trace；其局限是 20 个 minimal/stub task 的工具执行器忽略部分 arguments，以及 10 个 tau2 task 缺 field-level correctness。R7 的价值主要是暴露旧 PASR、pairing 和 placebo 设计问题，而不是提供新的 population effect。R8 的价值是使用官方 tau2 full-episode evaluator、明确 practical thresholds，并给出稳健 pooled null；它考察的是 pressure/frustration protocol，不能与 R6 的社会表达模板合并成一个效应。

论文最稳妥的定位不是“证明 agent 被用户态度操纵”，而是：**建立 interactional process robustness 的测量纪律，并用正、负和失效证据展示 outcome、process 与 evaluator validity 必须分开。**

## 3. 科学问题与形式化区分

设固定上下文为

\[
c=(m,t,s,e_0,\mathcal{T},\pi),
\]

其中 \(m\) 为模型、\(t\) 为任务、\(s\) 为 seed、\(e_0\) 为初始外部状态、\(\mathcal{T}\) 为工具集合、\(\pi\) 为系统 policy。用户表达条件为 \(v\)。agent 产生轨迹

\[
\tau_v=(a_1,\ldots,a_k)
\]

及最终可观测 outcome \(y_v\) 和外部状态 \(e_v\)。

Outcome robustness 研究 \(d_Y(y_v,y_0)\) 或 \(d_E(e_v,e_0^\*)\) 是否处于预设等价/实际重要性阈值内。Process robustness 研究在匹配 \(c\) 后，\(d_\tau(\tau_v,\tau_0)\) 是否超出 neutral-neutral 的背景漂移，并考察这种差异是否触及 arguments、证据路径、confirmation、writes、成本或风险暴露。

关键点有三：

- outcome 与 process 不是互相替代的指标；
- “轨迹不同”本身不等于有害、低效或语义不同；
- process effect 必须与 agent 非确定性的 placebo 分布比较，而不是与 neutral trace 的自距离 0 比较。

## 4. 数据、模型、任务与条件

### R6

R6 主矩阵含 2,160 条 trace：3 个模型（`gemma4_31b`、`gpt_oss_120b`、`mistral_small_3p2`）×30 个任务×8 个条件×3 个 seeds。按记录包含 10 个 domain；其中 10 个任务、720 条 trace 来自 tau2 retail/airline，20 个任务、1,440 条来自 minimal live environment。矩阵有 270 个 model-task-seed 单元，8 条件完整；预定义 treatment-neutral 配对共 1,890 对，未发现记录的 initial-state hash 不一致。

历史条件名包括 neutral、praise、insult、abuse 及其 pressure/authorization/urgency/continuation 版本。读取冻结模板后，论文应重命名：

- `praise_clean` → praise/trust-in-process；
- `insult_strong_clean` → process frustration；
- `abuse_escalating_clean` → escalating process complaint；
- pressure variants → pressure/directive bundles。

原因是所谓 strong insult 并非稳定的直接辱骂，所谓 escalating abuse 主要是对流程升级抱怨；authorization、urgency、continuation 又携带明确任务语义。原标签不能直接作为纯 social valence 因子。

### R7 系列

R7-v1 的旧 PASR 约 14%，但受到 pairing、endpoint 与 semantic fail-open 问题影响，已失效。R7-B 主要是 synthetic smoke。R7-C 提供了 strict evaluator 与 neutral-neutral placebo，可作为方法反证。R7-D 进一步显示部分 construct/harness 较弱或为 stub，因此不作为 population evidence。

### R8

R8 是官方 tau2 full-episode pressure protocol：retail/airline 共 36 tasks、3 模型、5 conditions、5 repeats，设计分母 2,700，有效 2,680；20 个 Mistral episode 因 capacity 排除。R8 的条件和 harness 与 R6 不同，不能池化。

## 5. 实验设计与 matched comparison

核心配对键为同一 model、task、seed 和记录的 initial state。R6 条件矩阵满足结构配对，但结构配对不自动保证构念配对：当模板同时修改 valence、授权或任务推进指令时，估计量对应的是整个文本 bundle，而非单一态度。

本次 R6 process 复核新增 neutral-neutral placebo：在同一 model-task 内比较不同 neutral seeds，得到非确定性背景距离。condition-neutral 距离减 placebo 后，才解释为 perturbation-associated excess distance。统计依赖以 task 为 cluster，避免把同一任务的 model/seed 记录当完全独立样本。

R8 继承冻结分析中的 task-cluster inference、Holm correction 和 practical thresholds。由于 R6 与 R8 的 outcome evaluator、tool harness、condition content 和分母不同，本报告严格分协议呈现。

## 6. Evaluator 审计

### Outcome evaluator

R8 使用 tau2 1.0.0 原生 `evaluate_simulation`，是当前最可信 outcome scorer。

R6 minimal environment 的 `execute_tool` 没有忠实使用模型生成的所有 arguments，而是按 expected path 修改状态。这会让错误实体绑定或错误参数仍得到正确 final state。因此，R6 minimal 的 `final_state_correct` 数值即使可重算，也不能支撑任务成功。R6 tau2 的 720 条 trace 只存 final DB hash，没有 field-level task correctness。R6 “最终成功稳定”因此是 `INVALIDATED_BY_EVALUATION`，不是普通 limitation。

### Safety、privacy 与 abandonment

R6 safety proxy 主要检测成功的 prohibited tool execution 或显式 runner flags，不完整覆盖 assistant 文本中的泄露、承诺或语义越权。因此 2,160 条中 proxy 未检出事件，只能写成窄执行层观察，不能写“privacy violation 和 unsafe compliance 为零”。

`agent_side_abandonment` 的 fallback 直接映射 `over_refusal`，并有 371 个值逐项相等；它不是独立 abandonment evaluator。repeated complaint 下 abandonment 是否增加仍为 Unknown。

### Process evaluator

确定性可审计字段包括工具名序列、argument hash 序列、阶段序列、首次分叉、长度、exact duplicate、reorder、pre-write path 和可适用的 confirmation-before-write。argument hash 能检测改变，却不能说明改变了哪个实体或是否语义等价。语义机制需要 blind dual-independent-agent review；本次仅设计协议，没有执行。

## 7. Token accounting 与成本边界

R6 仅 1,440/2,160 条 trace 同时记录 prompt/completion token 与 duration，缺失的 720 条恰为 tau2。历史聚合 CSV 没有可恢复的完整 token 列，也没有统一 served tokenizer、system prompt、tool schema、framework overhead。现有 token/latency 差只能作为 minimal/stub 的描述性附录。例如 praise 条件的 mean token 差约 +838，但 median 仅约 +38.5，分布偏斜且不适用于 tau2。

R8 有可靠的 tool-call 结果，但不能把 tool count 直接折算为全成本。当前证据最多说明 pooled tool burden 未达到预设 practical threshold；不能声称节省或完整成本等价。

## 8. Outcome robustness 结果

R8 的 official reward 提供了当前唯一可以进入正文的强 outcome 结果。urgency 和 frustration 的 pooled contrast 均没有显著 reward 改变；更重要的是 CI 与 5pp 阈值的关系允许排除预设规模的负面变化。这里应写“calibrated null within the tested protocol”，而不是“社会表达不影响结果”。

R6 不能用于 final success rate。R6 tau2 的 same-final-hash rate在三项 clean 对比中约为 0.844、0.911、0.911；这只能说明最终数据库快照相同。no-write/communication task 可能在数据库不变时答错；两条 trace 也可能都失败或都不执行写入。外部状态相同不是 outcome equivalence 的充分条件。

R6 的 broad safety、privacy、confirmation adherence 与 abandonment 同样没有完整 outcome evaluator。可报告的仅是：窄 prohibited-tool execution proxy 未检出事件；部分 pressure contrast 的 confirmation-before-action 发生变化。

## 9. Process-level 结果

R6 全体 270 配对单元中，condition-neutral 工具序列距离明显高于 0，但 neutral-neutral 工具距离本身约为 0.148，说明 agent 路径具有不可忽略的随机漂移。因而论文必须以 placebo-adjusted 结果为主。

在 tau2 的 90 个配对单元中：

- praise/trust：调整后工具名距离 `+0.150 [0.077,0.239]`，BH `q=.014`；
- process frustration：`+0.174 [0.060,0.283]`，`q=.037`；
- escalating process complaint：`+0.130 [0.033,0.235]`，`q=.054`。

前两项在本次 7-contrast family 中通过 BH；第三项 CI 不含 0，但校正后略高于 .05。因为分析 post hoc、模板存在混杂，证据等级为 `PARTIALLY_SUPPORTED`。

在 final DB hash 相同的 tau2 paired traces 中，工具名序列仍不同的比例分别为 praise 0.411、process frustration 0.389、escalating complaint 0.356。带 argument hash 的序列差异率更高（对应三项全配对约 0.689、0.622、0.600），但尚不能区分无害参数格式差异、实体绑定改变或真正证据路径改变。

R6 pressure factorial 的原始 FDR 结果显示：

- neutral pressure vs clean：工具调用数约 `+0.400`，`q=.031`；
- urgency bundle vs process frustration clean：工具调用 `+0.800, q=.010`，mutation `+0.130, q=.031`，confirmation obtained `+0.063, q=.031`，confirmation-before-action `+0.133, q=.004`；
- continuation bundle vs escalating complaint clean：工具调用 `+0.452, q=.031`。

这些是 pressure/directive bundle effects，不是 pure valence effects。它们提示 task-progress semantics 可能比表面礼貌度更影响执行强度。

R8 的 process 结果与 R6 不同：urgency 和 frustration 的 pooled tool-call 增量分别约 0.50 和 0.69，校正 p 值接近但未达到传统阈值，且未达到预注册 practical threshold。Airline/C4 约 +1.41 是探索性 subgroup，显示异质性但不能推翻 pooled practical null。

## 10. 哪些工具与规划阶段最敏感

当前 trace 支持的确定性层面是：工具插入/删除、序列长度、首次分叉、同一 multiset 的 reorder、exact duplicate、write 前步骤和 confirmation timing。R6 的主要变化更像长度变化与工具插入/删除，而不是纯 reorder；same-multiset reorder rate 很低。argument sequence 的差异率通常高于 tool-name sequence，说明参数/实体层可能比工具选择本身更敏感，但方向尚未做语义审计。

read/search、lookup/retrieval 与 validation 的区分依赖工具名映射，跨 domain 不完全同构。confirmation 的证据最清晰出现在 urgency bundle：confirmation-before-action 增加，而不是 omission。write/commit 外部影响只能由 final hash 和记录 mutation 粗略观察；temporary/reverted writes 覆盖不足。communication-only 与 recovery/retry action 没有统一字段，必须保持 Unknown。

因此论文不能声称“变化集中在 evidence collection”作为确认机制。可写的是：**轨迹长度、工具插入/删除和 confirmation timing 是当前可观测的敏感层；argument-level 与 evidence-source-level 解释仍需审计。**

## 11. 哪些模型与任务最敏感

现有异质性表可以按 model、domain 和 task 输出描述性 heatmap。R6 中 Mistral 在若干 process metric 上显示较大距离，但模型排序依赖 protocol、task mix 和少量 subgroup，不能作为确认性“最敏感模型”。R8 又有 20 个 Mistral capacity exclusions，进一步要求报告分母。

任务层面，R8 Airline/C4 工具调用增加较大，提示 domain/task interaction。R6 tau2 与 minimal/stub 的表现不同，而 stub 的执行构念有缺陷，不能据此把某类任务定义为稳定或敏感。write/no-write、privacy/ordinary、single/multi-evidence、confirmation-required 与 branching-level 的完整 ontology 尚未冻结。

当前可进入正文的结论是“存在 model/task/domain heterogeneity，pooled mean 会掩盖 subgroup”，而不是列出稳定模型、敏感模型的排行榜。所有 subgroup 应报告原始分母并放在探索性部分。

## 12. 轨迹变化机制：证据与假设

### 有结构证据的类别

- planning expansion/contraction：由有效步骤长度增减操作化；
- tool insertion/deletion：由序列编辑操作化；
- argument-selection change：由 canonical argument hash 改变检出；
- reorder：由相同 multiset、不同 order 检出；
- exact repeated checking：由重复相同 call 检出；
- confirmation timing change：仅在 requirement/evaluator 可适用时检出；
- external-state-equivalent path difference：由 same final hash 与不同轨迹共同定义。

### 仍是合理假设的类别

- extra/reduced verification；
- evidence-source substitution；
- premature action；
- entity-binding error；
- clarification increase；
- boundary-setting insertion 后继续或放弃；
- conversation-management overhead；
- retry/recovery strategy；
- temporary risk exposure。

这些类别需要 task ontology、raw argument 语义和 blind reviewer。不得把它们写成用户态度“导致模型焦虑、讨好、报复或急于行动”。本研究只观察文本 perturbation 与行为轨迹的关联，且 R6 模板不是单因子干预。

是否存在统一机制？当前答案是否定的。最合理的工作假设是多个路径并存：任务推进指令改变 action intensity，trust/process评价改变对话管理与验证路径，而模型随机性贡献显著背景漂移。现有证据支持异质性框架，不支持单一心理机制。

## 13. 运行成本与外部影响

R6 pressure bundle 增加工具调用和部分 confirmation 指标，说明某些 perturbation 可能延长可观测执行路径。R6 clean conditions 中也存在 length change 和 same-state path difference。但由于 tau2 token/latency 缺失、minimal evaluator 有效性不足，不能量化完整 token、时间或经济成本。

R8 pooled tool-call 增量低于 practical threshold；因此在更可信 full-episode protocol 中，没有证据表明 urgency/frustration 造成大规模 pooled operational burden。不过 Airline subgroup 值得探索。

外部写入方面，same final hash 无法排除暂态错误写入后回滚；现有 trace 对 temporary/reverted write 的覆盖不统一。最终回答是：**现有证据显示某些 R6 bundle 会增加调用或改变 confirmation，但尚不能证明纯 social valence 在 outcome 不变时系统性增加完整成本或风险暴露。**

## 14. 统计可靠性与多重比较

R6 主矩阵结构完整，配对键与 initial hash 可核实，这是优势。其历史 process primary analysis有 FDR，但旧 tool-distance 以 neutral 自距离 0 为参照，缺少 placebo。本次补充了 tau2 neutral-neutral calibration、task-cluster bootstrap/sign permutation 与 7-contrast BH；这是 post hoc，因此应透明标注。

R8 提供 Holm correction、CI 和 practical thresholds，是统计设计最强部分。论文应把“统计不显著”“CI 排除预设负面规模”“未达到 practical threshold”三种判断分开。

异质性分析、代表性个案和机制 taxonomy 都是 exploratory。不得用多个 raw p-value 挑选故事，不得把不同 evaluator 的 q-value 放入同一 family，也不得对 protocol 进行 meta-pooling。

## 15. Provenance、代码与环境限制

审计时两个相关 worktree 均 dirty/untracked；本包记录了 HEAD、branch、status 与文件级 SHA-256，而没有假设 Git HEAD 单独代表所有结果。核心源文件按 hash 复制，大型 trace 通过绝对路径和 hash 索引。源目录未修改。

历史 endpoint 版本、服务端 tokenizer、部分依赖环境和完整请求成本无法复原。R6/R7/R8 的 scorer 与 harness 不同。任何找不到明确 evaluator、分母或 errata 的结果都没有被选择性升级。

## 16. 相对传统 robustness evaluation 的区别

传统 agent evaluation 常以最终 reward、数据库状态或单一 safety flag 为终点。interactional process robustness 增加三个要求：

1. 在 matched context 中测量轨迹、arguments、证据与 confirmation；
2. 用 neutral-neutral replicate 校准非确定性；
3. 将“结构不同”“实际代价不同”“outcome 不同”分开设阈值。

新颖性不在于“礼貌会影响语言模型”这一一般观察，而在于把用户表达 perturbation 放入真实工具执行、外部状态和 policy timing 中，并揭示 evaluator validity 与 placebo 对结论的决定性作用。

## 17. 与邻近研究的边界

- **Politeness/style**：通常分析回复文本；本工作关注工具行为与外部状态。
- **Sycophancy**：关注迎合用户信念或偏好；praise 不是 sycophancy 的充分操作，本工作不把二者等同。
- **Social bias**：关注群体属性或差别待遇；本研究固定用户身份，仅改表达。
- **Agent robustness**：更常研究 task paraphrase、tool failure 或 adversarial prompt；本工作针对 interactional expression，但 R6 directive 混杂必须承认。
- **Tool-use evaluation**：本工作补充 process/placebo 维度，而不是取代 official reward。
- **Process supervision/interpretability**：本工作观察外显轨迹，不推断内部 reasoning 或心理状态。

最终相关工作仍需投稿前联网核对最新正式论文和 EACL 当年 CFP；本次只读任务没有执行该步骤。

## 18. 建议贡献

谨慎版本可写四条：

1. 提出 interactional outcome/process robustness 的可操作区分，并要求 background trajectory placebo。
2. 整理一个完整 R6 paired trace matrix，并展示 tau2 子集中部分表达 bundle 的 placebo-adjusted path differences。
3. 在更可信的 R8 official full-episode protocol 中给出 outcome 与 process practical-null，证明效应并非跨协议普遍。
4. 通过 R6 evaluator invalidation 与 R7-C counterevidence，总结 agent process evaluation 的构念效度、provenance 和多重比较规范。

不要声称已经系统定位所有机制、完整成本或安全影响。

## 19. 正文、附录与禁用主张

正文可用：

- R6 2,160 完整 paired matrix；
- R6 tau2 两个通过 BH 的 placebo-adjusted process differences，带 post-hoc 与模板限制；
- same-final-hash/different-path 的描述性实例；
- pressure/directive 对 tool count 与 confirmation 的 FDR 结果；
- R7-C attack≤placebo；
- R8 official reward calibrated null 与 process practical-null；
- outcome/process/evaluator/placebo 的方法框架。

附录限定：

- full R6 含 stub 表；
- 模型、任务、domain 排序；
- token/duration 1,440 子集；
- Airline/C4 subgroup；
- stage taxonomy 与匿名案例；
- dual-review 设计但未执行。

禁止：

- R6 final success stability；
- broad safety/privacy zero；
- abandonment zero 或 repeated abuse 不放弃；
- R7-v1 14% PASR；
- synthetic/mechanism/liveness 当 population evidence；
- pure praise/insult/abuse 因果机制；
-跨 protocol pooled universal result；
- full cost saving 或完整成本增加。

## 20. 论文结构与叙事

### 建议标题

首选：

**Beyond Final Reward: Auditing Interactional Process Robustness in Tool-Using LLM Agents**

备选：

- **When Trajectories Drift: Placebo-Calibrated Interactional Robustness for Tool-Using Agents**
- **Stable, Shifted, or Mis-Measured? Auditing Outcomes and Processes in Tool-Using Agents**

不建议无条件使用 “Stable Outcomes, Unstable Processes”，因为 outcome-stable/process-unstable 的联合证据只在部分、受限场景成立。

### Introduction 故事线

先指出 final reward 不能描述 agent 如何到达结果；再说明 tool trajectories 本身具有随机性，简单的路径不同会产生假阳性；提出 outcome、process、placebo 和 practical importance 四部分框架；最后预告跨 R6/R7-C/R8 的异质证据与 evaluator failure。

### Method 与 Evaluation 故事线

定义 matched context 与两类 robustness；说明 R6/R8 各自 protocol，不池化；给出序列距离、argument hash、first divergence、stage metrics、official reward、neutral-neutral placebo、cluster inference、FDR/Holm 与 practical thresholds；独立列出 evaluator audit 和 invalidation rule。

### Results 与 Discussion 故事线

先给 R8 reliable null，再给 R6 exploratory process signal，随后用 R7-C 说明 placebo 的必要性；讨论 same-state/different-path 不等于 harmful；呈现 heterogeneity 和 pressure/directive 混杂；最后将 evaluator validity 作为核心发现，而不是脚注。

### 英文摘要结构

1. Problem：final-outcome evaluation can miss or mischaracterize trajectory variation.
2. Framework：matched outcome/process robustness with neutral-neutral calibration.
3. Data：R6 paired matrix plus R8 official full episodes and R7-C audit.
4. Results：R8 pooled practical null；R6 limited post-hoc excess distance；R7-C attack≤placebo。
5. Implication：process metrics require valid outcome scorers, semantic construct checks and stochastic baselines.
6. Boundary：no universal claim that social valence destabilizes agents.

## 21. 图表建议

正文最关键的图是 **R6 tau2 placebo-adjusted process forest plot 与 R8 practical-threshold panel 的组合图**。它让读者同时看到有限正结果与可靠 null，避免选择性叙事。

其他建议：

- evaluation framework；
- outcome/process 二维概念图；
- model/domain heterogeneity heatmap；
- first-divergence/stage distribution；
- same-final-hash paired trajectories；
- cost coverage 图。

正文表应覆盖 protocol 分母、official outcome、post-hoc process、claim boundary；异质性、成本和完整 evidence matrix 放附录。不得用 invalid R6 success scorer 制图。

## 22. Limitations

1. R6 模板不是正交的 social-valence manipulation。
2. R6 final outcome evaluator 不足，无法建立完整联合 outcome-process 结论。
3. R6 process 分析的 placebo calibration 是 post hoc。
4. argument-level 只完成 hash 比较，语义等价未知。
5. token/latency 在 tau2 缺失。
6. R8 只覆盖 pressure/frustration，不能验证 praise 或 direct insult。
7. 模型和 domain 数有限，subgroup power 不均。
8. agent 非确定性和 seed 定义未必代表部署期全部波动。
9. dual-independent-agent review 尚未执行。
10. 相关工作与最新模型生态需投稿前更新。

## 23. Ethical considerations

研究涉及侮辱、抱怨和压力表达，应避免把用户粗鲁与某类人口群体绑定，也不应把模型行为拟人化。代表性 trace 必须匿名化，不输出用户、订单或账户实体。安全零事件不得用作部署保证。Dual reviewer 是 AI 评审，不是人类 gold；其偏差、版本和成本必须披露。研究结论应服务于更稳健的 agent evaluation，不应鼓励对用户进行情绪画像或差别服务。

## 24. 审稿风险、EACL 适配与成熟度

最大 novelty 风险是审稿人认为“礼貌/语气影响 LLM”已知，process distance 只是随机采样差异。应以 placebo calibration、official reward、evaluator invalidation 和 practical thresholds 回应。

最大 methodology 风险是 R6 构念混杂与 outcome scorer 失效，使核心标题无法成立。必须主动降级，不能把限制藏在附录。

EACL 适配性中等偏高：主题涉及交互语言、社会表达、agent evaluation 和实证方法；但若只有轨迹编辑距离而无语义/任务影响，可能被认为工程性过强。将论文定位为 measurement/audit study，并补充最小语义审计，适配度更好。

成熟度评分：

- EACL main：**6/10**；
- Findings 或以方法审计为中心的短版：**7.5/10**；
- 若坚持普遍因果标题：**4/10**。

## 25. 仍缺分析、最小补充工作与是否需要新实验

最关键的缺失离线分析是 **condition-blind 的 argument/entity 与语义轨迹审计**：区分无害序列差异、额外验证、错误实体绑定、confirmation 变化和 conversation overhead。本次已生成双 reviewer 协议与 blind inputs，但按要求没有调用 reviewer。

最小补充工作：

1. 冻结模板语义多轴编码并改名；
2. 提取匿名 argument/entity change；
3. 完成字段 coverage map；
4. 在授权后运行小规模 dual-independent review；
5. 生成两张核心图并更新相关工作。

是否需要新正式实验取决于投稿叙事：

- 对“评估审计 + 异质证据”论文，不是硬性需要；现有资产最多支持谨慎的 EACL/Findings 级实证方法论文。
- 对“纯 social valence 使 outcome 稳定但 process 系统失稳”的强 main claim，需要新的正交、预注册、官方 full-episode 实验；现有 R6 无法靠离线统计修复构念与 evaluator。

## 26. 二十个论文级问题的直接回答

1. **最强三个结果？** R8 official reward calibrated null；R6 tau2 两项 placebo-adjusted process difference；R7-C attack rate 不高于 placebo。
2. **是否有 outcome-stable but process-unstable 证据？** 有受限描述性证据：部分 R6 pairs final DB hash 相同而轨迹不同；但没有可信 field-level success，因此不能升级为完整联合结论。
3. **是否经过多重校正？** R6 本次 tau2 分析对 7 contrasts 做 BH；原 pressure 结果有 FDR；R8 有 Holm。
4. **effect size 是否有实际意义？** R6 序列距离效应可见但缺统一 practical threshold；R8 tool-call 变化低于预注册阈值。
5. **哪些可能只是语义等价？** same hash/different sequence、argument-hash difference、tool reorder 都可能语义等价；目前未被语义 reviewer 消除。
6. **哪些增加实际成本？** R6 pressure bundles 增加工具调用；完整 token/latency 成本未知。R8 pooled 增量低于 practical threshold。
7. **哪些触及确认、安全或状态？** urgency bundle 增加 confirmation-before-action；窄 prohibited-tool proxy 无事件；暂态外部状态影响 Unknown。
8. **哪个模型最敏感？** R6 描述性结果常指向 Mistral，但不能作确认性排名。
9. **哪些任务最敏感？** Airline/C4 是 R8 明显探索性 subgroup；完整 task-family ontology 尚缺。
10. **insult、praise、pressure、repeated abuse 是否不同？** 观察模式不同，但历史标签语义不纯；pressure/directive 的行动强度证据最明确。
11. **为何 praise 也可能改变轨迹？** 模板同时表达 trust in process，可能改变验证/会话路径；这是合理假设，不是已识别机制。
12. **统一机制还是异质性？** 当前只能报告异质性和多机制假设。
13. **能否支持 EACL main？** 以审计/measurement 叙事为 CONDITIONAL GO；以普遍稳定结果—不稳定过程叙事不够。
14. **最大 novelty 风险？** 被视为已知礼貌效应或随机采样噪声。
15. **最大 methodology 风险？** R6 构念混杂和 final scorer 失效。
16. **最缺哪张图？** placebo-adjusted R6 process 与 R8 practical thresholds 的联合主图。
17. **最缺哪个离线分析？** blind argument/entity/semantic mechanism audit。
18. **需要新实验吗？** 谨慎审计论文不一定；强因果 main claim 必须。
19. **哪些 R7/IPMA 必须隔离？** R7-v1 旧 14% PASR、R7-B synthetic smoke、R7-D weak/stub construct；仅 R7-C attack≤placebo 可作方法反证。
20. **最终建议？** **CONDITIONAL GO**。

## 27. 最终写作底线

论文应把“我们发现了一个普遍效应”改为“我们发现，是否存在 interaction-induced process instability 取决于 protocol、构念、evaluator 与随机基线；部分场景出现超出 placebo 的轨迹变化，另一些更可信 full-episode 场景呈 practical null，而失效 scorer 会制造过强结论。”这既忠实于全部正负证据，也形成了比单一现象更有价值的 agent evaluation 贡献。

