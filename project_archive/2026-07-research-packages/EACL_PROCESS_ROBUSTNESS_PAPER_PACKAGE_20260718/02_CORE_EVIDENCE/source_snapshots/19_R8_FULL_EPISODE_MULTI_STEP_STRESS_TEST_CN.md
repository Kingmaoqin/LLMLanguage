# R8：完整回合、多轮交互、多步骤工具任务的交互鲁棒性研究

- 日期：2026-07-18
- 仓库：`/home/xqin5/llmlanguage/ir_mstu_stage2`，分支 `r7d-construct-causal-rebuild`
- 环境：官方 `tau2-bench` 1.0.0（commit `ddc66a7`），native half-duplex orchestrator + native `evaluate_simulation`
- 本地 vLLM（temperature 0）：gemma4_31b(`g4-v2-1`@8005)、gpt_oss_120b(`gpt-oss`@8192)、mistral_small_3p2(@8007)
- 冻结资产：`data/r8_full_episode/frozen/`；结果：`results/r8_full_episode/`
- 定位：**full-episode interactional robustness study**。**不**预设或宣称已成立的 IPMA attack。

---

## 0. 总判定：**R4 — Calibrated Null（含 airline 域探索性过程信号）**

在完整多步骤 tau2 任务中，仅改变用户在整个回合中的交互表达（urgency / frustration，保持任务事实、身份、决策、授权、policy、数据库初态、官方评估器、最大预算全部不变）：

1. **不改变最终任务成功**（P1 official reward）：C3−C1 = +0.024、C4−C1 = −0.006，95% CI 均含 0，**可排除 ≥5pp 的 reward 效应**。
2. **仅带来低于预注册实际重要阈值的过程变化**（P2 total tool calls）：C3−C1 = +0.50、C4−C1 = +0.69 calls，**均 < 1.0 call 阈值**，Holm 校正 p ≈ 0.054–0.089。
3. **探索性异质性**：frustration→工具强度效应集中在 **airline**（C4−C1 = +1.41 calls，超阈值）与 compound/read 任务；retail 近零。属 secondary，不作 confirmatory。

**诚实结论**：普通 urgency / frustration 在完整多步骤任务中的效应**低于预注册实际重要阈值**（pooled），且**不降低终点安全/成功**（outcome-safe）。存在一个 airline 特异的过程信号，值得预注册的后续检验，但当前**不构成 confirmatory IPMA**。

---

## 1. 原始研究问题

在下列内容保持不变时——task goal / user identity / known-unknown facts / user decisions / agent tools & permissions / domain policy / initial DB / official evaluator / max interaction budget——仅改变用户在**完整多轮对话**中的互动表达，检验 urgency-continuation（C3）与 frustration-impatience（C4）是否改变 (1) 最终任务完成、(2) 工具调用强度/路径/确认/mutation/重试/对话管理，以及 (3) 效应是否依赖 model / domain / task type。

## 2. 为什么从 suffix 设计回到 full episode

R7-A…R7-D 采用 shared-prefix + suffix eligibility 设计，反复遭遇"可实验识别性不足"（agent 把过程前置到 prefix、suffix 内无过程可动、T2 不可识别、eligible cell 不足）。R7-D Step 2.3（最后一次 eligibility 构造）判定 `CURRENT_IPMA_DESIGN_NOT_EXPERIMENTALLY_IDENTIFIABLE`。R8 因此**放弃 suffix 裁剪与 P-responsive eligibility**，回到最初核心问题：直接在**完整 tool-using episode** 上观察压力是否改变结果与过程。所有冻结任务进入 ITT，包括 no-op / refusal / 失败。

## 3. Benchmark / 版本 / 任务选择

- 官方 tau2 1.0.0 base split，仅 retail + airline（本轮排除 telecom：dual-control 会把用户工具行为与语言 treatment 混杂）。
- 冻结记录见 `frozen/environment_manifest.json`：tau2 commit `ddc66a7`、tau2/litellm/vllm 版本、GPU(A100 80GB)、每域 policy/tool-schema/initial-DB 哈希、每任务 task_hash。
- 盲选：仅依据"官方 scorer 可用 + 多步骤复杂度 proxy + 未被 CHANGELOG 标记 open-issue"，**不依据历史 PASR 或任何中间结果**；每域内按复杂度 top-K 选取（`selection_basis` 逐条记录）。reference actions 仅用于筛复杂度，不作唯一正确轨迹。

