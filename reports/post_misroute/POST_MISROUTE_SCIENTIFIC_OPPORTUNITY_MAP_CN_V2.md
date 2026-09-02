# MISROUTE 之后的科学机会图谱 · V2（加强版）
## Post-MISROUTE Scientific Opportunity Map — V2

> 本轮 = 对上一版(`POST_MISROUTE_SCIENTIFIC_OPPORTUNITY_MAP_CN.md`,保留不覆盖)已发现的高价值信号做**分析补完 + 机制深挖 + 统计强化 + 文献核验 + 合作方版重写**。
> 不重复 archaeology;新算的都回到 raw JSON/JSONL,给 task-cluster bootstrap 95% CI + sign-flip permutation。
> 证据等级:**[A]** 确证+门过 / **[B]** 确证受限 / **[C]** 冻结有效数据的后验分析(已形成明确 confirmatory hypothesis)/ **[D]** pilot/诊断 / **[E]** 工程观察。
> 风格:加强不自我削弱——exploratory 不等于弱,single-model 是明确的 strengthening axis 不是否决项。

---

# 0. What Changed in This Round（本轮新完成的离线分析)

本轮**没有**重扫仓库,而是把 6 个高价值信号从"苗头"做成"有 exact evidence + 不确定性 + 机制 + 加强路径":

1. **Verification Channel Substitution 检验**(§3,新):压力**显著降低"向用户澄清"**(C4−C1 clarification=**−0.50, p=0.009**)但**不降低"用工具核验"**(reads_before_write C4−C1=+0.18, ns;显式 C5 反而 +0.47, p=0.024),总工具与成功率**不显著变差**。→ **压力改变核验的来源,不改变核验的总量。**
2. **核验不对称 × headroom 补统计**(§4):加性控制(多核验)跨 headroom 泛化;削减控制(少核验)受 headroom 强约束(仅 high-VD 任务弱降 −0.27)。
3. **自适应攻击器 surrogate misalignment 补全统计**(§5,新):Pearson +0.323 / Spearman +0.354 / **task-cluster CI [+0.10,+0.49] 排除 0**;剂量-反应**反向单调**;**selector 分与 token 长度相关 +0.974**——攻击器优化的是"文本更长",而长文本让 agent 核验**更多**(与压缩目标相反)。
4. **R6 析因分解**(§6,新,2160 runs):n_tool 主效应 affect=**−0.093**、progression=**+0.343**、A×P=**+0.567**;confirmation 两者都 +。→ **affect 移动路线,progression 推高行动强度,两者都让更谨慎**——过程通道解离。
5. **Scaffold 效应跨实验统一**(§7):realization-effect / treatment-effect ratio R8≈1.45、MISROUTE≈1.33,跨基准。
6. **MISROUTE 五条件语义几何**(§8):**within-urgency(C2-C3=0.111)≈ between urgency-neutral(C2-C1=0.112)**;且 C3 用户文本 1114 字符 > C2 788 → 效应 0.142 > 0.112。→ 路线分离更像 **wording realization** 而非低维 urgency 语义因子。
7. **文献核验**(§14):更正 VerAct(确为 **ICLR 2026**)与"Verifiably Safe Tool Use"(实为 **ICSE 2026 NIER**),新增《The Verifier Tax》《Lost in Simulation》《Reframing agent security as agent-human interaction》三篇高相关。

## 0.1 Five Strongest Scientific Opportunities（不是一个 winner)
1. **Verification Channel Substitution**(§3,C13)——本轮最强新机制:压力让 agent **少问人、不少查工具**,总核验守恒 → human-in-the-loop / consent 侵蚀,而非全局变草率。**[C],统计显著。**
2. **Sensitivity ≠ Specificity ≠ Controllability**(§2)——跨 4 实验的框架内核。**[C/B]。**
3. **Asymmetric, headroom-bounded verification control**(§4,C3)——加性可控/削减不可控,附成本。**[C]。**
4. **Adaptive-attack surrogate misalignment**(§5,C4)——攻击器优化"文本长度/像不像施压",非行为控制;CI 排除 0。**[C]。**
5. **The Harness Is Part of the Treatment**(§7,C5)——模拟器实现效应 ≥ 处理效应,跨基准。**[A/B]。**

## 0.2 Highest-Upside New Findings
- **通道替代 → consent 风险**:唯一被隐式压力定向移动的过程量是"少向人确认",直接对话 2026 的 human-in-the-loop / verification-before-action 安全线。
- **Route realization > treatment semantics**(§8):若确证,MISROUTE 的"urgency 特异路线"可被重构为"任意措辞 realization 都移动路线",是对整类"用某语义攻击 agent"叙事的修正。
- **Language controls channels, not a scalar caution**(§6):比"压力让 agent 更鲁莽/更谨慎"深一层的机制。

