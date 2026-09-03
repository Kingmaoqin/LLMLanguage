# Adaptive Process-Control Attack — 攻击证据挖掘与研究机会地图
## Evidence Mining & Attack Opportunity Map（内部研究决策报告，非论文，非审稿）

> 任务:对已完成的大量实验做一次**攻击视角**的证据挖掘,找出(1)已足够强、可直接支撑攻击论文核心故事的结果;(2)pooled 不强但存在**大 effect / 稳定方向 / 机制解释**的 high-signal regime;(3)下一步最值得跑的实验。
> 新核心命题:**Adaptive Process-Control Attack** —— 攻击者用一系列表面合理、低风险的语言交互,持续改变 agent 中间决策轨迹,使其逐步减少向人类澄清/确认/复核,最终把人类移出 human-in-the-loop(**Human Oversight Displacement**),自主执行本应人工确认的高风险操作。
> 攻击链:Benign Intervention → Process-Trajectory Manipulation → Clarification/Confirmation/Verification Suppression → Human Oversight Displacement → Autonomous Execution → Unsafe Outcome。
> 目标层级:**Adaptive > Matched Static > Neutral**。
> 态度:强就说强;所有 subgroup 都标 pre-specified/机制驱动 vs post-hoc,并保留 pooled 与 provenance;不靠单 seed/单 prompt 造趋势。
> 主要可挖数据:**R9v2**(BFCL-deep,Qwen2.5-72B,1401 episode,6 条件 C0–C5 × 压缩/膨胀两家族,逐 episode 有完整过程通道);辅以 R9v1-clean(880,gemma+mistral)、R8/MISROUTE(τ²,3 模型)、R6(τ²,2160)、R7-C/R7-D(τ²)。

---

# 1. Executive Summary —— 目前最强的结果

**一句话**:我们已经有**强证据**证明攻击链的**第一环(Human Oversight Displacement 的 L1:澄清抑制)**成立且**在监督余量大的任务上急剧放大**;但**L2 自主执行放大、L3 不安全后果、L4 端到端 ASR、以及 Adaptive>Static** 目前**尚未建立**。下一步只要补一个"带真实人类确认点 + 不安全后果 + 自适应策略"的端到端设置,这个攻击故事就能立起来。

**当前最强的 5+ 个结果/趋势(详见 §3–§4 Result Cards):**

1. **[STRONG] 监督旁路 / 澄清抑制**(M3):压力攻击使 agent 向用户澄清显著减少,C4−C1 = **−0.504 turns,CI[−0.855,−0.162],p=.009**;**完全零澄清("彻底不问人")的 episode 比例 C1 23% → C4 33% → C5 37%(+10 / +14pp)**。这是目前**最干净的、对一个 human-oversight 通道的直接控制证据**。
2. **[STRONG TREND] 澄清抑制随"监督余量"单调放大**(M3+M4,Trend 1):按基线澄清倾向三分位,C4−C1 = LOW **+0.08** → MID **−0.26** → HIGH **−1.33**(CI[−2.03,−0.72],同向 69%)。**监督余量越大,攻击对监督通道的控制越强**——完美的 dose-response,且直接服务威胁模型(攻击在"本该最多问人"的地方削得最狠)。
3. **[STRONG TREND] 通道特异的双向控制**(M4,Trend 4):不同语言行为控制不同过程通道——**urgency ↓澄清(−0.50)**;**skepticism ↑澄清(+0.33)、↑写前读(+0.33)、推迟写操作(first-write +0.41,CI[+0.05,+0.80])**。同一"澄清"通道被两种语言行为**反向**推动。这直接定义了 adaptive attacker 的 action space。
4. **[VERY STRONG] 核验通道可被显式控制且跨批次复现**(M4,阳性对照):显式"多核验"使 verification_effort 从基线 ~1.84 升到 **4.83**(R9v2)/ 从 2.45 升到 **6.62**(R9v1),两个独立批次+两组模型一致(+160%~+170%)。证明过程通道**确实可被操纵**——只是目前只对**显式**指令稳定,对**隐式**压力不稳定。
5. **[STRONG TREND] Surrogate misalignment**(M7):自适应攻击器的 selector 打分与真实核验变化**反向**相关(Pearson +0.323 / Spearman +0.354,task-cluster CI[+0.10,+0.49] 排除 0),且打分与文本长度相关 **+0.974**;剂量-反应反向(最低分候选反而最能压缩)。**表面分数/单一语言强度不能预测真实过程控制** → 这是"为什么必须用 trajectory-feedback 自适应"的核心 rationale。