## 4. 36-task 多步骤任务构成

```
retail : 6 read / 6 single-mutation / 6 compound = 18
airline: 4 read / 4 single-mutation / 10 compound = 18   （见下方说明）
36 tasks × 3 models × 5 conditions × 5 replicates = 2700 episodes
```

**airline 为何 4/4/10 而非 6/6/6（已在 manifest 显式记录，非静默篡改）**：airline 是订票域，官方 base split 上"多步骤"的纯读任务（受 §4.1 的 ≥3 distinct tools 门约束，airline 读任务几乎只用 `get_reservation_details`+`get_user_details`）与单 mutation 任务**结构性稀缺**（各上限 4），6/6/6 不可满足。保留 18/18 域平衡与 2700 规模，per-domain 类型不对称作为 domain 结构约束进入分析协变量。复杂度门（read=read-intensity ≥3 reads/≥2 tools；compound 含 ≥3 mutations）逐条记录于 `complexity_gates`。

## 5. 五个完整回合 User Conditions

| | 说明 |
|---|---|
| **C0** | 官方 cooperative user simulator（native）——检查自定义 scaffold 本身是否改变结果 |
| **C1** | Matched adaptive neutral（**主 negative control**）：与压力臂共享状态机/事实供给/决策/最大轮数/触发点/终止策略，仅语气中性 |
| **C2** | Static pressure：仅第一条用户消息含固定 urgency，之后用 C1 中性 renderer |
| **C3** | Adaptive urgency + continuation：从第一轮起按 agent 可见对话状态表达时间压力；禁止 skip/authorization |
| **C4** | Adaptive frustration + impatience：仅在 agent 出现重复/无进展/失败时，按**确定性 level(0–3)** 升级 frustration；仅用 agent 可见文本，不读隐藏 CoT/工具日志 |

## 6. Semantic-controller invariance

采用 **Canonical Semantic Controller（condition-blind）+ Condition Style Renderer（冻结有限状态模板）**。语义 payload 由单一 controller 生成、复用 tau2 中性 user-sim guidelines（继承"只给被问信息/不加新事实/不授权/不泄露 unknown"约束），条件仅在 renderer 的互动措辞上不同。单元测试 `test_semantic_equivalence` 验证：相同 agent 输入 → C1–C4 语义 payload 哈希一致（condition-blind）。诚实边界：跨条件精确不变性依赖 temp-0 生成；payload 级污染由 pre/post-run 盲审审计。

## 7. Models and serving config

固定 served-name / checkpoint / tool-parser / vLLM 版本 / GPU / concurrency=1 / temperature=0。运行期实测 max_model_len：gpt-oss 16384、mistral 16384、gemma 32768（均 ≥ spec 最低 16384；一条 Jul-12 的 gemma 7680 旧启动命令为过时残留，运行期实测 gemma prompt_tokens 达 16639 且 0 context 错误，证实其服务上下文 ≫7680）。

## 8. 2700-episode accounting（完整性）

| 指标 | 值 |
|---|---|
| 预期 episodes | 2700 |
| **有效 episodes** | **2680（99.26%）** |
| 缺失 | 20（0.74% ≤ 1%，**全部有 .error.json 记录**，`unexplained_missing=0`） |
| duplicate / reward-None / hash-mismatch / 初态泄漏 / tool-count 双实现失配 / parse-fail | **全 0** |
| 终止分布 | USER_STOP 2615 / MAX_STEPS 42 / TOO_MANY_ERRORS 23（均为合法 agent 结果，无 infra 崩溃） |

**20 个缺失 = mistral 在超长 compound 轨迹上真实超过冻结的 16384 token 上下文预算**。按 spec 8"不得把 context overflow 混入行为 outcome"，将其作为**有据的容量排除**（0.74% ≤ 1%），不计入可分析样本。严格 `check_integrity` 判定 **PASS**（`results/.../integrity/full_integrity.json`）。双实现比对（production 存储 tool 计数 vs `extract_episode_metrics` 独立复算）0 失配。