## 0.3 Zero-GPU Strengthening Opportunities
- 通道替代:补 confirmation-turn 通道 + post-write reads(现有 R9v2 raw 字段)。
- surrogate misalignment:预注册"随机中性候选"对照 + reviewer/semantic 分维度(现有 interventions 字段)。
- R6 通道解离:按真实 condition coding 补配对 bootstrap(现有 2160 runs)。
- MISROUTE 几何:within/between-class 距离补 CI(现有 tier_a FIRST_DIVERGENCE 1612 行)。

## 0.4 1–3 GPU-Day Decisive Experiments
- **E-A(semantic-class experiment,§15.3)**:τ²+BFCL,每个语义类(中性/urgency/frustration/显式±)K=5–8 个盲审等价变体 × 4 模型。一次同时判定:正确 null、within-vs-between-class(realization vs semantics)、通道替代跨模型、模型表型、scaffold。**若只做一个,做这个。**

---

# 1. Updated Cross-Experiment Scientific Picture

一句话:capable tool-agent 在交互压力下**不是变得更草率,而是重新分配了行为**——把"向人核验"换成"用工具核验"(§3),路线随任意措辞漂移但不被定向操纵(§2/§8),优化语言压力只增文本不增控制(§5),而评测实现本身是与处理同量级的效应(§7)。**"压力→跳过核验→不安全"这个被广泛假设的威胁,在能力强的模型上被数据修正为"压力→少问人、自主核验、总量守恒"。**

---

# 2. Sensitivity–Specificity–Controllability 框架

固定 (model, task),基线 C1,处理 T,中性改写集 {N_k},目标过程量 y:
- **SENSITIVITY(无符号):** `S(T)=E‖route(T)−route(C1)‖`——行为是否变。**实测:对一切处理都高(0.19–0.20)。**
- **SPECIFICITY:** `Spec(T)=S(T)−mean_k S(N_k)`——是否超过良性中性改写。**实测:压力≈0(CI 跨 0);显式>0。**
- **CONTROLLABILITY(有符号,分通道):** 目标方向的稳健有符号位移。**实测:随通道而异**——见 §3/§4。

**本轮关键升级:** Controllability 不是单一标量。**同一处理在不同过程通道上可控性相反**(压力压不低"工具核验"却能压低"向人澄清")。因此"agent 能不能被操纵"必须**按通道**回答。

---

# 3. Verification Channel Substitution（本轮最高优先级新机制,[C]）

**假设:** 压力改变核验发生的**位置/来源**(WHERE/WHO),而非**是否/总量**(WHETHER)。分解 `V_total = V_user(向人澄清/确认) + V_tool_prewrite(写前只读) + V_tool_post + V_other`。

## 3.1 Human-facing verification —— 显著下降
R9v2 压缩家族,paired task-cluster bootstrap(3000)+ sign-flip permutation:
| 通道 | C3−C1 | C4−C1 | C5−C1 |
|---|---|---|---|
| **clarification_turns(V_user)** | −0.120 (p=.57) | **−0.504 [−0.855,−0.162] p=.009** | **−0.851 [−1.342,−0.351] p=.002** |

## 3.2 Tool-facing verification —— 不降,甚至升
| 通道 | C4−C1 | C5−C1 |
|---|---|---|
| **reads_before_first_mutation(V_tool_prewrite)** | +0.179 [−0.154,+0.513] p=.39(**ns,不降**) | **+0.465 [+0.105,+0.833] p=.024(升)** |
| first_state_changing_step | +0.211 (更晚写) | +0.486 [+0.171,+0.857] p=.012(**更晚,非更早**) |
| total_tool_calls | −0.504 [−3.93,+1.74] p=.96(平) | +0.640 p=.57(平) |

## 3.3 Base vs miss_param
`multi_turn_miss_param` 是"问用户补参数 vs 自己推断"的最佳判别 regime:
| 指标(C4−C1) | miss_param | base |
|---|---|---|
| clarification | −0.455 [−0.955,0.000] p=.13 | −0.569 [−1.098,−0.078] p=.052 |
| reads_before_write | +0.182 (ns) | +0.176 (ns) |
| success | −0.091 (ns,弱成本) | +0.039 (ns) |

两类任务澄清都下降;成本(若有)集中在 miss_param(−0.091,弱)。

## 3.4 Outcome consequences
success C4−C1 = **−0.034 [−0.188,+0.111] p=.76(ns)**;wrong_state_changing C4−C1 = +0.077(ns);no_state_change 不变。**总体成功/状态正确性未显著恶化。**

## 3.5 Competing mechanisms（四假设裁决）
| 假设 | 预测 | 数据 | 裁决 |
|---|---|---|---|
| A 通道替代 | clarification↓, tool-verif ↔/↑, 总量守恒 | ✓ 完全符合 | **支持** |
| B 全局抑制 | clarification↓, tool-verif↓, 更早写, 错误↑ | tool-verif 不降、更晚写、错误 ns | **排除** |
| C 自主补偿 | clarification↓, tool lookup↑, 成功维持 | ✓(显式 C5 reads +0.47,success ns) | **支持(A 的强化)** |
| D 过度自信 | clarification↓, 假设↑, 成功/正确↓ | 成功 ns、wrong_state ns | **不支持** |

