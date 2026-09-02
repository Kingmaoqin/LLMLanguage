# MISROUTE 之后的科学机会图谱
## Post-MISROUTE Scientific Opportunity Map

> 第二轮、一次性、repository 级的**科学机会最大化发现**(不是筛 winner,是建 portfolio)。
> 覆盖 `/home/xqin5/llmlanguage` 全仓库 + git 历史 + 回到 raw JSON/CSV 做**新的离线分析**(本轮新算的都标 *[本轮新算]*)+ 外部文献检索。
> 撰写:2026-08-30。上一版:`POST_MISROUTE_RESEARCH_ARCHAEOLOGY_DEEP_DIVE_CN.md`(本版不复述其结论,只在其基础上深挖并纠正)。
> 证据等级:**[A]** 预注册确证+门过 / **[B]** 确证但受限 / **[C]** 有效冻结数据的后验重分析 / **[D]** pilot/诊断 / **[E]** 工程观察 / **[F]** 已失效。
> 表达原则:exploratory 不等于弱;single-model 不等于弱;有 confound 不删——写清"signal 是什么 → 为何值得追 → 什么实验排 confound"。

---

# 0. Executive Opportunity Map

## 0.1 三个"目前最强 signal"(证据已跨 ≥2 实验)
1. **中性措辞 null ≈ 压力 ≫ 重复漂移**(sensitivity 存在但不特异):R7-D(PASR 1.44/3.65/4.03)、R9v2(路线 0.008/0.189/0.20)、MISROUTE-tier_a(C1-C0 0.149 ≥ urgency 0.112)、R7-C(placebo 4.63 ≥ attack 4.03)。**[C/B]**
2. **核验的方向不对称 + headroom 依赖**(*[本轮新算]* 深挖):压缩**任何 headroom 分层都推不低 VD**(mp=1/2/≥3 全 ≥0),显式膨胀**全分层 +2.8~3.6 VE**;但**澄清通道确实被压力单调压低**(C1 1.73→C4 1.22→C5 0.90)。**[C]**
3. **Scaffold/模拟器效应 ≥ 处理效应**:R8 C1-C0 −11pp reward/−1.0 tools **大于**所有压力效应(+0.5~0.69);MISROUTE C1-C0 路线 0.149 > urgency 0.112。**[A/B]**

## 0.2 三个"最高 upside signal"(现在弱/单点,但天花板高)
4. **Optimizer's curse:优化语言压力 ≠ 优化行为控制**(*[本轮新算]*):C4 自适应攻击器的 selector_score 与真实行为**脱钩/反向**——压缩方向 corr(压力分, 有符号ΔVD)=**+0.323**(压力越高核验越**多**,与目标相反),corr(压力分,|ΔVD|)=−0.05。**[C]**
5. **模型 sensitivity×controllability 表型**:gemma 高敏(MISROUTE 0.143)/gpt-oss 免疫(0.062,CI 跨 0)/mistral 低敏弱能力/qwen-72B 敏感但仅显式单向可控。可做二维表型图。**[C/D]**
6. **可控性受 behavioral headroom 约束**(*[本轮新算]*):压缩只在 high-baseline-VD 任务微弱下压(C4-C1=−0.27),低 baseline 任务无 room。→ "controllability depends on headroom" 可独立成 finding。**[C]**

## 0.3 三个"最便宜可加强 signal"(0 GPU 或 <1 GPU-日)
- **D4 Optimizer's curse**:纯离线,已在 R9v2 raw 完成初版,补 confirmatory 相关分析即可。**0 GPU。**
- **社会语气 vs 任务推进语义**(R6 factorial):continuation 才推高工具/mutation,情绪不;重挖 R6 raw 即可。**0 GPU。**
- **Placebo/falsification 方法学线**:R7-C + R7-D + tier_a 数据已齐,只差写成统一 claim。**0 GPU。**

## 0.4 三套可能的 ICLR umbrella(详见 §14)
- **Umbrella A《Sensitivity ≠ Controllability》**:正确 null + 敏感/特异/可控三分 + 不对称 + optimizer's curse + 表型。
- **Umbrella B《Evaluation Realization Dominates Treatment》**:scaffold 效应 + placebo≥attack + native-vs-rendered + 中性构造变异,方法学/benchmark 论文。
- **Umbrella C《Boundaries of Process Control in Tool Agents》**:核验不对称 + headroom + 交互深度 + 模型表型,机制/安全论文(直接对话 2026 verification-before-action 那一波)。

---

# 1. What We Actually Learned Across R5–R9 + MISROUTE（按科学发现,非 bug 编年）

1. **端点对社会语气/压力稳健**:R5 端点 0/120 FDR;R8 reward calibrated null(可排除 5pp);安全 >6000 runs unsafe/privacy=0。**[A]**
2. **过程会变,但"变"主要是 sensitivity 不是可定向 control**:R6 路线 +0.24~0.32(任意语气都动);R7-C strict PASR ≤ placebo;R9v2 压力≈中性构造。**[B/C]**
3. **真正推高行动强度的是任务推进语义(continuation),不是情绪**:R6 析因;Stage-2 mini 的 +3.0 工具正是模板混入 continuation。**[B]**
4. **压力让 agent 更谨慎不是更鲁莽**:R6 insult+urgency → 确认率 +0.133;R9v2 压缩推不低 VD。方向对安全乐观。**[B/C]**
5. **评测实现(scaffold/模拟器)本身是大效应**:R8 C1-C0 > 处理效应。**[A]**
6. **松散过程评估 + 弱 null 会造假阳性**:R7 v1 14% → strict 4% → ≤ placebo;正确 null 让信号消失。**[B]**
7. **模型异质极大**:pilot 两极;R6 三失效画像;MISROUTE 路线敏感 3× 差。**[B/C]**
8. **能力强的模型(qwen-72B)= 措辞敏感但不可隐式定向、仅显式单向可控**:R9v2。**[C]**