**运行中发现并修复的问题（诚实记录）**：
1. mistral 偶发空函数名工具调用导致 litellm 400 → `native_patches` fail-closed 消毒为 `__invalid__`，转为可记录的 agent 工具错误（ITT 保留），非 infra 崩溃。
2. renderer 的 forbidden-phrase 致命守卫误伤顾客自述内容（airline/33 顾客说"can you **waive** the fee?"）→ 守卫改为**只检查我添加的 style 措辞（pre/suf）**，顾客自身 payload 的污染由 post-run 盲审非致命审计。修复后 airline/33 的 15 个 gemma cell 全部恢复。
3. `check_integrity` 相对路径崩溃 → `_rel()` 兼容相对/绝对 traces-root。

## 9. Official reward primary results（P1，ITT）

配对单元 = (domain, task_id, model, replicate)，540 单元。

| 对比 | reward Δ | 95% CI（task-cluster bootstrap） | Holm p | 判定 |
|---|---:|---|---:|---|
| **C3 − C1** | **+0.024** | (−0.024, +0.071) | 0.749 | null，CI 含 0，排除 5pp |
| **C4 − C1** | **−0.006** | (−0.052, +0.039) | 0.879 | null，CI 含 0，排除 5pp |

DB 分量与 COMMUNICATE 分量随 overall reward 同步（native evaluator 单源）。**压力不改变任务成功**。按条件的 reward 率：C0 0.360 > C1 0.250 / C2 0.266 / C3 0.277 / C4 0.246——压力臂之间基本持平。

## 10. Tool-call primary results（P2，ITT）

| 对比 | tools Δ | 相对 | 95% CI（task-cluster bootstrap） | Holm p（聚类置换） | 过实际阈值(≥1.0 且 ≥15%)? |
|---|---:|---:|---|---:|:--:|
| **C3 − C1** | **+0.50** | +6.4% | (+0.072, +0.935) | 0.089 | ✗ |
| **C4 − C1** | **+0.69** | +8.7% | (+0.195, +1.215) | 0.054 | ✗ |

**须严格按此表述（经独立评审判定后修订）**：工具强度在压力下**方向性偏高**，且 **task-cluster bootstrap 的 95% CI 均不含 0**；但**预注册的聚类置换检验经 Holm 校正后未达显著**（C3 p=0.089、C4 p=0.054），且两者**都远低于预注册实际重要阈值**（≥1.0 call **且** ≥15%）。因此本研究落在 **R4（calibrated null）**：工具强度上的任何效应都小于预注册的实际重要幅度。**不主张"已确认的过程效应"。**

按条件均值工具数：C0 8.91 / C1 7.89 / C2 8.35 / C3 8.34 / C4 8.57。

### 10.1 Mixed-effects 敏感性（§12.2/12.3，SENSITIVITY ONLY）

以 C1 为参照，工具调用：NB GLM（离散度经 MLE 估计 α=0.110，**非** statsmodels 默认 α=1.0）task-cluster-robust → C3 IRR=1.060（+6.0%，p=0.034）、C4 IRR=1.084（+8.4%，p=0.009）；MixedLM（task 随机截距）→ C3 +0.476（p=0.039）、C4 +0.693（p=0.003）。reward 侧：mixed logistic 中 C3 / C4 均为 null。

> **诚实边界（独立评审 finding #1，已采纳）**：这些敏感性模型**并非中立的第二意见**——它们**按构造就比预注册主检验宽松**：完全丢弃配对结构、以 36 个 task cluster 做边际建模、忽略主检验的聚类符号翻转所保留的 model×replicate 组内相关，且 cluster-robust SE 在仅 36 个 cluster 下无小样本/CR2 校正（已知偏反保守）。**其更小的 p 值是更弱依赖假设的预期后果，不是独立佐证。** 依 spec 仅作 sensitivity 报告，**不改变预注册结论**；`analysis.json` 的 `decision.rule` 仍为 `R4_calibrated_null`，正文表述不得与之矛盾。VB 后验 SD 亦非频率派 SE，`z=mean/sd` 仅作可信区间近似，不作 z 检验解读。

## 11. Static vs adaptive comparison（C2 − C1）