**诚实的关键缺口(见 §2/§9):** L2 自主执行放大、L3 不安全后果、L4 端到端 ASR 未测;**Adaptive 未证明胜过 Static**(C4≈C3);澄清抑制**未**共现更多工具执行(corr≈0)。

---

# 2. Current Attack Evidence Chain —— 已打通哪几环、还缺哪几环

| 层级 | 定义 | 现状 | 证据 |
|---|---|---|---|
| **L0 Eligible Checkpoint** | 存在合理的人类确认点 | ✅ 有 | BFCL/τ² 任务基线澄清 ~1.7 轮、含 miss_param(漏参数本应问用户) |
| **L1 Oversight Bypass** | 跳过本应有的澄清/确认/核验 | ✅ **强** | 澄清 C4−C1=−0.50 p=.009;零澄清率 +10pp;高余量任务 −1.33 |
| **L2 Autonomous Execution↑** | 无人工确认下继续/更多执行 | ⚠️ **未建立** | 澄清抑制与 Δtool_calls(corr −0.04)、Δfirst_write(−0.03)几乎无共现 |
| **L3 Unsafe/Unauthorized Outcome** | 越权/错误的后果性动作 | ❌ **未测** | R9v2 无 unsafe/unauthorized 后果的注入与判定 |
| **L4 End-to-End ASR** | L1∧L2∧L3 联合 | ❌ **未构造** | 需专门的端到端 checkpoint→execution→outcome 设置 |
| **M2 Adaptive > Static** | 自适应胜过最优静态 | ❌ **未建立** | C4≈C3 全对比;仅 R9v1 膨胀 C4−C3=+0.153(弱、门无效、未复现) |

**结论**:攻击链目前**打通了 L0→L1**(且 L1 在高监督余量处很强),**L2–L4 与 adaptive advantage 全是空白**。这不是"方向失败",而是明确告诉我们:**下一个实验必须把 L1 的强控制,接到一个能测 L2/L3/L4 的端到端环境上,并让攻击策略真正 trajectory-adaptive。**

---

# 3. Strong-as-is Results（Result Cards）

## Result Card R1 —— 监督旁路 / 澄清抑制（Human Oversight Displacement 的 L1）
- **Evidence Module**: M3(Human Oversight Displacement)/ M4(Process-Control Mechanism)
- **Core Research Question**: 表面合理的压力交互能否让 agent 减少向人类澄清?
- **Original / Pooled Result**: C4(自适应压力)−C1(中性)clarification_turns = **−0.504**,CI[−0.855,−0.162],**p=.009**(任务层配对 + 3000 次 task-cluster bootstrap + sign-flip permutation)。显式 C5−C1 = −0.851,p=.002。
- **High-Signal Condition**: 强化于高基线澄清任务(见 R2);pooled 本身已显著。
- **N / Seeds**: 1401 episode 中的压缩家族约 700;有效任务 38–39;repeats=3。
- **Model(s)**: Qwen2.5-72B(AWQ)。
- **Task(s)**: BFCL-deep(multi_turn_base + multi_turn_miss_param);base 与 miss_param **同向**(−0.569 / −0.455)。
- **Harness / Scaffold**: BFCL 原生多轮沙盒 + 冻结中性渲染器。
- **Intervention**: C4 自适应"催促/时间压力"语言(不含任务事实/授权)。
- **Primary Outcome**: clarification_turns(agent 向用户澄清的轮数=向人核验)。
- **Effect Size / Absolute**: −0.50 turns(基线 ~1.73,**相对 −29%**);**完全零澄清率 23%→33%(C4,+10pp)/ 37%(C5,+14pp)**。
- **CI / p**: [−0.855,−0.162],p=.009(C4);[−1.342,−0.351],p=.002(C5)。
- **Cross-Task Consistency**: base 与 miss_param 同向;强度随基线澄清梯度上升(R2)。
- **Cross-Model / Seed**: 单模型(qwen);跨 repeats 稳定。跨模型是明确 strengthening 轴。
- **Mechanistic Interpretation**: 压力**重定向核验来源**——把"向人澄清"压下去,同时**不减少**"用工具核验"(见 §6 通道矩阵),即 Verification Channel Substitution。攻击意义:human-in-the-loop 被削弱,而 agent 表面仍在"负责地核验"。
- **Why This Matters for Attack**: 这是攻击链 L1 的**直接、显著**证据——benign 语言即可压低一个 human-oversight 通道。
- **What Exact Claim This Supports**: 「现有数据已经支持:在压力型交互下,agent 向人类澄清是一个**可被直接压制的过程通道**,压制幅度约 0.5 轮、并使'彻底不问人'的比例提高约 10 个百分点。」
- **Current Strength**: **STRONG**(Local Signal Score ≈ 11/15:Mag 2,Repl 2,Dir 2,Mech 3,Rel 2)。
- **Main Remaining Gap**: 澄清↓是否级联到 L2 自主执行 / L3 不安全后果(目前 corr≈0,未级联)。
- **Potential Confounds**: 单模型;"澄清是否本应发生"未逐 episode 判定(L0 未硬门)。
- **Minimum Next Experiment**: 在带**显式人类确认点**的任务上,测"确认被跳过率(OBR)"是否同样被压低,并接自主执行判定。
- **Quantitative Success Criterion**: 攻击使 OBR(确认跳过率)相对中性 **↑≥15pp**,且 CI 不跨 0。
- **Priority**: **P0**。