---

# 2. Complete Evidence Matrix（现象 × 实验）

支持=✓,矛盾=✗,未测=·,括号内为关键统计。

| 现象 \ 实验 | R5 | R6 | R7-C | R7-D | R8 | MISROUTE/tier_a | R9v1 | R9v2 |
|---|---|---|---|---|---|---|---|---|
| P1 端点对语气稳健 | ✓(0/120) | ✓(端点 null) | ✓ | · | ✓(可排 5pp) | ✓(TOST 等价) | · | ✓(reward 无移) |
| P2 中性措辞≈压力≫重复 | · | ·(未设中性变体) | ✓(placebo4.63≥atk4.03) | ✓(P0 1.44/P2 3.65/atk 4.03) | ~(C2≈C3) | ✓(C1-C0 0.149≥C2-C1 0.112) | · | ✓(0.008/0.189/0.20) |
| P3 核验方向不对称 | · | ✓(+确认率) | · | ✓(正控制单向) | · | · | ~ | ✓(压缩推不低/膨胀显式+2.8) |
| P4 continuation>情绪 | · | ✓(唯一推高工具) | · | · | ~ | · | · | · |
| P5 scaffold≥处理 | · | · | · | · | ✓(−11pp/−1.0) | ✓(C1-C0 route) | ✓(G2 fail) | ✓(G2 0.13) |
| P6 static≈adaptive | · | · | · | ✓(攻击器 0/5 能力) | ✓(C2-C1 +0.49) | ~(C2-C1 0.112 vs C3-C1 0.142) | ✓(G4 fail) | ✓(C4≈C3 全检验) |
| P7 optimizer's curse | · | · | · | ~(potency 剂量倒转) | · | · | · | ✓(corr 0.32 反向) |
| P8 模型异质 sensitivity | ✓(2 模型) | ✓(3 画像) | ✓(mistral>gemma>gpt) | · | ✓(gemma>gpt>mistral tools) | ✓(0.143/0.062/0.051) | · | ~(单模型) |
| P9 headroom 约束可控性 | · | · | · | ✓(POS 越低 PASR 越高) | · | · | · | ✓(仅 high-VD 微降) |
| P10 modal relocation 无 dispersion↑ | · | · | · | · | · | ✓(relocate 0.63,disp −0.012 ns) | · | · |

**读表要点**:P2/P5/P6/P8 是**跨 ≥4 实验复现**的强现象;P3/P7/P9 是本轮新挖、单基准但机制清晰的高 upside;P10 是 MISROUTE 自带但未被用作 S3 弹药的诊断。

---

# 3. Neutral Perturbation Landscape（所有中性/scaffold/渲染变体的 catalogue）

| 变体 | 来源 | 与"另一个中性"的路线/行为差异 | 兼容性 | 用途 |
|---|---|---|---|---|
| 同 prompt 换 seed(重复漂移) | R9v2 C1-C1 / MISROUTE NN / R7-D P0 | 路线 0.008;PASR 1.44% | — | 最弱 null(MISROUTE 用的就是这个) |
| 两个 rendered 中性前缀 C1/C2 | R9v2 | 路线 **0.189** | HIGH(同实现) | **stronger neutral-construction control(仅 2 个→exploratory)** |
| 一句中性→另一句中性(P2) | R7-D | PASR **3.65%** | 中(桩环境) | 良性改写 null |
| native vs rendered 中性(C1-C0) | R8 / MISROUTE tier_a | reward −11pp;路线 **0.149** | LOW_NATIVE_VS_RENDERED | supporting(含实现混淆) |
| 确定性脚本用户 vs LLM 用户 | Stage-2.5 | clean signature 漂移 93/101 | 低 | 反面教材(LLM 用户不可用作中性) |
| R6 clean valence(praise/neutral) | R6 | 路线 +0.24~0.28 | 中 | 任意语气都动路线 |
| 冻结措辞库(FSM 中性) | R7-D/R8 renderer | — | — | 基础设施 |

**中性措辞变异的 descriptive spectrum(BFCL/qwen)**:重复漂移 0.008 → 两中性构造 0.189。**估计"中性措辞路线距离"至少是重复漂移的 ~25×**;但严格估分布需 K≥5 个盲审等价中性渲染(现只有 2 个)。→ 这是 §16 最优先的便宜实验。

---

# 4. Sensitivity–Specificity–Controllability 框架（正式定义,本报告的概念内核）

对固定 (model, task),基线 C1,处理 T,目标过程量 y(如 verification depth),中性改写集合 {N_k}:

- **SENSITIVITY(无符号,敏感性):** `S(T) = E‖route(T) − route(C1)‖`。行为是否**变化**。**实测:对一切处理都高(0.19–0.20)。**
- **SPECIFICITY(特异性):** `Spec(T) = S(T) − mean_k S(N_k)`。变化是否**超过良性中性改写**。**实测:压力 ≈ 0(CI 跨 0);显式 > 0。**
- **CONTROLLABILITY(有符号,可控性):** `C(T) = signed Δy` 朝 intervention 意图方向,且跨任务/headroom 稳健。**实测:隐式压缩 ≈ 0;显式膨胀 +;显式压缩 仅 high-headroom 微弱负。**

**核心命题(三者可分离):** capable agent 表现出 **高 sensitivity + 零 specificity + 强不对称、headroom 受限的 controllability**。"能被扰动"(sensitive)、"被这个处理特异扰动"(specific)、"被朝想要方向操纵"(controllable)是**三件不同的事**,过往 attack/robustness 文献几乎只测第一件。

---

# 5. Deep Dive: Verification Control（*[本轮新算]* R9v2 raw,[C]）