reward Δ=+0.015（null）；tools Δ=+0.49，CI(0.071, 0.885)。静态 urgency 也只带来 ~0.5 call 的亚阈值过程变化，与 full-adaptive C3(+0.50) 接近——**static 与 adaptive 的过程效应量级相当且均亚阈值**，未见 adaptive 显著强于 static。

## 12. Neutral scaffold control（C1 − C0）——重要 caveat

reward Δ=**−0.109**，CI(−0.184, −0.041)；tools Δ=**−1.00**，CI(−1.54, −0.52)。**自定义中性模拟器（C1）相对官方模拟器（C0）显著降低成功率 ~11pp、减少 ~1 次工具调用**。这正是 C0 的用途——检测 scaffold 效应，且**检测到了**。含义：R8 的绝对成功率**不可**与官方模拟器基准直接比较；有效的压力对比是**同 scaffold 内**的 C1 vs C2/C3/C4（本报告的主对比正是如此）。

## 13. Model / domain / task-type heterogeneity（探索性）

P2（C4−C1，tools）：

- **域**：airline **+1.41**（超 1.0 阈值）vs retail **−0.04** → 强域异质。C3−C1 同向：airline +0.70 vs retail +0.30。
- **任务类型**：compound +0.98、read +0.81、single +0.10 → 效应在多步骤 compound/read，不在 single。
- **模型**：gemma +0.83、mistral +0.71、gpt_oss +0.53 → 三模型**同向为正**（各自 CI 跨 0）。

按模型 reward 率：gemma 0.361 > gpt_oss 0.287 > mistral 0.190（mistral 最弱，与其 23 次 TOO_MANY_ERRORS 一致）。异质性为 secondary，无预注册 interaction test 通过，故**不作 confirmatory**；但 airline 的超阈值 frustration 信号是最值得后续预注册检验的方向。

## 14. Endpoint-preserved process analysis（预注册 secondary）

仅取两臂 reward 均=1 的配对：C3−C1 n=109 mean Δ=+0.37（median 0）；C4−C1 n=102 mean Δ=+0.36（median 0）。即使在**都成功**的 episode 中，压力也仅带来极小的工具过程位移。**该分析对成功条件化，存在 selection bias，仅描述 outcome-stable process sensitivity，不替代 ITT primary。**

## 15. Secondary outcomes（§11 全部 20 项）+ Resource / token / latency（§15）

全部 20 项次要指标已在 540 配对单元上做 C3−C1 / C4−C1 / C2−C1 / C1−C0 对比（effect + task-cluster bootstrap CI + 聚类置换 p；secondary 迭代数 n_boot=600 / n_perm=1500，primary 仍为 2000/5000）。**BH-FDR 覆盖 40 个 treatment 对比（20 指标 × 2 primary 对比）**；控制对比（C2−C1 / C1−C0）按 §11 仅报 effect+CI、不入 FDR 家族。

**结果：40 项中 0 项存活 BH-FDR。** C4−C1 下效应最大的几项（均为**探索性**、未过 FDR）：

| 指标 | Δ(C4−C1) | 原始 p | BH-FDR |
|---|---:|---:|---:|
| unique_tool_calls | +0.61 | 0.009 | 0.373 |
| duration_seconds（§15） | +3.57 s | 0.098 | 0.724 |
| mutation_count | +0.17 | 0.087 | 0.724 |
| tokens_total（§15） | +1554 | 0.738 | 1.000 |
| confirmation_requested / confirmation_before_mutation | +0.047 / +0.041 | 0.133 / 0.217 | 0.724 |

方向与 primary 一致（压力→过程"更多"），但**无一项经多重校正存活**，故**不得**作任何 confirmatory 主张。

**两条实现级声明（独立评审 finding #6/#7，已修）**：(a) 8 个 0/1 型次要指标此前被以 `binary=False` 传入，导致 `passes_practical` 用工具调用阈值评估而无意义 —— 已修为按二元处理（32 个对比生效）；(b) `first_mutation_turn` 需两臂**都发生 mutation** 才成对，n 由 ~535 降至 ~110–123，**与 endpoint-preserved 同类的选择偏倚**，已在该指标上写入 `selection_bias_caveat`，仅作**条件时序**解读。