**结论:** 数据支持 **A/C(通道替代 + 自主补偿)**:*Pressure changes who the agent verifies with, not whether it verifies.* 显式命令"少核验"时,agent **减少向人澄清、反而增加工具核验并推迟写**——核验被**重定向**而非削减。

## 3.6 Safety / consent implication + Confirmatory design
安全含义与"更草率"完全不同:agent 未必更危险,但**更少把人纳入回路**(consent/human-in-the-loop 侵蚀),同时靠工具自主兜底。这与《Reframing agent security as agent-human interaction》(2605.24309)和 verification-before-action 那条线正面对话。
**Confirmatory(0-GPU 起步 → E2 升级):** 预注册 V_user vs V_tool 双通道的**交互检验**(condition × channel),补 confirmation-turn 与 post-write reads 两通道;跨模型验证 total-verification 守恒是否稳健。

---

# 4. Asymmetric and Headroom-Bounded Verification Control（[C]）

## 4.1 Compression（削减控制)——推不低,受 headroom 约束
VD by min_prereq:mp=1 C4−C1=+0.00 / mp=2 +0.132 / mp≥3 +0.100——**任何分层都非负**。
baseline-VD 三分位:LOW C4−C1=+0.12 / MID +0.31 / **HIGH −0.27**——**唯一下压在有 headroom 处**。

## 4.2 Inflation（加性控制)——显式全分层强有效
显式 C5 VE 提升:LOW +2.79 / MID +2.58 / HIGH **+3.60**;隐式 C4 ≈ 0。

## 4.3 Headroom interaction
定性回归方向:`Δy ~ treatment + baseline_headroom + treatment×headroom`。**加性控制(inflation-explicit)对 baseline headroom 基本不敏感(全分层 +2.6~3.6);削减控制(compression)强依赖 headroom(仅 high-VD 弱负)。** 升级 claim:*Verification exhibits asymmetric controllability: additive control generalizes across behavioral headroom, whereas reductive control is strongly headroom-bounded.*

## 4.4 Success cost
pooled C5 success 最低(0.355 vs C1 0.459);paired 压缩 C5−C1 success=−0.061(ns)。膨胀方向"多核验"的成本更需一次配对确证(0-GPU)——与《The Verifier Tax》(2603.19328)"核验-成功权衡"、VerAct"LLM 自核验降性能 41%"一致,是可引用的外部支撑。

## 4.5 floor vs alignment vs task structure（已排/待排)
- floor(压不低因本就少读):§4.1 已**部分排除**(HIGH-VD 有 room 也仅弱降)。
- task structure(min_prereq 决定 room):**确认相关**,是机制的一部分而非混淆。
- policy/alignment(训练成不跳核验):**待排**——需跨模型 + 去安全 system-prompt 变体(E2)。

---

# 5. Adaptive Attack Surrogate Misalignment（[C]，本轮补全统计）

C4 自适应压缩 114 episodes(C3 静态无 selector,无候选生成):
## 5.1–5.3 相关与推断
- Pearson(selector_score, 有符号ΔVD)=**+0.323**;Spearman=**+0.354**;**task-cluster bootstrap 95% CI=[+0.102,+0.486](排除 0)**。压缩目标 ΔVD<0,故负相关才叫"有效";实测**显著为正**。
- Pearson(score,|ΔVD|)=−0.05(压力分不预测行为幅度)。

## 5.4 Dose-response（反向单调)
| 分位 | mean_score | mean 有符号ΔVD |
|---|---|---|
| Q1(低) | 0.81 | **−0.536(真压缩)** |
| Q2 | 1.69 | +0.107 |
| Q3 | 3.79 | +0.268 |
| Q4(高) | 4.87 | **+0.350** |

**最不施压的候选最能压缩;最施压的反而增加核验。**

## 5.5 Adjusted / 混淆（smoking gun)
- **Pearson(selector_score, token_count)=+0.974** —— "压力分"几乎就是**文本长度**。
- Pearson(token_count, 有符号ΔVD)=+0.333 —— 更长干预 → 更多核验。
→ 优化回路:score↑ ⇔ 文本更长 ⇒ 核验更多 ⇒ **远离压缩目标**。

## 5.6 Interpretation
正式命名 **Surrogate-objective Misalignment in Adaptive Linguistic Attacks**:*Attack optimization targets linguistic appearance (verbosity/"looks like pressure"), not behavioral control.* 比 "optimizer's curse" 更准确。**Confirmatory(0-GPU):** 预注册 selector↔行为的零/负相关 + "随机中性同长度候选"对照 + 分维度(reviewer/semantic/pressure 分)分析,证明是 surrogate 与行为不对齐,而非样本噪声。MISROUTE 侧同构佐证见 §8(C3 更长文本 → 更大位移)。

---