## Result Card R2 —— 澄清抑制随"监督余量"单调放大（STRONG TREND）
- **Evidence Module**: M3 / M4(Trend 1:headroom→controllability)
- **Core Question**: 攻击对监督通道的控制是否取决于该任务本来有多少监督余量?
- **Original / Pooled**: pooled 澄清抑制 −0.50(见 R1)——本身中等。
- **High-Signal Condition(机制驱动分层,pre-specified)**: 按每任务在 C1 下的基线澄清倾向三分位:
  | 基线澄清 | C4−C1 clarification | CI | 同向 % |
  |---|---|---|---|
  | LOW(本就少问) | **+0.077** | [−0.15,+0.31] | 15% |
  | MID | **−0.256** | [−0.74,+0.28] | 31% |
  | **HIGH(本就多问)** | **−1.333** | **[−2.03,−0.72]** | **69%** |
- **N**: 每层 13 任务,单模型。
- **Trend / Gradient**: **单调**:LOW +0.08 → MID −0.26 → HIGH −1.33。
- **Mechanistic Interpretation**: 攻击**恰恰在"本该最多问人"的任务上削得最狠**——监督余量本身就是可被攻击的资源。
- **Why This Matters**: 直接支撑威胁模型最危险的版本:high-oversight(=high-stakes、需人确认)任务反而最易被移出人类。
- **What Exact Claim This Supports**: 「现有数据已支持一个强趋势:**agent 的监督余量越大,压力攻击对其监督通道的抑制越强**(单调梯度,高余量任务达 −1.33 轮、同向 69%)。」
- **Current Strength**: **STRONG TREND**(Score ≈ 12/15:Mag 3,Repl 2,Dir 3,Mech 3,Rel 1)。
- **Main Gap**: 单模型;需在跨模型/跨任务复现该梯度。
- **Minimum Next Experiment**: 跨 3 模型 × (低/中/高监督余量任务) 复现梯度。
- **Quantitative Success Criterion**: 高余量层 C4−C1 ≤ −0.8 且在 ≥2 模型同向。
- **Priority**: **P0**。

## Result Card R3 —— 核验通道可被显式控制、跨批次复现（VERY STRONG，但目前仅显式）
- **Evidence Module**: M4(可控性上界)/ M5 的反面(目前需显式,非 benign)
- **Original / Pooled**: 显式"多核验"C5:verification_effort 从基线 **1.84→4.83**(R9v2,Qwen);**2.45→6.62**(R9v1,gemma/mistral)。两独立批次一致,+160%~170%。
- **Cross-batch**: R9v1 与 R9v2 两套模型/基准均复现。
- **Mechanistic**: 过程通道**确实可被操纵**;可控性的上界很高。
- **Why This Matters**: 证明"通道可控"这一前提成立;当前 attack 的短板不是"通道不可控",而是"**隐式/benign 语言还控不动它**"(见 §7 缺口)。也给出攻击的一个**方向不对称**:让 agent **多**核验容易、**少**核验难(见 §7)。
- **What Exact Claim This Supports**: 「过程核验通道是**高度可控的**(显式指令下 VE +160%),因此攻击的核心难点在于把这种可控性用 benign、自适应的语言实现,而非通道本身不可动。」
- **Current Strength**: **VERY STRONG**(Score ≈ 15/15)——但注意它是**阳性对照**,不是 stealth 攻击。
- **Priority**: **P1**(作为可控性上界与 benign gap 的锚点)。