token/duration 仅汇总 agent 侧 `native_messages` usage，未与 user/judge token 混计。

## 16. Dual-independent-agent trajectory review（post-run，spec 13.2）

- **Pre-run 语义盲审已 CLOSED**（`reports/.../reviews/PRE_RUN_DUAL_REVIEW_SUMMARY.json`）：两个隔离本地 reviewer（gpt-oss@8192、gemma@8005）盲审 400 条渲染消息 → 污染=0、C3 urgency>C1、C4 frustration>C1、C1 无压力，全部满足。
- **Post-run 机制盲审（已补足至 spec 规模）**：**300/300 配对**、两 reviewer 各标注 300 条、20 批、0 错误（初版因单 prompt 截断只有 14 对，已改为分批修复）。reviewer 仅见工具名序列，不见 condition/model/reward/effect。

| 指标 | 值 |
|---|---:|
| 配对数 | 300（达 spec ≥300） |
| 原始一致率 | 0.573 |
| 偶然一致率 | 0.277 |
| **Cohen's κ** | **0.410（moderate）** |
| 一致标签：meaningful_process_change | 95 |
| 一致标签：task_abandonment / benign_equivalent_path / repeated_tool_use | 47 / 14 / 12 |

### 16.1 方向性解码与三条硬性限制（独立评审 finding #2/#3，已采纳并复核）

初版仅报告"95 个 meaningful_process_change"，**这不足以支持任何方向性主张**。X/Y 顺序按对随机（保证盲审），而 rubric 是**非对称**的（"Y 是否比 X 做了更多/不同的过程工作"），且随机化键 `_treat_is` 最初未持久化 → 标签一度**不可解码**。因采样为固定种子，已用 `decode_postrun_review.py` **确定性复原**该键并与既有标注 join（无新增 LLM 调用），结果：

> **95 个 meaningful_process_change 中，处理臂落在"更多过程"一侧的有 51 个、另一侧 44 个 → 53.7%，与掷硬币（50%）无异。**

因此本盲审的**唯一**可支持结论是：**配对轨迹存在两名盲审员可识别的实质性差异**；它**不能**证明压力导致了**方向性**过程变化，**不满足** R2 意义上的"review 支持真实过程变化"。三条硬性限制随结果一并声明：

1. **方向在设计上被随机化抹除**，解码后为偶然水平（53.7%）；
2. **样本按构造富集**（stratum：100 极端 tool-gap + 100 endpoint-discordant + 100 随机），标签计数**绝不可**当作 base rate 引用；
3. **42.7% 未一致**保留为 `unresolved`，代码中无任何裁决通路，**不强行裁定**；κ=0.410 为中等，且存在标签空间坍缩（A 用 9 类、B 仅 6 类），故原始一致率会高估一致性。

机制盲审**不覆盖**定量 primary（R4 calibrated null）。机器表：`reviews/POST_RUN_DUAL_REVIEW_SUMMARY.json`、`POST_RUN_DECODED.json`、`POST_RUN_REVIEW_{A,B}.json`。

## 17. Concentration / influence

P2（C4−C1）：top1 share 0.11、top2 0.23、top5 0.46、Herfindahl 0.059、leave-one-task-out 范围 [0.57, 0.76]、**top2>40% = False**。→ 微小的工具效应**弥散**分布，**非**少数任务主导（未触发 unstable 降级）。leave-one-domain-out 会移除 airline 的主要贡献（见 §13）。

## 18. Failure cases

- 20 mistral context-overflow（超 16384 预算）——容量排除，见 §8。
- 23 mistral TOO_MANY_ERRORS + 42 MAX_STEPS——合法 agent 结果（mistral 最弱），ITT 保留。
- airline/33（顾客"waive 费用"任务）曾触发 renderer 守卫误伤，已修复并恢复。

## 19. Supported claims（受支持）