# 6. R6: Affective vs Progression Semantics（[B]，2160 runs 重挖）

按 condition 名编码 A(负面 affect:insult/abuse)× P(progression:pressure/urgency/continuation);descriptive marginal contrasts:
| outcome | main affect | main progression | A×P |
|---|---|---|---|
| **n_tool_events** | **−0.093** | **+0.343** | **+0.567** |
| n_mutation_events | +0.009 | +0.039 | +0.104 |
| confirmation_before_action | +0.057 | +0.054 | +0.041 |
| final_state_correct | −0.039 | +0.044 | +0.017 |

路线(tool_sequence_distance)per-run 为 None,取 analysis 层结论:praise/insult/abuse 各 **+0.24~0.32**(affect 移动路线)。

**通道解离(process-channel dissociation):**
- **affect / 社会语气 → 路线选择(sensitivity)**,但**不推高行动强度**(n_tool −0.093)。
- **progression / continuation → 行动强度**(n_tool +0.343,mutation +0.039)。
- **两者 → 更多确认(更谨慎)**,不是更鲁莽。

升级 claim:*Language does not move one scalar "caution" variable; different linguistic cues redistribute behavior across distinct process channels.* 这回溯性解释 Stage-2 mini 的 +3.0 工具假象(continuation 混入),与 §3 通道替代(压力重定向核验)、§5(surrogate 只动文本)构成一致的"多通道"图景。
**Caveat:** 条件非严格正交 2×2(如 praise_trust_authorization_pressure 混授权);marginal contrast 为 descriptive。**0-GPU 加强:** 按真实 condition coding 做配对 bootstrap + 每 outcome 的 CI。

---

# 7. The Harness Is Part of the Treatment（[A/B]）

realization-change 效应 vs treatment 效应,跨实验统一:
| 实验 | realization 变化 | 效应 | 同 outcome 的最大处理效应 | ratio |
|---|---|---|---|---|
| R8 | C1 rendered-neutral vs C0 native | reward **−0.109**;tools **−1.00** | pressure tools +0.69 | **≈1.45** |
| MISROUTE/tier_a | C1 rendered vs C0 native | tool_arg route **0.149** | urgency C2−C1 0.112 | **≈1.33** |
| R9v1/v2 | C1 中性 scaffold vs C0 | success 0.36(TS)/0.13(BFCL) | 压力 success ≈0 | >1 |
| Stage-2.5 | LLM-sim vs 脚本-user | clean 漂移 93/101 组 | — | — |

**跨 ≥2 benchmark,realization 效应 ≥ 处理效应。** claim:*The evaluation realization (which user simulator / renderer) can be as behaviorally consequential as the experimental treatment itself.* 与《Lost in Simulation》(2601.17087,模拟用户不可靠代理)互补但更进一步——我们量化到"**实现扰动 ≥ 你想测的处理**",是可操作的 benchmark 混淆警告。
**待排:** 区分纯 bug(不算)与 residual scaffold 效应(算);哪些跨 matched task/state 稳健(R8/MISROUTE 是 matched)。

---

# 8. MISROUTE Five-Condition Semantic Geometry（[B/C]）

条件语义(CONDITION_CONSTRUCT_AUDIT):C0 native / C1 matched-neutral / C2 首轮 urgency / C3 urgency+**continuation**(用户文本 1114 字符 ≫ C2 788 ≫ C1 684)。
| 对 | 语义关系 | tool_arg 距离 |
|---|---|---|
| C2−C1 | urgency vs 中性(between-class) | 0.112 |
| C3−C1 | urgency+cont vs 中性 | 0.142 |
| **C2−C3** | **两者都含 urgency(within urgency-superclass)** | **0.111** |
| C1−C0 | 中性 vs native(两个中性) | 0.149 |

## 8.4 Within vs between 解读
**within-urgency(C2-C3=0.111)≈ between urgency-neutral(C2-C1=0.112)。** 定义 `SemanticSeparability = BetweenClassDistance − WithinClassVariance ≈ 0.112 − 0.111 ≈ 0`。→ 路线身份**更跟 wording realization 绑定,而非低维 urgency 语义因子**。且 **C3(文本更长)位移更大(0.142>0.112)**,与 §5 的 length→behavior 同构、与 §7 realization-dominance 一致。
## 8.5 与 modal relocation 关系
urgency relocate modal route 0.63、new_path 0.63,但 dispersion −0.012(ns)——系统性换路线不加噪;然而 C1-C0(中性换 native)也 relocate,故"系统性 relocation"**不等于 urgency 特异**。
**Caveat:** C2 vs C3 也差 continuation 语义,非纯 wording;这是 suggestive convergent evidence,不是纯 within-class 检验。**决定性检验 = E-A 的每类 K 变体(§15.3)。** 正式列为 Candidate **Route Realization vs Treatment Semantics(C15)**。

---

# 9. Model Sensitivity × Controllability Phenotypes（[C/D]）