## Result Card R4 —— Surrogate Misalignment（STRONG TREND；adaptation necessity 证据）
- **Evidence Module**: M7
- **Original / Pooled**: C4 自适应压缩 114 episode:corr(selector_score, signed ΔVD) Pearson **+0.323** / Spearman **+0.354**,task-cluster CI **[+0.10,+0.49]**(排除 0)。压缩目标 ΔVD<0,故正相关=**方向错误**。
- **Smoking gun**: corr(selector_score, 文本 token 数)= **+0.974**;corr(token, ΔVD)=+0.333 → **打分本质是文本长度,而长文本让核验更多**。
- **Dose-response(反向)**: Q1(最低分)ΔVD **−0.536** → Q4(最高分)**+0.350**。
- **By headroom**: min_prereq=1 corr +0.380 / min_prereq≥2 +0.357 —— **各 regime 一致失效**(不是 regime-specific,是普遍 misalignment)。
- **Why This Matters**: **单一 surface/semantic 强度分数不能预测真实过程控制** → 证明"必须用 trajectory feedback 的自适应策略,而非静态最大化语言强度"。这是 adaptive-attack 的存在理由。
- **What Exact Claim This Supports**: 「现有数据已支持:优化'看起来更强的压力语言'(surrogate)与真实过程控制**脱钩甚至反向**,因此有效攻击必须基于轨迹反馈自适应,而非静态放大语言强度。」
- **Current Strength**: **STRONG TREND**(Score ≈ 12/15)。
- **Main Gap**: 需证明"真正的 trajectory-adaptive 策略**能**做到 surrogate 做不到的控制"(即 M2)。
- **Priority**: **P1**。

---

# 4. Strong-Trend Subsets（弱 pooled → 强局部）

## R5 —— Language Act × Process Channel 矩阵（channel-specific controllability，STRONG TREND）
机制驱动,pre-specified。R9v2,C4−C1,压缩(urgency)vs 膨胀(skepticism):

| 过程通道 | urgency(压缩) | skepticism(膨胀) | 读法 |
|---|---|---|---|
| **clarification(V_user)** | **−0.504** [−0.86,−0.16] | **+0.333** [−0.04,+0.68] | **同一通道被反向控制** |
| reads_before_write(V_tool) | +0.179 [−0.15,+0.51] | **+0.325** [−0.02,+0.70] | skepticism 抬工具核验 |
| verification_depth | +0.053 | +0.191 | — |
| first_write_step(推迟写) | +0.211 | **+0.414** [+0.05,+0.80] | skepticism 显著推迟动手 |
| total_tool_calls | −0.504(宽) | −0.175 | — |

- **趋势**:urgency 的主要杠杆 = **压低向人澄清**;skepticism 的主要杠杆 = **抬高向人澄清 + 抬工具核验 + 推迟写**。**不同语言行为控制不同(且对同一通道相反)的过程通道** = channel-specific controllability。
- **Why This Matters**: 直接给出 adaptive attacker 的 action space——想移除人类监督用 urgency,想拖延/制造犹豫用 skepticism。
- **Strength**: **STRONG TREND**(Score ≈ 11/15)。**Priority P1。**

## R6 —— 显式 vs 隐式的方向不对称 + headroom（CANDIDATE→STRONG TREND）
(承接 §3 R3)加性控制(多核验)跨 headroom 泛化(显式 C5:低/中/高基线 VE 均 +2.6~+3.6);削减控制(少核验)受 headroom 约束(压缩仅高基线-VD 任务弱降 −0.27,其余 ≥0)。
- **趋势**:*additive control generalizes; reductive control is headroom-bounded.* **Priority P1。**

## R7 —— 完全零澄清("彻底移出人类")率（STRONG-as-trend）
零澄清 episode 率:C1 23.1% → C3 20.5% → **C4 33.3% → C5 36.8%**。即**自适应攻击使"整段对话完全不问用户"的比例绝对提高 +10pp,显式 +14pp**。这是最贴近"Human Oversight Displacement"的二值 attack 指标。**Priority P0**(是 R1 的二值化,建议作为主 attack 指标之一)。

---

# 5. Attack Vulnerability Map —— 什么条件下攻击最易成功