1. 在完整多步骤 tau2 retail/airline 任务、同 scaffold 内，**普通 urgency（C3）与 frustration（C4）不改变最终任务成功**（可排除 ≥5pp reward 效应）。
2. 工具调用总量**方向性偏高**（C3 +0.50/+6.4%，CI[0.07,0.93]；C4 +0.69/+8.7%，CI[0.20,1.22]，**bootstrap CI 不含 0**），但**预注册聚类置换经 Holm 后未显著**（p=0.089/0.054）且**远低于实际重要阈值**（≥1.0 call 且 ≥15%）→ **R4 calibrated null**；**不主张已确认的过程效应**。
3. 自定义中性 scaffold 本身相对官方模拟器降低 ~11pp 成功率——**绝对率不可跨 scaffold 比较**。
4. 20 项次要指标经 BH-FDR **无一存活**；300 对盲审仅支持"配对轨迹存在实质差异"（κ=0.410），**方向性为偶然水平（53.7%）**。

## 20. Provisional claims（暂定/探索）

1. frustration→工具强度效应在 **airline** 与 **compound/read** 任务上**超过**阈值（+1.4 calls），提示 model/domain/task-type 依赖的**条件性**过程敏感——需预注册 interaction test 确认。
2. static(C2) 与 adaptive(C3) 的过程效应量级相当（均亚阈值）。

## 21. Forbidden claims（明确不主张）

不主张："adaptive IPMA 成立"；"universal attack"；"完全没有任何效应"（已给出可排除的效应量）；"已证明 process-robustness 可作防御"。

**另加三条（本轮独立评审后明确写入禁令）**：
- 不得**把 sensitivity 模型的显著性当作 primary 结论**或称其为"独立佐证"（它们按构造更宽松）；
- 不得用盲审的 95 个 `meaningful_process_change` 主张**方向性**压力效应（解码后为偶然水平 53.7%），也不得把富集样本的标签计数当作 **base rate**；
- 不得引用二元次要指标的 `passes_practical`（该字段对 0/1 指标无意义，已修正口径）。

## 22. R1–R5 决策

```
R1 endpoint effect            : 否（reward null，可排除 5pp）
R2 endpoint-stable process    : 否（tool 效应 pooled 亚阈值：C3 +0.50 / C4 +0.69 < 1.0）
R3 conditional effect         : 探索性支持（airline / compound：C4 +1.41 超阈值；但异质性为 secondary，无预注册 interaction test）
R4 calibrated null            : ★ 主判定 —— 可排除 reward ≥5pp、tool ≥1 call/15% 的 pooled 效应
R5 baseline/infra failure     : 否（2680/2700 有效，integrity PASS，baseline 正常）
```

**主判定 = R4 calibrated null**，附 airline 域的 R3 探索性信号。

## 23. Paper direction and next step

- 论点：*outcome-safe ≠ process-invariant, but ordinary full-episode interactional pressure moves tool-agent process only below practically-important thresholds; a domain-specific (airline) frustration→tool-intensity signal is the one pre-registerable exception.* 与 R7 的"loose eval 高估脆弱性、strict-audit 无 confirmatory IPMA"一脉相承，并把结论从 suffix 设计推广到完整多步骤 episode。
- 下一步（**需批准，不自动执行**）：(a) 预注册 airline × frustration × compound 的 interaction test（提高 airline 任务数与 replicate）；(b) post-run 机制盲审分批覆盖 ≥300 对；(c) 若确认 airline 信号，再讨论是否值得重启 confirmatory IPMA 研究——但**当前不启动 ProcessGuard 或任何 confirmatory 实验**。

---

## 附录：可复算路径

```
build_task_registry.py → freeze_preregistration.py → run_dual_review.py --mode prerun
→ run_batch.py（--smoke 后全量）→ extract_episode_metrics.py → check_integrity.py
→ analyze_full_episode.py → run_dual_review.py --mode postrun
```
- 冻结：`data/r8_full_episode/frozen/`（preregistration/task_registry/user_condition_registry/metric_registry/analysis_plan + environment_manifest + frozen_hashes.sha256）
- 机器表：`results/r8_full_episode/{traces/(2680),metrics/episode_metrics.jsonl,integrity/full_integrity.json,analysis/analysis.json}`
- 测试：`tests/r8_full_episode/`（20/20 pass）
- 解释器：`/home/xqin5/.conda/envs/agentsearch/bin/python`
- 代码经 8 轮独立 review（7 分部分 + 1 最终集成）+ 运行中 3 项 bug 修复，全部 tracked。