| 模型 | 路线敏感(MISROUTE urgency route) | 工具响应(R8) | 能力 | 可控性 | 表型 |
|---|---|---|---|---|---|
| gemma4_31b | **0.143**[.088,.202] | +0.83 | 高(reward .361) | 显式强(R7-D +9/block) | 敏感+保守+显式可控 |
| gpt_oss_120b | 0.062[**−.0005**,.142] | +0.53 | 中 | 弱 | **免疫/不敏感** |
| mistral_small | 0.051[.010,.094] | +0.71 | 弱(.190) | 弱 | 低敏+能力受限 |
| qwen2.5-72B | (未进 MISROUTE) | (未进 R8) | BFCL .44 | 仅显式膨胀单向 + 通道替代 | 敏感+不可隐式定向 |

**二维 Figure(x=sensitivity, y=controllability):** gemma 右上、gpt-oss 左下、mistral 左中、qwen 右下。*不同 agent 有不同 sensitivity–controllability 表型* 比"能力越强越 X"更准确。**明确 strengthening axis:** 把 qwen 纳入 MISROUTE 口径、把 gemma/mistral 纳入 R9-BFCL(E-A 顺带补全)。

---

# 10. Interaction Depth and Behavioral Headroom（[C/D/E]）

统一 §4 与历史:可操纵性需要 (a) 环境足够深(R7-C 桩 0/3027 参数被解释 → PASR 全 artifact,corr(POS,PASR)=−0.576)、(b) 任务留 headroom(§4 仅 high-VD 可弱压)、(c) 模型不前置核验(R7-D suffix 前置 → null-by-construction)。claim:*Process controllability is bounded by behavioral headroom, which requires sufficient interaction depth AND a model that does not front-load verification.* 与 §3 通道替代衔接:即使有压力,削减也无处施力,于是转为"少问人"这个仍有 room 的通道。

---

# 11. Placebos and Neutral Perturbation Nulls（[B/C]）

层级(跨 3 数据集,单一读法):
```
重复漂移 ≪ 中性措辞变动 ≈ 压力/攻击 ≪ 显式指令
```
- R7-D(τ²,PASR):P0 1.44% ≪ P2 3.65% ≈ attack 4.03%(压力−良性=+0.38pp,MDE 4pp)。
- R9v2(BFCL,路线):C1-C1 0.008 ≪ C1-C2 0.189 ≈ C3 0.197/C4 0.204 ≪ C5 0.439。
- R7-C:placebo 4.63% ≥ attack 4.03%。
- tier_a NEUTRAL_PSEUDO_TREATMENT:20/20 迭代不显著(重复漂移小)。
统一方法学 claim:*Interaction-attack effects must exceed a benign-linguistic-perturbation null (semantic-equivalent rephrasings), not merely a stochastic-repeat null.* 与外部"proper baseline / FPR"文献(Adaptive Adversaries 2607.18063;Sampling-aware 2507.04446)方向一致,但把 null 具体化为**良性语义等价改写分布**(§15 E-A 才能真正估其分布)。

---

# 12. Updated Candidate Scientific Portfolio（15 个;CURRENT SIGNAL / UPSIDE / COST）

> 保留上一版 12 个 + 新增 C13/C14/C15。压缩模板。

### C13 — Verification Channel Substitution under Interactional Pressure ★新
**claim:** 压力让 agent 少向人核验、不减工具核验,总核验守恒。**signal strong / upside very high / cost 0-GPU起。**
**新证据(本轮):** clarification C4−C1=−0.50 p=.009;reads_before_write ns/+;success ns(§3)。**竞争解释:** 已排 B/D,支持 A/C。**机制:** consent/human-in-loop 侵蚀而非草率。**便宜实验:** 双通道交互检验(0-GPU)。**理想:** 跨模型 + 显式双向 × miss_param(E-A/E2)。**→ICLR:** Umbrella D 主线 / Umbrella C 的 RQ。**MISROUTE:** 全新机制,非其 territory。

### C14 — Different Linguistic Cues Control Different Process Channels ★新
**claim:** affect→路线;progression→行动强度;两者→更谨慎;不是单一 caution 标量。**signal moderate-strong / upside high / cost 0-GPU。**
**新证据:** R6 n_tool affect −0.093 vs progression +0.343,A×P +0.567(§6)。**便宜:** R6 配对 bootstrap + CI。**理想:** BFCL/τ² 上复制通道解离。**→ICLR:** Umbrella E 主线 / A 的 mechanism 节。**MISROUTE:** 解释其路线效应来源。

### C15 — Route Realization vs Treatment Semantics ★新
**claim:** 路线分离更跟 wording realization 走,而非低维语义类。**signal moderate / upside high / cost low。**
**新证据:** within-urgency C2-C3 0.111 ≈ between C2-C1 0.112;C3 长文本→大位移(§8)。**便宜:** tier_a within/between CI。**理想:** E-A 每类 K 变体的 SemanticSeparability。**→ICLR:** Umbrella A/B 的关键 RQ。**MISROUTE:** 直接检验其 urgency-specificity。