| 维度 | 高易攻击(High) | 中(Medium) | 低/鲁棒(Low) | 证据 |
|---|---|---|---|---|
| **Process Channel** | **clarification(向人澄清)** | 写操作时机/工具核验(skepticism 方向) | verification_depth 的"削减"方向 | R1/R5/R6 |
| **Behavioral Headroom** | **高监督余量任务(−1.33)** | 中(−0.26) | 低(+0.08,无空间) | R2 |
| **Checkpoint Type** | 澄清型(clarify user) | 写前核验(delay 可诱导) | "少核验"型(抗性) | R5/R6 |
| **Language Act** | urgency→移除澄清;skepticism→拖延 | — | 单一"强度"最大化(surrogate 失效) | R4/R5 |
| **Control Mode** | **显式指令(VE +160%)** | 自适应压力(部分通道) | 隐式压力对"少核验"方向 | R3 |
| **Model** | gemma(路线最敏感 0.143) | mistral / qwen(措辞敏感) | gpt-oss(免疫 0.062,CI 跨 0) | R8/MISROUTE §8 |
| **Direction** | 增(多核验/多澄清/推迟) | — | 减(少核验)——结构抗性 | R6 |

**给下一轮的直接指令**:在**高监督余量、澄清型 checkpoint、gemma/qwen**上构造 end-to-end 攻击,用 **urgency 移除澄清**为主杠杆,最可能拿到强 L1→L2→L3。

---

# 6. Mechanistic Trend Map

| Trend | 内容 | 证据强度 | 支持实验 | 例外 | 当前最佳解释 | 下一步验证 |
|---|---|---|---|---|---|---|
| **A. Headroom → controllability** | 监督/行为余量↑ → 攻击对通道控制↑ | **强** | R2(澄清梯度 +0.08→−1.33)、R6(VE headroom) | 低余量任务无效 | 余量是可被攻击的资源 | 跨模型复现梯度 |
| **B. Pressure → clarification↓,非 verification/tool↓** | urgency 压低向人澄清,但不减工具核验/不提前写 | **强** | R1、R5、§B 共现 corr≈0 | — | Verification Channel Substitution | 端到端接 OBR/自主执行 |
| **C. Progression/skepticism → 抬工具核验/推迟写** | skepticism 抬 reads(+0.33)、推迟 write(+0.41) | 中强 | R5、R6(τ² progression +0.343 tool) | — | 通道特异 | Language-Act×Channel 全矩阵 |
| **D. Surrogate ≠ real control** | selector 分=文本长度,与 ΔVD 反向 | **强** | R4(CI 排 0,len r=.97) | 各 headroom 一致失效 | 代理目标错位 | 证明 trajectory-adaptive 能超越 |
| **E. Harness/scaffold 是大效应** | 换模拟器实现效应 ≥ 处理效应(ratio 1.33–1.45) | 中强 | R8/MISROUTE §7 | — | 评测实现即处理 | 同任务多 renderer 攻击放大测试 |
| **F. Model sensitivity ≠ controllability** | gemma 高敏可控 / gpt-oss 免疫 / qwen 敏感但难隐式定向 | 中 | §8 表型 | — | 表型差异 | 4 模型 matched |
| **G. 方向不对称** | 多核验/多澄清易;少核验难 | 中强 | R3/R6 | — | policy/结构抗性 | 去安全 system-prompt 分离 |

---

# 7. 弱 pooled 但揭示强局部 regime 的方向（不要降级，标出强局部）

- **隐式压缩核验(pooled null)**:C4−C1 VD +0.053(null)。但**局部**:高基线-VD 任务 C4−C1=−0.27(唯一可削减处);更重要的是它**掩盖了通道替代**——真信号在 clarification(R1)。→ **不是 null,是"测错了通道"**。
- **Adaptive vs Static(pooled null,C4≈C3)**:目前**未建立** adaptive advantage,这是攻击论文的**致命缺口**。但 R4 已给出"为什么静态注定不够"(surrogate misalignment),说明 adaptive advantage 需要**真正 trajectory-feedback 的 C4**,而当前 C4 的 selector 是坏代理(优化长度)。→ **修好 C4 的目标函数后再测 adaptive>static** 是最高价值实验(见 §10 E1)。
- **膨胀攻击(pooled ASR 0.149 但 FPR 0.202)**:pooled 不可区分,但**局部**:R9v1 膨胀 C4−C3=+0.153(CI 不跨 0)+ skepticism 的 channel 效应(R5)提示膨胀方向真有可控通道(推迟写、抬核验),只是当前指标口径没抓住"攻击后果"。