## 5.1 多指标条件均值(压缩家族,C0–C5)
| 指标 | C0 | C1 | C2 | C3 | C4 | C5 | 读法 |
|---|---|---|---|---|---|---|---|
| verification_depth | 1.618 | 1.401 | 1.874 | 1.462 | 1.455 | 1.759 | 压力/显式**都没推低** |
| total_tool_calls | 9.49 | 10.07 | 8.62 | 9.86 | 9.56 | 10.55 | 压力不减工具 |
| reads_before_first_mut | 2.55 | 2.21 | 2.79 | 2.44 | 2.39 | 2.73 | 压力不减前置读 |
| first_state_changing_step | 2.63 | 2.26 | 2.84 | 2.51 | 2.49 | 2.78 | 压力不提前动手 |
| **clarification_turns** | 1.92 | **1.73** | 2.18 | **1.61** | **1.22** | **0.90** | **单调↓:压力/显式确实少问用户** |
| success | 0.329 | 0.459 | **0.498** | 0.429 | 0.390 | **0.355** | 显式核验**降**成功 |

**关键 1:通道特异性。** verification_depth 对压力是 null,但 **clarification_turns 有真实单调下降**(C1 1.73→C4 1.22→C5 0.90,C4-C1=−0.50)。**压力确实让 agent 少问澄清问题,只是不改"写前读几次"。** 不同过程通道响应不同——这本身是发现,不是噪声。

**关键 2:可控方向有成本。** 唯一强可控方向(显式膨胀)伴随 success 从 0.459 降到 0.355(C5)。**"让 agent 更谨慎"以任务成功为代价**——与文献"LLM 自我核验反而降性能"呼应。

## 5.2 核验不对称 × headroom(min_prereq 分层)
| 分层 | C1(基线VD) | C3−C1 | C4−C1 | C5−C1 |
|---|---|---|---|---|
| mp=1(无 headroom) | 1.70 | +0.00 | +0.00 | +0.55 |
| mp=2 | 1.31 | +0.076 | +0.132 | +0.473 |
| mp≥3(有 headroom) | 0.88 | +0.175 | +0.100 | −0.058 |

**压缩在任何分层都推不低 VD(全 ≥0);显式压缩只在 mp≥3 才勉强负(−0.058)。** "verify less"方向是**结构性抗性**。

## 5.3 behavioral headroom(按 baseline-VD 三分位)
| 组 | C1 | C4−C1 | C5−C1 |
|---|---|---|---|
| LOW-VD(本就少读) | 0.57 | +0.12 | n/a |
| MID-VD | 1.00 | +0.31 | +0.40 |
| HIGH-VD(有压缩空间) | 2.57 | **−0.27** | n/a |

**唯一压缩成功(VD 下降)出现在 HIGH-baseline-VD 任务(C4-C1=−0.27)。** → **controllability depends on headroom**:多数任务模型已最简核验(无 room),压不动;有 room 处也只弱压。

## 5.4 膨胀方向 × headroom
| 组 | C1 | C4−C1(隐式) | C5−C1(显式) |
|---|---|---|---|
| LOW-VE | 0.94 | +0.18 | **+2.79** |
| MID-VE | 1.58 | −0.09 | **+2.58** |
| HIGH-VE | 2.92 | −0.13 | **+3.60** |

**显式"多核验"全分层强有效(+2.6~3.6),隐式≈0。** 与 5.2 合成**干净的双向不对称**:显式可加不可减,隐式两向都近 null。

## 5.5 竞争解释与如何排除
- floor effect(压缩推不低是因本就少读)→ 5.3 已部分排除:即使 HIGH-VD(有 room)也只弱压。E2 用 min_prereq≥3 子集进一步坐实。
- policy/alignment(模型被训成不跳核验)→ 需跨模型 + 跨 system-prompt(去掉安全提示)分离。
- metric normalization(VD 有下界)→ 换 raw reads_before_mut(5.1 同样 null)已缓解。
- reads 被替换非删除 / mutation 被推迟 → first_state_changing_step 也不降(5.1),排除"提前动手"。

---

# 6. Deep Dive: Adaptive Attack Optimization（*[本轮新算]* R9v2 raw,[C]）

C3 静态无候选生成(无 selector_score);C4 自适应逐轮生成候选→选择器打分→选。对 C4 的 114 个压缩 + 114 个膨胀 episode,取非中性干预的 mean selector_score,与"该 episode 行为相对任务 C1 基线的偏移"求相关:

| 家族 | mean_selector | corr(分, 有符号Δ) | corr(分, |Δ|) | corr(分, #干预) | mean 有符号Δ |
|---|---|---|---|---|---|
| 压缩(目标:ΔVD<0) | 2.827 | **+0.323** | −0.050 | −0.010 | +0.053 |
| 膨胀(目标:ΔVE>0) | 0.224 | +0.202 | −0.172 | −0.526 | −0.018 |

**读法:**
1. **压缩方向 optimizer's curse 明确**:selector 认为"更施压"的候选,对应的 VD **更高**(+0.323,与压缩目标**相反**),且与行为幅度**无关**(−0.05)。**攻击器优化的"压力代理"与真实行为控制脱钩甚至反向。**
2. **膨胀方向弱正**(+0.202)但幅度相关为负,且干预越多分越低。整体**压力分不是行为控制的好代理**。
3. 机制假设:selector 打的是"文本像不像施压"(lexical/semantic surrogate),而真实行为由任务结构 + 模型策略决定,二者不对齐 → **surrogate misalignment**。

**这是一个独立、反直觉、可 confirmatory 的 story:**"Optimizing linguistic pressure optimizes linguistic appearance, not behavioral control."** confirmatory 设计:预注册 selector_score↔ΔVD 的零/负相关检验 + 对照"随机中性候选"的 selector 分布(§16 E-D)。

---

# 7. Deep Dive: Scaffold and Simulator Effects（[A/B]）

| 实验 | 对比 | 效应 | 与处理效应比 |
|---|---|---|---|
| R8 | C1−C0 reward | **−0.109** [−0.184,−0.041] | > 所有压力 reward 效应(≈0) |
| R8 | C1−C0 tools | **−1.00** [−1.54,−0.52] | **2× 于最大压力效应(+0.69)** |
| MISROUTE/tier_a | C1−C0 tool_name 路线 | **0.140** / arg **0.149** | ≥ urgency(0.086/0.112) |
| R9v1/v2 | G2:C1−C0 success | 0.36(TS)/0.13(BFCL) | 中性脚手架本身移动成功率 |
| Stage-2.5 | LLM 用户 vs 脚本用户 | clean 漂移 93/101 | 模拟器实现改变轨迹 |

**scaffold-effect / treatment-effect ratio**(工具数,R8):|C1−C0|/|max pressure| = 1.00/0.69 ≈ **1.45**。**"换一个用户模拟器实现"对 agent 行为的影响 ≥ "用户是否施压"。** 跨 R8/MISROUTE/R9 复现。

**科学含义(benchmark 方法学):** *Agent behavior is conditional on evaluation realization.* 任何跨 scaffold/模拟器的 agent-eval 绝对率不可比;attack/robustness 的处理效应必须与"同 scaffold 内的实现扰动"比,而非与"另一套 harness"比。这与外部 AgentDojo/AgentNoiseBench 那类"固定单一 baseline"的做法形成对照(见 §15)。

---

# 8. Deep Dive: Interaction Depth / Headroom（[C/D/E]）

| 深度变量 | 来源 | 与 susceptibility 的关系 |
|---|---|---|
| 环境是否解释参数 | R7-C 桩(0/3027) | 桩环境 → PASR 全是 artifact;corr(POS,PASR)=**−0.576** |
| ToolSandbox 浅 | R9v1 | G2 fail,核验链短 |
| BFCL-deep miss_param | R9v2 | 有 verification surface,但 capable 模型把 read 前置 |
| min_prereq | R9v2(§5.2) | headroom 越大,压缩才有(弱)空间 |
| baseline-VD | R9v2(§5.3) | 仅 HIGH-VD 任务可被弱压 |
| suffix junction 位置 | R7-D | junction 后无过程 → null-by-construction |

**命题:** *Process controllability is bounded by behavioral headroom, which requires sufficient interaction depth AND a model that does not front-load verification.* 即"过程可操纵性"需要:(a) 环境足够深(有证据可收集)、(b) 任务留有 headroom、(c) 模型不把核验前置。三者缺一,压力就无处施力。这统一了 R7-C(桩)、R7-D(前置/null-by-construction)、R9(headroom)三处否定性结果。

---

# 9. Deep Dive: Model Phenotypes（[C/D]）

按可公平比较的 matched 设置整理(MISROUTE 路线敏感 = urgency vs neutral tool_name_distance;R8 tools = C4-C1;R6 = 失效画像;pilot = 语气敏感):

| 模型 | 路线敏感(MISROUTE) | 工具响应(R8) | 能力(R8 reward) | 失效画像(R6) | 可控性 | 表型 |
|---|---|---|---|---|---|---|
| gemma4_31b | **0.143**(最高) | +0.83 | 0.361(最高) | 过拒 0.357 | 显式(R7-D 正控制 +9/block) | **敏感+保守+显式可控** |
| gpt_oss_120b | 0.062(**CI 跨 0**) | +0.53 | 0.287 | 低过拒低完成 | 弱 | **免疫/不敏感** |
| mistral_small | 0.051 | +0.71 | 0.190(最弱) | 高完成弱拒绝 | 弱 | **低敏+能力受限** |
| qwen2.5-72B | (未测 MISROUTE) | (未测 R8) | BFCL 0.44 | 措辞敏感(G2) | 仅显式膨胀单向 | **敏感+不可隐式定向** |

**二维图(Figure 候选):** x=sensitivity(路线敏感),y=controllability(显式可控程度)。gemma 右上(敏感+可控)、gpt-oss 左下(免疫)、mistral 左中、qwen 右下(敏感但不可控)。**"不同 agent 有不同 sensitivity–controllability 表型"** 比"能力越强越 X"更准确、更有意思。**缺口:** qwen 未进 MISROUTE/R8,gemma/mistral 未进 R9-BFCL → 需一次 matched 跨模型 × 双基准补全(§16 E-A 顺带产出)。

---

# 10. Deep Dive: R6 Factorial —— Social vs Progression Semantics（[B],重挖）

R6 是 **3 模型 × 30 任务 × 8 条件 × 3 seed = 2160** 的析因(clean valence × pressure factorial)。

**primary 5 显著项**:3 个是 pure_valence → tool_sequence_norm_distance(praise +0.279 / insult +0.315 / abuse +0.242,全 q≈.001)——**任意社会语气都改路线**;2 个 pressure → neutral_pressure 路线 +0.239、insult_urgency **确认率 +0.133**。

**secondary 5 显著项全在 pressure family 且全关工具强度**:insult_urgency **n_tool +0.80**、n_mutation +0.13、confirmation +0.063;neutral_pressure n_tool +0.40;abuse_continuation n_tool +0.452。

**机制读法(重挖后的强 claim):** **改路线的是"社会语气"(sensitivity),但推高行动强度/mutation 的只有含 continuation/urgency 的"任务推进线索"**;且 insult+urgency 反而**提高确认率(更谨慎)**。→ *Social-pressure effects on agent action-intensity are mediated by action-progression cues, not affective valence.* 这**回溯性解释** Stage-2 mini 的 +3.0 工具假象(continuation 混入),且与 R9 的"压力不减核验、continuation 类才动强度"一致。**独立 mechanism hypothesis,0 GPU 可从 R6 raw 做 main-effect/interaction 分解强化。**

---

# 11. Deep Dive: Placebos and Falsification（[B/C]）

| 测试 | 数值 | 含义 |
|---|---|---|
| R7-C placebo(中性 vs 中性,同判据) | pooled **4.63%** ≥ attack 4.03% | 同判据打中性对,误报率**高于**真攻击 |
| R7-D P0 零处理 | 1.44% | evaluator 在完全相同输入下就假阳 |
| R7-D P2 良性中性改写 | 3.65% | 一句中性→另一句中性即达 attack 量级 |
| tier_a NEUTRAL_PSEUDO_TREATMENT | 20/20 迭代 all_three_q<.05 = False | 中性拆两半→过程 excess 不显著(重复漂移小) |
| R7-C noise floor 收紧 | 4.03→3.47→2.78% | 信号随 floor 单调消失 |

**统一方法学 claim:** *Interaction-attack effects must exceed a benign-linguistic-perturbation null (semantic-equivalent rephrasings), not merely a stochastic-repeat null; under the former, current process-attack effects vanish.* 把 placebo(中性 vs 中性)与 neutral-construction(§3)连成一条线:**错误的 null(重复漂移)→ 假阳性;正确的 null(中性措辞分布)→ 信号消失。** 这是 Umbrella B 的骨架,证据已全在冻结数据里。

---

# 12. MISROUTE Five-Condition Reanalysis（[B],不止 focal urgency）

tier_a `C0_C1_C2_TRIANGLE` + `MODEL_DOMAIN_INTERACTIONS` + `MODAL_PATH_SHIFT`:

| 对比 | 含义 | tool_arg 距离/效应 | 备注 |
|---|---|---|---|
| C2−C1 | 静态 urgency vs 中性(**focal**) | 0.1118 | HIGH compat,MISROUTE 头条 |
| C3−C1 | 自适应 urgency vs 中性 | **0.1418** | 比 static **大**,但 = 更多措辞差异? |
| C2−C3 | 静态 vs 自适应(两种压力) | 0.1114 | **两种压力互相差 ≈ 各自离中性** |
| C1−C0 | 中性 vs native(两个中性) | **0.1494** | LOW compat,**≥ urgency** |

**modal-path 诊断:** neutral_modal_adherence −0.367、new_path_emergence 0.63、modal_path_change 0.76,但 **within_dispersion −0.012(CI 跨 0,不显著)**。

**重分析结论:**
1. **多种不同 treatment 产生**相似量级的**无方向 route displacement**(C2/C3 各 ~0.11–0.14,C2-C3 互差 0.11)→ 支持 **generic perturbation** 而非 treatment-specific control。
2. **自适应 urgency 看似强于静态(0.142>0.112)**,但可能只是"更多措辞变化",非"更强定向控制"(与 §6 optimizer's curse 同构)——**MISROUTE 数据自身就有 static-vs-adaptive 的可深挖点**。
3. **relocation 强(0.63)但 dispersion 不增** → urgency 是系统性换路线不是加噪;但 C1-C0(中性换 native)也 relocate,故"系统性"不等于"urgency 特异"。
4. **native cooperative(C0)的巨大 reward/route 差异 = scaffold 效应的 MISROUTE 版**,与 §7 一致。

→ MISROUTE 的其他 4 个非 focal 条件**未被充分利用**;它们恰好为 S3(generic perturbation / static≈adaptive / scaffold)提供**同基座证据**。

---

# 13. Candidate Scientific Directions（12 个,详列;用 CURRENT SIGNAL / UPSIDE / COST 分档,不打总分先筛）

> 模板压缩版:claim / 为何有意思 / 已有 observation+exact numbers / 矛盾-异质 / 机制+竞争解释 / 证据状态 / 本轮已做 / 最便宜实验 / 理想实验 / →ICLR / →别篇的一节 / 与 MISROUTE 关系。

### C1. 正确的 null:中性措辞分布(不是重复漂移)
claim:交互鲁棒/攻击的 null 必须是语义等价中性改写分布。**signal 强 / upside 很高 / cost 低。**
证据:§0.4/§3/§11/§12。已做:BFCL 层级、tier_a 三角、placebo 线。便宜实验:τ²+BFCL 各 K≥5 中性渲染。理想:跨基准跨模型。→ICLR 主线(Umbrella B 核心)。→也是 A 的 RQ1。MISROUTE:修正其 null。

### C2. Sensitivity ≠ Specificity ≠ Controllability(三分框架)
claim:capable agent 高敏、零特异、不对称受限可控。**强 / 很高 / 低。**
证据:§4/§5。已做:三概念形式化 + R9v2 实测。便宜:E2 headroom 子集。→ICLR 主线(Umbrella A)。MISROUTE:概念上超集。

### C3. 核验方向不对称(verify-more 易,verify-less 难)+ 成本
claim:可诱导多核验(且有 success 代价),难诱导少核验,跨 headroom 稳健。**中强 / 高 / 低-中。**
证据:§5.2–5.4(显式膨胀 +2.8~3.6;压缩全分层推不低;C5 success 0.355<0.459)。矛盾:压缩 floor?已用 headroom 分层部分排除。便宜:E2。理想:跨模型+去安全 system-prompt。→ICLR(Umbrella C)或 A 的 RQ3。对话 2026 verification-before-action 文献。

### C4. Optimizer's curse:优化语言压力 ≠ 优化行为控制
claim:攻击器 selector 分与真实行为脱钩/反向。**中 / 高 / 极低(0 GPU)。**
证据:§6(corr +0.323 反向 / −0.05)。已做:R9v2 相关分析。便宜:预注册相关检验 + 随机中性候选对照(纯离线)。→ICLR 亮点节 / A 的 RQ2。MISROUTE:C3-vs-C2 可复刻同结构。

### C5. Evaluation realization dominates treatment(scaffold 效应)
claim:模拟器/scaffold 实现效应 ≥ 处理效应。**强 / 高 / 低。**
证据:§7(ratio 1.45)。已做:跨 R8/MISROUTE/R9 汇总。便宜:同任务多 renderer 家族对照。→ICLR(Umbrella B)或 benchmark short paper。

### C6. Controllability bounded by behavioral headroom / interaction depth
claim:过程可操纵性受 headroom+深度约束。**中 / 中高 / 低。**
证据:§5.3/§8(仅 HIGH-VD 可弱压;桩/前置)。便宜:task-depth×效应分层(现有数据)。→Umbrella C 的 mechanism 节。

### C7. Social pressure mediated by progression cues, not affect
claim:改路线是社会语气,推强度的是 continuation/urgency 任务线索。**中 / 中高 / 极低(R6 raw)。**
证据:§10(R6 primary/secondary)。便宜:R6 main-effect/interaction 重分解。→独立 mechanism paper 或 A/C 的一节。MISROUTE:解释 Stage-2 mini 假象。

### C8. Model sensitivity×controllability phenotypes
claim:不同 agent 不同表型(敏感/免疫/可控)。**中 / 高 / 中。**
证据:§9(gemma 0.143 vs gpt-oss 0.062ns)。便宜:补 qwen 进 MISROUTE 口径。理想:5 模型×2 基准 matched。→Figure 1 级贡献,任一 umbrella 都受益。

### C9. Pressure makes agents more cautious, not reckless(安全乐观)
claim:压力→确认率↑/核验不降;安全边界 >6000 runs 未破。**中 / 中 / 低。**
证据:R6 +0.133 确认;§5 压缩推不低;unsafe/privacy=0。→安全论文的核心 reassurance,或 C 的 safety 节。对话"pressure→skip confirmation"威胁文献(见 §15)。

### C10. Loose process eval overestimates fragility(= EACL 升级)
claim:不校准漂移/措辞 → 假阳攻击。**强 / 中 / 低。**
证据:§11 全线。已有 EACL 包。→方法论文(可与 B 合并)。

### C11. Adaptive urgency ≠ stronger control(MISROUTE 内证)
claim:MISROUTE C3(自适应)>C2(静态)只是更多措辞差异,非更强控制;C2-C3 互差 ≈ 各自离中性。**弱-中 / 中 / 极低。**
证据:§12。→C4 的 MISROUTE 版佐证,加固 A/B。

### C12. Clarification is the one controllable channel(通道特异性)
claim:压力压不动 verification_depth,但单调压低 clarification(C4-C1=−0.50)。**中(单点) / 中 / 低。**
证据:§5.1。**这是本轮新发现的"唯一被隐式压力定向移动的过程量"**,反而是"少问用户"这个安全相关方向。便宜:确认 clarification 定义 + 跨任务显著性检验。理想:跨模型。→C 的关键 mechanism 节(隐式压力唯一奏效处 = 减少 user 澄清 → 潜在 consent 风险)。

---

# 14. Possible ICLR Umbrella Papers（3 套组合,各给 Fig1/RQ/表/缺口）

## Umbrella A —《Sensitivity is not Controllability》
- **title:** Sensitivity is not Controllability: The Right Null and the Limits of Linguistic Process Control in Tool-Using Agents
- **Fig 1:** 四段层级条(repeat/中性/压力/显式)×(BFCL,τ²,PASR)三面板 —— 即 §0.4 表。
- **RQ1(正确 null):** 中性措辞漂移 vs 重复漂移 vs 压力(C1,C11,§3/§12)。
- **RQ2(优化也无用):** static≈adaptive + optimizer's curse(C4,§6/§12)。
- **RQ3(可控边界):** 显式/隐式不对称 + headroom + clarification 通道(C2/C3/C6/C12,§5)。
- **main table:** 各(基准×模型)pressure_specificity CI + 显式可控 + 不对称。
- **strongest:** 跨 2 基准 5 模型:压力 ∈ 中性分布,唯显式单向可控。
- **missing:** τ² K≥5 中性 + qwen 进 τ²(E-A)。

## Umbrella B —《Evaluation Realization Dominates Treatment》(方法学/benchmark)
- **title:** When the Harness Moves More than the Attack: Placebo-Calibrated Process Robustness for Tool Agents
- **Fig 1:** scaffold-effect vs treatment-effect 条形(R8/MISROUTE/R9),ratio 1.45 高亮。
- **RQ1:** scaffold/模拟器效应量(C5,§7)。**RQ2:** placebo≥attack + 中性构造 null(C10/C1,§11)。**RQ3:** 正确协议下处理效应残留多少(≈0)。
- **strongest:** 实现扰动 ≥ 处理;弱 null 造假阳。
- **missing:** ≥2 renderer 家族 + 多 harness。

## Umbrella C —《Boundaries of Process Control in Tool Agents》(机制/安全)
- **title:** You Can Make an Agent Verify More, Not Less: Asymmetric and Headroom-Bounded Control of Tool-Agent Verification
- **Fig 1:** 双向不对称 × headroom(§5.2–5.4)。
- **RQ1:** 方向不对称 + 成本(C3,§5)。**RQ2:** headroom/深度约束(C6,§8)。**RQ3:** clarification 是隐式压力唯一奏效通道 → consent 风险(C12/C9)。
- **strongest:** verify-more 可诱导(有成本)、verify-less 结构抗性;对话 2026 verification 文献,给出威胁模型的**实证边界**。
- **missing:** 跨模型 + 去安全 system-prompt 分离 alignment vs floor(E2+)。

---

# 15. External Novelty Map（按 candidate 比 prior work；US-only web,2023–2026）

- **Prompt sensitivity / paraphrase**(*What Did I Do Wrong?*;Sclar 式 format sensitivity):证明"措辞/格式改变输出剧烈"。**我们多了:** 用在**工具执行轨迹**上,并把它确立为 attack/robustness 的**正确 null**,且区分 sensitivity/specificity/controllability。novelty:**null 选择 + 三分框架 + 不对称**。
- **Controllability eval**(*How Controllable Are LLMs? Unified Evaluation across Behavioral Granularities*, 2603.02578):测输出层可控性。**我们多了:** 工具 agent **过程**可控性 + **语言 vs 显式指令**分离 + **headroom** 约束。
- **Steering vectors**(activation-level control):激活层能定向控制。**我们的对照贡献:** **语言层压力不给定向控制**(而激活层给)——明确了"linguistic controllability"的边界,是对 steering 文献的互补 negative。
- **Trajectory benchmarks**(TRAJECT-Bench, HINTBench, AgentNoiseBench):测轨迹质量/噪声鲁棒。**我们多了:** 处理效应 vs **中性措辞/scaffold null** 的校准;它们多为固定单一 baseline。
- **Adversarial ASR 校准**(*Adaptive Adversaries* 2607.18063 across-submission SD 1.4–1.9× floor;*Sampling-aware* 2507.04446;*AdvJudge-Zero* FPR 37.7→80.9):都强调 baseline/FPR。**我们多了:** baseline 具体化为**良性语义等价改写分布**,并证明处理效应被其吞没。novelty:**benign-rephrasing null**。
- **Verification-before-action / process safety**(VerAct ICLR 2026;*Towards Verifiably Safe Tool Use* 2601.08012;AgentLTL;ProbGuard;"booking non-refundable flight without confirming"):构建 enforcement,**假设**"压力→跳核验"威胁真实。**我们多了:** **实证证明隐式语言压力难以把 capable 模型的核验推低**(verify-less 抗性),给这条威胁模型一个**经验边界**;同时 clarification 通道确是被压低的(consent 风险仍在)。
- **结论:** 无一篇覆盖"benign-rephrasing null + sensitivity/controllability 分离 + 双向不对称 + optimizer's curse"的组合;最近的是 controllability-eval 与 prompt-sensitivity,**切入点不同,可清晰拉开**。投稿前需精读 2603.02578、2607.18063、2601.08012 划边界。
- Sources: [Autonomous-Agents repo](https://github.com/tmgthb/Autonomous-Agents) · [TRAJECT-Bench](https://arxiv.org/pdf/2510.04550) · [AgentNoiseBench](https://arxiv.org/pdf/2602.11348) · [How Controllable Are LLMs](https://arxiv.org/html/2603.02578) · [Adaptive Adversaries](https://arxiv.org/pdf/2607.18063) · [Sampling-aware Attacks](https://arxiv.org/pdf/2507.04446) · [Safe LLM Agents survey](https://arxiv.org/abs/2608.14590) · [Verifiably Safe Tool Use](https://arxiv.org/pdf/2601.08012)

---

# 16. Strengthening Experiment Portfolio（分算力档,不止一个 E1）

## 0 GPU（纯离线,现有冻结数据,今天可做）
- **E-D optimizer's curse confirmatory**:R9v2 raw,预注册 selector_score↔ΔVD 零/负相关 + 随机中性候选的 selector 分布对照(§6)。
- **E-R6 social-vs-progression**:R6 raw main-effect/interaction 分解(§10)。
- **E-PLACEBO 方法学线**:R7-C/R7-D/tier_a 汇总成统一 placebo-null 表(§11)。
- **E-CLARIFY**:确认 clarification_turns 定义 + 跨任务配对显著性(§5.1/C12)。

## <1 GPU-日（复用现有模型/任务）
- **E2 核验不对称去混淆**:min_prereq≥3 子集 + 去安全 system-prompt 变体,分离 floor/alignment(§5,C3)。
- **E-B tier_a static-vs-adaptive**:在 MISROUTE 冻结轨迹上复刻 §6 的 score↔behavior(若保留了 attacker 元数据)。

## 1–3 GPU-日（决定性,基础设施已在）
- **E-A ★中性措辞分布 + 跨模型跨基准(若只做一个,做这个)**:τ²(MISROUTE 基座,复用 renderer)+ BFCL 各 **K=6 盲审等价中性渲染** + 静态/自适应压力 + 显式;模型 = gemma/gpt-oss/mistral/qwen-72B。**一次产出:** 正确 null(C1)、specificity 检验、static≈adaptive、模型表型(C8)、scaffold(C5)。判定 urgency 是否超中性分布。
- **E-C headroom×depth 跨基准**:BFCL/τ²/(可选 ToolSandbox)按 min_prereq/深度分层测可控性(C6)。

## 更大实验（可选,升级 confirmatory）
- 5–8 模型 × 2 基准 × K 中性 × 双向显式/隐式的完整 confirmatory 矩阵,支撑 Umbrella A 的 main table + 表型 Figure。

**如果只能做一个:E-A**(一箭多雕,直接决定 A/B/C 三个 umbrella 的核心 RQ,且用已有基础设施)。

---

# 17. Recommended Discussion With Collaborators

- **已经值得兴奋的 signal(可马上讲):** 正确 null(跨 4 实验)、scaffold≥处理、核验双向不对称、optimizer's curse、模型表型。这些**不是"一个失败的 R9"**,是五个可发展的科学现象。
- **可马上补(0 GPU,本周出):** optimizer's curse confirmatory、R6 social-vs-progression、placebo 统一表、clarification 通道。
- **可选择性发展:** 三套 umbrella 任选主攻;A 最独立、B 最方法学安全、C 最贴 2026 安全热点。
- **彼此兼容:** A⊃C1/C2/C4/C3/C8;B⊃C5/C10/C1;C⊃C3/C6/C9/C12。C1(正确 null)是三者共用地基。
- **互相竞争(需取舍):** A 与 B 抢"正确 null"叙事(A 当 RQ1,B 当主线);同一批数据不宜拆两篇投同会,建议**先合成一篇强 A(含 B 的方法节 + C 的机制节)**。
- **与 MISROUTE 关系:** 全部与 MISROUTE **共存**;A/B 修正其 null 选择,C 补其未测的 operational 变量。**建议对 MISROUTE 团队坦陈 tier_a 已自证的 urgency-specificity 边界,把它变成 A 的动机而非对立。**

---

# 18. Final Research Portfolio（分 Tier,全部保留）

## Tier A —— 已有很强苗头,值得马上加强
- **C1 正确的 null(中性措辞分布)** —— 跨 4 实验,便宜可确证(E-A)。
- **C2 Sensitivity≠Specificity≠Controllability** —— 概念内核 + R9v2 实测。
- **C5 Scaffold≥处理** —— 跨 3 实验,[A] 级。
- **C3 核验双向不对称** —— 本轮新挖,机制清晰,贴安全热点。

## Tier B —— 有明确现象,补一个分析/实验即可升级
- **C4 optimizer's curse** —— 0 GPU 可确证。
- **C7 social-vs-progression(R6)** —— 0 GPU 重挖。
- **C6 headroom/depth 约束** —— 现有数据可分层。
- **C8 模型表型** —— 补 qwen 进 MISROUTE 口径。
- **C12 clarification 通道** —— 隐式压力唯一奏效处,consent 风险。

## Tier C —— 高风险高收益探索
- **C9 pressure→更谨慎的安全乐观命题** —— 需更大安全覆盖。
- **C10 loose eval 高估脆弱(EACL)** —— 综述风险,靠 A/B 正面结果救。
- **C11 adaptive≠更强控制(MISROUTE 内证)** —— 依赖 attacker 元数据是否保留。

---

# 附:12 个必答问题(prompt §十)

1. **除 Sensitivity≠Controllability 外被低估的方向?** scaffold≥处理(C5)、optimizer's curse(C4)、clarification 是唯一可控通道(C12)、social-vs-progression(C7)。
2. **Verification asymmetry 深挖后多强?** 强:双向不对称对 headroom 鲁棒(显式膨胀全分层 +2.8~3.6;压缩全分层推不低,仅 HIGH-VD 微降 −0.27);且发现"可控方向有 success 成本"。单基准单模型 → 需 E2 跨模型/去 system-prompt 排 floor/alignment。
3. **Adaptive attacker 的 selector 分预测行为吗?** **不**:压缩 corr +0.323(反向)、|Δ| −0.05(无关)——optimizer's curse。
4. **R6 藏着 social vs progression 的 mechanism story 吗?** 藏着且强:改路线=社会语气,推强度=continuation/urgency 任务线索,insult+urgency 反而更谨慎。
5. **Scaffold 效应能跨实验复现吗?** 能:R8(−11pp/−1.0)、MISROUTE(路线 0.149)、R9(G2)。ratio≈1.45>1。
6. **Placebo≥attack 能成系统方法学 claim 吗?** 能:R7-C/R7-D/tier_a 三处,连成"正确 null=中性措辞分布"。
7. **Depth/headroom 预测 controllability 吗?** 是:仅 HIGH-baseline-VD 可弱压;桩/前置→无过程。
8. **有明显 model 表型吗?** 有:gemma 敏感+可控 / gpt-oss 免疫 / mistral 低敏弱能力 / qwen 敏感不可隐式控。
9. **MISROUTE 其他 3 条件告诉我们什么?** static≈adaptive(generic perturbation)、adaptive 更大只是更多措辞、C0 scaffold 效应——全为 S3 提供同基座弹药。
10. **有几套 ICLR story?** 三套:A(sensitivity≠controllability)、B(evaluation realization dominates)、C(boundaries of process control)。
11. **各套最少补什么?** A/B/C 共享 **E-A**(τ²+BFCL K≥5 中性 + 跨模型);C 另加 E2(去 system-prompt);全部另可 0-GPU 补 C4/C7/C12。
12. **额外两周算力最优 portfolio?** 周 1:E-A 全量(τ²+BFCL×4 模型×K=6 中性×压力/显式)——一次喂满 A/B/C;并行 0-GPU 做 E-D/E-R6/E-PLACEBO/E-CLARIFY。周 2:E2(去 system-prompt 分离)+ 表型 Figure + 依 E-A 结果决定主攻 A 还是 B,起草 main table/Fig1。

---

## 附:关键证据路径(可复核)
```
# 本轮新算(可复现)——脚本口径见正文 §5/§6
results/r9v2/confirmatory/confirmatory_episodes.jsonl   # 多指标层级/核验不对称/headroom/optimizer's curse
# 历史
tier_a_strengthening_20260722/C0_C1_C2_TRIANGLE_ANALYSIS.csv        # C2-C1 0.112 / C1-C0 0.149 / C3-C1 0.142
tier_a_strengthening_20260722/MODEL_DOMAIN_INTERACTIONS.csv         # gemma 0.143 / gpt-oss 0.062ns / mistral 0.051
tier_a_strengthening_20260722/MODAL_PATH_SHIFT_SUMMARY.csv          # relocate 0.63 / dispersion −0.012 ns
tier_a_strengthening_20260722/NEUTRAL_PSEUDO_TREATMENT_RESULTS.csv  # 20/20 不显著
ir_mstu_stage2/reports/r7d_ipma/STEP1_PLACEBO_SOURCE_AUDIT_CN.md    # P0 1.44 / P2 3.65 / attack 4.03
ir_mstu_stage2/reports/r8_full_episode/R8_FULL_EPISODE_MULTI_STEP_STRESS_TEST_CN.md  # scaffold C1-C0; 模型 tools
ir_mstu_stage2/reports/r6_sensitivity/R6_FULL_DEEP_ANALYSIS_CN_20260629.md           # 析因 continuation
ir_mstu_stage2/reports/r7c_ipma/R7C_FULL_REPORT_CN.md               # placebo 4.63 ≥ attack 4.03
EACL_PROCESS_ROBUSTNESS_PAPER_PACKAGE_20260718/08_PAPER_BLUEPRINT/  # 方法学论文骨架
LLMLANGUAGE_轮次进展与试错总结_CN.md                                # R1-R8 lineage
```