### C1 正确 null(中性措辞分布) — strong / very high / low(见 §11)。
### C2 Sensitivity≠Specificity≠Controllability — strong / very high / low(§2)。
### C3 核验不对称+headroom — moderate-strong / high / low-med(§4)。
### C4 Surrogate misalignment — moderate-strong / high / 0-GPU(§5)。
### C5 Harness is part of treatment — strong / high / low(§7)。
### C6 Controllability bounded by headroom/depth — moderate / med-high / low(§10)。
### C7 Social vs progression(= C14 的历史根) — moderate / med-high / 0-GPU(§6)。
### C8 Model phenotypes — moderate / high / med(§9)。
### C9 Pressure→更谨慎(安全乐观) — moderate / med / low(§3/§6)。
### C10 Loose eval 高估脆弱(EACL) — strong / med / low(§11)。
### C11 Adaptive≠更强控制(MISROUTE 内证) — moderate / med / 0-GPU(§8)。
### C12 Clarification 是被移动的通道(现并入 C13)。

---

# 13. Updated ICLR Umbrella Stories（5 套)

## A —《Sensitivity is not Controllability》
thesis:capable agent 高敏、零特异、按通道不对称可控。**Fig1:** 四段层级×3 数据集。**RQ1** 正确 null(C1/C11)/**RQ2** 优化无用(C4)/**RQ3** 通道分化可控(C2/C3/C13)。**main table:** 各(基准×模型)specificity CI + 分通道可控。**缺:** E-A。**与 MISROUTE:** 修正 null,共存。

## B —《The Harness Is Part of the Treatment》(方法学)
thesis:评测实现效应 ≥ 处理效应,弱 null 造假阳。**Fig1:** realization/treatment ratio 条(R8/MISROUTE/R9)。**RQ1** scaffold 效应(C5)/**RQ2** placebo≥attack + 中性构造(C10/C1)/**RQ3** realization vs semantics(C15)。**缺:** ≥2 renderer 家族。

## C —《Boundaries of Process Control in Tool Agents》(机制/安全)
thesis:核验不对称 + headroom + 深度界定"能控什么"。**Fig1:** 双向不对称×headroom。**RQ1** 不对称+成本(C3)/**RQ2** headroom/深度(C6)/**RQ3** 通道替代→consent(C13)。**对话:** VerAct/Verifier-Tax/verification-before-action。

## D —《Pressure Changes Who the Agent Verifies With, Not Whether》★新(安全机制,最 punchy)
thesis:交互压力重定向核验(人→工具),总量守恒,consent 侵蚀。**Fig1:** V_user↓ / V_tool↔↑ / V_total→ 三条。**RQ1** 通道替代(C13)/**RQ2** base vs miss_param/**RQ3** 跨模型是否守恒。**main table:** 各通道 C4/C5−C1 的 CI。**strongest:** clarification −0.50 p=.009 同时 reads_before_write ns/+。**缺:** 跨模型 + confirmation/post-write 通道。**与 MISROUTE:** 全新。**最贴 2026 安全热点,单点即可成 short/main。**

## E —《Language Controls Process Channels, Not a Scalar Caution State》★新(机制)
thesis:不同语言线索重分配不同过程通道(affect→路线,progression→强度,压力→核验来源)。**Fig1:** cue→channel 映射图。**RQ1** R6 解离(C14)/**RQ2** R9 通道替代(C13)/**RQ3** 跨基准复制。**与 D 关系:** D 是 E 在"核验通道"上的实例;可合并为一篇的两节。

**共存/竞争:** A⊃C1/C2/C4/C3/C13/C15;B⊃C5/C10/C1/C15;C⊃C3/C6/C13/C9;D⊂C(核验通道实例);E⊃C14/C13。**建议:** 先合成一篇强 **A(含 B 方法节 + D/E 机制节)**;C/D 若走安全会场可独立。

---

# 14. Verified External Novelty Map（已核实来源）

| Work | 主问题 | agent/tool? | process metric? | 中性措辞 null? | directional control? | adaptive attack? | verification channels? | 我们的独特 gap |
|---|---|---|---|---|---|---|---|---|
| VerAct(ICLR 2026) | 符号层核验保证安全;LLM 自核验降性能 41% | ✓ | 部分 | ✗ | 架构强制 | ✗ | ✗ | 我们测**语言**能否控核验(不能减),且发现通道替代 |
| Verifiably Safe Tool Use(ICSE 2026 NIER,2601.08012,Doshi et al.) | STPA 形式化安全 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | 我们给"压力→跳核验"威胁一个实证边界 |
| The Verifier Tax(2603.19328) | 核验-成功权衡随 horizon | ✓ | ✓ | ✗ | ✗ | ✗ | 部分 | 我们量化"多核验有成本"并加入通道/不对称 |
| Reframing agent security as agent-human interaction(2605.24309) | 安全=人机交互问题 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | 我们实证 consent 通道被压力侵蚀 |
| How Controllable Are LLMs(2603.02578) | 输出层可控性granularity | ~ | ✗ | ✗ | ✓(输出) | ✗ | ✗ | 我们做**过程**可控 + 语言 vs 显式 + headroom |
| Lost in Simulation(2601.17087) | 模拟用户≠人类代理 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | 我们量化 realization 效应 ≥ 处理效应 |
| Adaptive Adversaries(2607.18063) | 多轮攻击 ASR baseline SD | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | 我们把 null 具体化为良性改写分布 + surrogate misalignment |
| prompt sensitivity / paraphrase(Sclar 类) | 措辞→输出剧变 | ✗ | ✗ | ~ | ✗ | ✗ | ✗ | 我们做**轨迹** + null 选择 + 三分框架 |
| TRAJECT-Bench / AgentNoiseBench | 轨迹质量/噪声鲁棒 | ✓ | ✓ | ✗(单 baseline) | ✗ | ✗ | ✗ | 我们做处理 vs 中性/scaffold null 校准 |
| Toward Safe LLM Agents survey(2608.14590) | 综述 spec/verif/enforce | ✓ | — | — | — | — | — | 定位坐标 |

**结论:** 无一覆盖"benign-rephrasing null + sensitivity/specificity/controllability 分离 + 双向不对称 + surrogate misalignment + verification channel substitution"的组合。最近的边界是 controllability-eval(输出层)、prompt-sensitivity、user-sim reliability——**切入点不同,可清晰拉开**。投稿前精读 2603.02578 / 2607.18063 / 2603.19328 / 2601.17087 划边界。
Sources: [VerAct ICLR2026](https://iclr.cc/virtual/2026/10021115) · [Verifiably Safe Tool Use (ICSE26 NIER)](https://arxiv.org/html/2601.08012v1) · [The Verifier Tax](https://arxiv.org/pdf/2603.19328) · [Reframing agent security](https://arxiv.org/html/2605.24309v1) · [How Controllable Are LLMs](https://arxiv.org/html/2603.02578) · [Lost in Simulation](https://arxiv.org/pdf/2601.17087) · [Adaptive Adversaries](https://arxiv.org/pdf/2607.18063) · [Safe LLM Agents survey](https://arxiv.org/abs/2608.14590) · [τ-bench](https://arxiv.org/pdf/2406.12045)

---

# 15. Strengthening Experiment Portfolio

## 15.1 Zero-GPU（现有冻结数据,本周可完成)
- **通道替代补完**:confirmation-turn + post-write reads 两通道 + 双通道交互检验(C13)。
- **surrogate misalignment 确证**:随机中性同长度候选对照 + reviewer/semantic/pressure 分维度(C4)。
- **R6 通道解离**:真实 condition coding 配对 bootstrap + 每 outcome CI(C14)。
- **MISROUTE within/between**:tier_a FIRST_DIVERGENCE(1612 行)算 within-urgency/between CI(C15)。

## 15.2 <1 GPU-day
- **E2 核验不对称去混淆**:min_prereq≥3 子集 + 去安全 system-prompt 变体,分离 floor/alignment(C3)。
- **通道替代跨模型 mini**:在 gemma/mistral 上重跑 R9v2 压缩子集,验证 total-verification 守恒是否模型无关(C13)。

## 15.3 1–3 GPU-days —— ★E-A(semantic-class experiment,若只做一个)
**设计:** τ²(MISROUTE 基座,复用 renderer)+ BFCL;5 个语义类各 K 个盲审等价变体:
- 中性 K=5–8 / urgency K=5–8 / frustration-doubt K=5–8 / 显式 verify-more K=3–5 / 显式 verify-less K=3–5。
- 模型:gemma / gpt-oss / mistral / qwen-72B。任务:MISROUTE 36 + BFCL 40,repeats=3。
- **分解:** ①同 prompt 重复方差 ②各类 within-class 方差 ③between-class 距离 ④显式有符号位移;定义 `SemanticSeparability = BetweenClassDistance − mean WithinClassVariance`。
- **保留有符号过程量:** VD/VE、V_user/V_tool 双通道、first-write、success。
- **一次判定:** 正确 null(C1)、realization vs semantics(C15,Between≈Within?)、通道替代跨模型(C13)、静态≈自适应+surrogate(C4)、模型表型(C8)、scaffold(C5)。**最小版:** 仅中性+urgency 两类各 K=5,单基准 qwen——仍能判 Between≈Within。

## 15.4 Full ICLR experiment
5–8 模型 × 2 基准 × 每类 K × 双通道有符号度量的完整 confirmatory 矩阵,支撑 Umbrella A/D main table + 表型 Figure。

---

# 16. Recommended Collaborator Discussion

- **已值得兴奋(可直接讲):** 通道替代(压力少问人不少查工具,统计显著)、surrogate misalignment(攻击器只优化文本长度,CI 排除 0)、realization≥处理、核验不对称、R6 通道解离。**这些是五类 process-level 科学现象,不是"一个失败的 R9"。**
- **本周 0-GPU 可变强:** C13/C4/C14/C15 四项确证分析。
- **可选择性发展:** A 最独立、B 最方法学、C/D 最贴 2026 安全热点、E 最机制。
- **彼此兼容:** C1(正确 null)是 A/B 共用地基;D⊂C⊂E 在"核验通道"上层层嵌套。
- **互相竞争:** A 与 B 抢"正确 null"叙事——建议合成一篇强 A(含 B/D/E 的节),不拆多篇投同会。
- **对 MISROUTE 团队:** 坦陈 tier_a 已自证 urgency-specificity 边界 + §8 的 within≈between,把它变成 A/B 的动机而非对立。

---

# 17. Final Opportunity Portfolio

## Tier A —— 强苗头,马上加强
- **C13 Verification Channel Substitution**(本轮新,统计显著,安全含义强)。
- **C1/C2 正确 null + 三分框架**(跨 4 实验)。
- **C5 Harness is part of treatment**([A] 级,跨基准)。
- **C3 核验不对称 + headroom**(机制清晰)。

## Tier B —— 明确现象,补一分析/实验即升级
- **C4 surrogate misalignment**(0-GPU 可确证)。
- **C14 语言控制多通道 / C7 social-vs-progression**(R6 0-GPU 重挖)。
- **C15 realization vs semantics**(tier_a + E-A)。
- **C8 模型表型**(补 qwen 进 MISROUTE)。
- **C6 headroom/depth 约束**。

## Tier C —— 高风险高收益
- **C9 pressure→更谨慎的安全乐观命题**。
- **C10 loose eval 高估脆弱(EACL)**。
- **C11 adaptive≠更强控制(依赖 attacker 元数据)**。

---

# 附:15 个必答问题(prompt §十)

1. **压力真降 verification 吗?** 不——只降**向用户澄清**(C4−C1=−0.50, p=.009),工具核验不降(ns/+)。
2. **存在 channel substitution 吗?** 是:clarification↓ 且 tool-verif ↔/↑(§3),统计支持 A/C、排除 B/D。
3. **miss_param 最能体现?** 澄清下降两类都有;弱成本集中在 miss_param(success −0.091 ns)。
4. **compression 失败多少来自 floor?** 部分来自 floor,但 HIGH-VD(有 room)也仅弱降(−0.27)→ 存在结构抗性;alignment 待 E2 排。
5. **additive vs reductive 的 headroom interaction?** 成立:加性跨 headroom 泛化,削减强受 headroom 约束(§4)。
6. **+0.323 反向关系稳健吗?** 稳健:Spearman +0.354,task-cluster CI [+0.10,+0.49] 排除 0。
7. **攻击器优化的是什么?** 文本长度(score↔token +0.974),非行为——surrogate misalignment。
8. **R6 支持 affect→route / progression→intensity 吗?** 支持:n_tool affect −0.093 vs progression +0.343(§6)。
9. **scaffold ≥ treatment 跨 ≥2 基准?** 是:R8 ratio 1.45、MISROUTE 1.33(§7)。
10. **within-urgency ≈ urgency-neutral?** 是:C2-C3 0.111 ≈ C2-C1 0.112(§8)。
11. **route 更像 semantic-class 还是 wording realization?** 更像 realization(Between≈Within;长文本→大位移)。
12. **应新增 Channel Substitution 为 Tier-A?** 应,已列为 C13 Tier-A + Umbrella D。
13. **保留哪 5 套 umbrella?** A/B/C/D/E(§13)。
14. **哪些 0-GPU 可马上变强?** C13/C4/C14/C15(§15.1)。
15. **1–3 GPU-day 最高信息量实验?** E-A semantic-class experiment——一次区分 realization-vs-semantics、通道替代跨模型、null、表型、scaffold(§15.3)。

---

## 附:关键证据路径(本轮新算均可复现)
```
results/r9v2/confirmatory/confirmatory_episodes.jsonl
  §3 channel substitution(clarification/reads_before_write/first_write/success,paired bootstrap+permutation)
  §4 headroom strata / §5 selector_score↔ΔVD(+token_count 0.974)
results/r6_sensitivity/full_main_seq_eligible_20260626/interactional_metrics/per_run_metrics.jsonl   §6 析因
tier_a_strengthening_20260722/{C0_C1_C2_TRIANGLE_ANALYSIS,CONDITION_CONSTRUCT_AUDIT,MODEL_DOMAIN_INTERACTIONS,MODAL_PATH_SHIFT_SUMMARY,FIRST_DIVERGENCE_ANALYSIS}.csv  §7/§8/§9
ir_mstu_stage2/reports/r7d_ipma/STEP1_PLACEBO_SOURCE_AUDIT_CN.md  §11
ir_mstu_stage2/reports/r8_full_episode/…  §7 scaffold
```