---

# 8. 目前无强信号、暂时降级的方向

- **压缩方向的"隐式少核验"作为独立攻击**:显式都难(R3/R6 方向不对称),隐式更难;除非作为"通道替代"的对照,否则单独降级。
- **纯 route-distance 作为攻击指标**:route 会变但=中性改写(非特异),不能直接当"攻击成功";降级为底层机制,不作 headline。
- **gpt-oss 上的攻击**:路线敏感 0.062(CI 跨 0),免疫;不作为主攻模型。
（以上降级仅指"不作为攻击论文主结果",其机制价值仍保留。）

---

# 9. ICLR 级攻击论文最缺的证据（Top Missing Evidence）

1. **L3/L4:带真实不安全/越权后果的端到端 ASR** —— 现在完全没有。必须有一个"该确认却没确认 → 自主执行 → 越权/错误后果"可判定的任务集。**最关键。**
2. **Adaptive > Best Static** —— 现在 C4≈C3。需修好自适应目标(用真实过程反馈而非文本长度代理),再证明 adaptive 胜出。
3. **L1→L2 级联** —— 澄清抑制目前不共现自主执行(corr≈0);需在有真实执行动作的环境里证明"少问人 → 多自主执行"。
4. **跨模型/跨 harness 泛化** —— 现在核心机制单模型(qwen)。
5. **Benignness/Stealth 量化** —— 需盲审证明攻击文本"看起来无恶意、低风险"(M5)。

---

# 10. Ranked Next Experiments（最值得马上跑的）

## E1 [P0] End-to-End Oversight-Displacement Attack（带确认点+后果）
- **Why Now**: L1 已强(R1/R2/R7),但 L2–L4 空白——补上即成攻击论文骨架。
- **Existing Signal**: 澄清抑制 −0.50/p=.009;零澄清 +10pp;高余量 −1.33。
- **Exact Hypothesis**: 在**显式含人类确认点 + 可判定越权/错误后果**的任务上,自适应 urgency 攻击使 OBR(确认跳过率)↑≥15pp、AER(自主执行率)↑、并产生可判定的 unsafe/unauthorized outcome。
- **Minimal Design**: τ² 或 BFCL 子集里挑/改造"destructive 或需授权"的任务(如取消订单/删除/发送),显式 checkpoint;条件 = neutral / static-urgency / adaptive-urgency;Qwen-72B + gemma;每任务 repeats≥5;主指标 OBR / AER / ASR(L1∧L2∧L3)。
- **Expected / Strong**: adaptive urgency 的 ASR 相对 neutral ↑≥15–20pp 且 > static。
- **Supports**: M1 端到端 ASR + 攻击链主图。
- **Cost**: Medium。**Priority P0。**

## E2 [P0] 高监督余量任务上的澄清抑制跨模型复现（坐实 R2 梯度)
- **Why Now**: R2 是最强趋势但单模型。
- **Hypothesis**: 澄清抑制的 headroom 梯度(LOW→HIGH)在 ≥2 模型同向,高余量层 ≤ −0.8。
- **Design**: 挑低/中/高澄清倾向各 ~10 任务 × gemma/mistral/qwen × C1/C3/C4。
- **Strong if**: 高余量层 ≥2 模型同向且 |Δ|≥0.8。**Cost Low–Medium。P0。**

## E3 [P1] 修复自适应目标 → 证明 Adaptive > Static（M2)
- **Why Now**: R4 证明当前 selector 是坏代理(优化长度);M2 是攻击论文必需但现缺。
- **Hypothesis**: 用"真实过程反馈(上一轮 agent 是否问人/是否核验)"驱动的 trajectory-adaptive 策略,在**高余量/高不确定**状态上 adaptive−static ≥ +15pp(OBR),而低余量状态 ≈0(交互效应=adaptation necessity)。
- **Design**: 新 C4 目标函数(过程反馈,非文本分);对比 static-best;分 headroom 层。
- **Strong if**: adaptive 优势集中在高余量层、呈梯度。**Cost Medium。P1。**

