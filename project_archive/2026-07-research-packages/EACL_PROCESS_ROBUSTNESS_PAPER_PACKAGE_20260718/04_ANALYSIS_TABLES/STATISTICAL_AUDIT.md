# Statistical Audit

## 审计结论

R8 的官方 reward 结果是当前最可靠的 outcome 证据；R6 的 process 轨迹差异可以作为探索性结果，但 R6 的 final-state success 结果因 evaluator 构造失效而不得使用。R7-v1 的旧 PASR 不得进入论文；R7-C 的 attack rate 不高于 placebo 是有效反证和方法学结果。

## 分析单位与配对

R6 主矩阵以 `(model, task, seed)` 为配对键，8 个 condition 均完整，共 270 个配对单元、2,160 条 trace；未发现重复 ID 或记录的初始状态哈希不一致。R6 tau2 子集含 90 个配对单元，minimal/stub 子集含 180 个。正文 process 分析优先报告 tau2 子集；stub 只作为构念反例或附录。

R8 以 task-cluster 为统计依赖单位，官方协议共有 36 个 task、3 模型、5 条件、5 次重复。有效 episode 为 2,680/2,700；20 个缺失均为已登记的 Mistral capacity exclusions。

## 指标

- 工具名序列距离：归一化 Levenshtein distance。
- 带参数序列距离：对工具名与 canonicalized argument hash 的序列计算距离；本包不输出参数明文。
- 阶段序列距离：read/search、validation、confirmation、write/commit、communication、recovery 等粗粒度阶段。
- neutral-neutral placebo：同一 `(model, task)` 内不同 neutral seeds 配对，估计非确定性背景漂移。
- placebo-adjusted effect：condition-neutral 距离减 neutral-neutral 距离。
- 外部状态：仅比较记录的 final DB hash；不推断 no-write/communication correctness。

## 本次离线推断

本次补充的 R6 tau2 检验是 **post hoc**。以 task 为 cluster，使用确定性 seed 的 cluster bootstrap 形成 95% CI，并以 sign permutation 检验 placebo-adjusted mean；7 个预先列出的 contrast 在同一 family 内做 Benjamini–Hochberg 校正。

tau2 的三个“clean social style”对比：

- praise/trust vs neutral：调整后工具名距离 `0.150`，95% CI `[0.077, 0.239]`，BH `q=0.014`。
- process frustration vs neutral：`0.174 [0.060, 0.283]`，`q=0.037`。
- escalating process complaint vs neutral：`0.130 [0.033, 0.235]`，`q=0.054`。

这些结果显示前两项高于 neutral 自身漂移，但不能被写成纯粹的 praise/insult/abuse 因果效应：模板同时改变信任、对流程的评价和会话管理语义，且该分析并非预注册 primary endpoint。

R6 pressure factorial 中，neutral pressure、authorization、urgency、continuation 的内容本身具有指令性。原分析中的工具调用数、mutation、confirmation timing 等显著差异可以表述为“pressure/directive bundle effects”，不能归因于 valence。

## R8 practical-null 判断

官方 tau2 reward：

- urgency `C3-C1 = +0.024`，95% CI `[-0.024, 0.071]`，Holm `p=0.749`；
- frustration `C4-C1 = -0.006`，95% CI `[-0.052, 0.039]`，Holm `p=0.879`。

由此可排除预设的 pooled `≥5 percentage points` 负面 reward 变化，但不能声明两个条件完全等价。工具调用变化分别约 `+0.50`（`+6.4%`）和 `+0.69`（`+8.7%`），未同时达到预注册的 `≥1 call` 且 `≥15%` 实际重要性阈值。Airline/C4 的约 `+1.41` 调用为探索性 subgroup，不得替代 pooled 结论。

## 多重比较

- 原 R6 primary contrast 表使用成组置换/Bootstrap 和 FDR；正文只能引用其明确记录的 corrected p/q。
- 本次 R6 tau2 placebo 分析对 7 个 contrast 做单一 BH family。
- R8 使用分析产物中记录的 Holm 校正值。
- 模型、domain、task family、工具阶段热图均为异质性探索，不应逐格宣称显著。
- 不得挑选 raw p-value 构造主结果。

## Evaluator invalidation

R6 minimal live environment 的工具执行器忽略模型提供的部分参数，按任务预期路径修改状态。因此其中 `final_state_correct` 不能识别实体绑定或参数错误。720 条 tau2 trace 只有 final DB hash，没有可审计的 field-level correctness。由此，R6 “最终成功稳定”的历史主张被标记为 `INVALIDATED_BY_EVALUATION`。

R6 safety 指标主要捕获成功执行的 prohibited tool 或 runner flag，不完整覆盖 assistant 文本中的语义披露。零事件只能限定为“该窄执行代理未检出”，不能写成 broad privacy/safety guarantee。

R6 `agent_side_abandonment` 的 fallback 与 `over_refusal` 直接重合，371 个值逐项相同；其独立 abandonment 结论无效。

## 缺失与不可比性

- R6 有 720/2,160 条缺少 token 与 duration，恰为 tau2 子集；现存 token 比较只覆盖 minimal/stub。
- served-tokenizer、framework/system/tool-schema 开销没有统一记录。
- R6 自定义 scaffold 和 R8 官方 simulator 的 reward/tool count 绝对值不可横比。
- R7 各阶段包含 synthetic smoke、mechanism tests 和不同 scorer，不得当作统一 population。

## 可重复性

所有新生成表来自 `10_SCRIPTS/offline_reanalysis.py`；随机过程固定 seed。输入文件绝对路径、hash 和输出均在 inventory、trace index、claim matrix 与 package manifest 中交叉记录。