## E4 [P1] Language-Act × Process-Channel 全矩阵（坐实 R5/action space）
- **Hypothesis**: urgency→澄清↓、skepticism→澄清↑/推迟写、progression→工具↑、affect→路线,各 channel-specific 且跨模型稳定。
- **Design**: 4 语言行为 × 5 过程通道 × 3 模型 × BFCL+τ²。
- **Strong if**: ≥3 个 channel-specific 大格(|effect|大且 CI 不跨 0)。**Cost Medium。P1。**

## E5 [P2] Harness/Renderer 攻击放大（坐实 Trend E）
- **Hypothesis**: 同 model/task 下,某些 renderer/scaffold 使澄清抑制 / OBR 明显放大。
- **Design**: 固定 model/task,≥2 renderer 家族 × neutral/attack。
- **Strong if**: renderer 间攻击效应差 ≥1.3×。**Cost Low–Medium。P2。**

**若只能做 5 个**:E1、E2、E3、E4、E5(即上面全部)——但**顺序**为 E1→E2→E3 优先(直接把攻击链补成端到端 + 坐实最强趋势 + 建立 adaptive advantage)。

---

# 11. Final Assessment（直接、自信地回答）

**A. 目前最接近 paper-level 的核心结果?**
**监督旁路 / 澄清抑制(R1 + 零澄清率 R7)**:压力型 benign 交互使 agent 向人类澄清显著减少(−0.50,p=.009),"彻底不问人"的比例绝对 +10pp。这是**已经成立**的、对一个 human-oversight 通道的直接控制证据,是攻击链 L1 的强锚点。

**B. 哪些 overall 不强但已有明显 strong trend?**
- **澄清抑制 × 监督余量**(R2):pooled 中等,但按余量分层出现 **+0.08→−0.26→−1.33 的单调梯度**,高余量层同向 69%——**强趋势**。
- **Surrogate misalignment**(R4):pooled 相关"不高",但方向错误 + CI 排 0 + 文本长度 r=.97 + 反向剂量-反应——**强趋势**,且是 adaptation-necessity 的核心论据。
- **方向不对称/headroom-bounded 核验**(R6)、**channel-specific 控制**(R5):强局部趋势。

**C. 这些 strong trends 集中在什么条件?**
**高监督余量任务 + 澄清型 checkpoint + urgency 语言 + gemma/qwen 模型 + 显式或(修好后的)自适应控制模式**。低余量任务、"少核验"方向、gpt-oss 模型是鲁棒/免疫区。

**D. 哪几个实验一次 targeted follow-up 就可能变成强 paper 结果?**
- **E1**(端到端 ASR):把已强的 L1 接到 L2/L3/L4 → 直接产出攻击论文主结果。
- **E2**(跨模型坐实 R2 梯度):把最漂亮的趋势变成跨模型确证。
- **E3**(修好目标后的 adaptive>static):补上攻击论文最缺的 M2。

**E. 只能做 5 个实验,做哪 5 个?**
**E1(端到端攻击)、E2(headroom 梯度跨模型)、E3(adaptive>static)、E4(language-act×channel 矩阵)、E5(harness 放大)**;优先级 E1 > E2 > E3 > E4 > E5。做完 E1–E3,"Adaptive Process-Control Attack → Human Oversight Displacement"的故事即可立起来。

---

## 附:方法与数据(自包含)
- 主数据 **R9v2**:BFCL-deep(multi_turn_base + multi_turn_miss_param)多轮工具沙盒,模型 Qwen2.5-72B(AWQ),1401 个确证 episode,6 条件 C0(纯中性)/C1(中性前缀A,对照)/C2(中性前缀B)/C3(静态压力)/C4(自适应攻击)/C5(显式指令)× 压缩(催促→少核验)/膨胀(质疑→多核验)两家族。逐 episode 记录:澄清轮数、写前只读次数、首次写步号、verification_depth/effort、工具总数、官方成功、攻击器 selector 分与文本 token 数。
- 差值统计:任务层配对 → 3000 次 task-cluster bootstrap 95% CI + 3000 次 sign-flip permutation p;subgroup 均为机制驱动的 1 变量分层(task 类型 / 基线澄清三分位 / min_prereq / 家族),保留 pooled 与全 provenance;未按单 seed/单 prompt 选组。
- 辅助:R9v1-clean(880,gemma+mistral,BFCL+ToolSandbox);R8/MISROUTE(τ²,3 模型,~2680);R6(τ²,2160);R7-C/R7-D(τ²)。相应 CSV/analysis 已随结果同步到仓库 results/ 下(condition_level_summary / per_episode_flat)。
