# MISROUTE 之后的科学机会图谱 · V3（清晰完整版）
## Post-MISROUTE Scientific Opportunity Map — V3

> 本版目的:把 V2 里每一个科学发现都**写清楚**——目标是什么、实验怎么设计、用了哪个数据集/哪个模型/多少任务多少 episode、每个 metric 精确含义、结果数字(含不确定性)、以及怎么解读。合作方应能**独立读懂每一节**,不必回看前几版。
> V2(`..._V2.md`)保留不动。本版是它的"讲清楚"重写。
> 所有"本轮新算"的数字都回到 raw JSON/JSONL 复现,统计口径见 §0.4。

---

# 0. 阅读须知：共享设定（所有后续章节都用这套术语，只定义一次）

## 0.1 用到的基准数据集（benchmark）

- **BFCL(Berkeley Function-Calling Leaderboard）multi-turn**:多轮工具调用任务。agent 在一个**有状态的沙盒**里(例如一个模拟文件系统 GorillaFileSystem)接收用户请求,通过调用工具(读文件、写文件、移动等)完成任务。官方评测器在结束时比对**最终状态是否等于标准答案**,给 0/1。
  - 本项目用的是 **"BFCL-deep"**,即两个子类别合起来:
    - `multi_turn_base`:标准多轮任务。
    - `multi_turn_miss_param`:用户**故意漏掉一个必要参数**,agent 要么**问用户补参数**、要么**自己用工具查/推断**。这是区分"向人核验"和"自主核验"的最佳任务类型(§3 用到)。
- **τ²-bench(tau2)**:航空(airline)+ 零售(retail)客服任务。agent 与一个**模拟用户**多轮对话并调用工具,官方 `evaluate_simulation` 给 reward。MISROUTE / R8 / R6 用它。
- **ToolSandbox**:已弃用(核验链太浅,信噪比低)。

## 0.2 用到的模型（model）

| 模型 | 在哪些实验里 | 备注 |
|---|---|---|
| **Qwen2.5-72B-Instruct(AWQ 量化)** | **R9v2 全部确证实验**(§3/§4/§5) | 本地唯一通过 BFCL-deep 能力带 [0.40,0.90] 的模型(中性成功率 0.438);故 R9v2 是**单模型**。这是明确的 strengthening axis(补跨模型),不是缺陷。 |
| gemma-4-31b / gpt-oss-120b / mistral-small-3.2-24b | MISROUTE / R8 / R6(§6/§7/§8/§9) | 三模型,可做模型异质性比较 |
| Qwen2.5-32B(0.250)、Llama-3.3-70B(0.125) | R9v2 校准 | 未过 BFCL-deep 能力带,未进确证 |

**为什么单模型不等于"弱证据"**:Qwen-72B 在 R9v2 上提供的是**最干净的、机制级、逐 episode 的因果/过程证据**(有完整的工具轨迹、写前读数、澄清轮数等)。跨模型验证是下一步最直接的加强轴(§15),而不是否决当前发现的理由。

## 0.3 R9 的六个用户条件（condition C0–C5）——这是理解 §3/§4/§5 的关键

同一个任务,只改"用户怎么说话",工具/权限/任务事实/初始状态/评测器全固定。六个条件:

| 条件 | 用户说话方式 | 作用 |
|---|---|---|
| **C0** | 纯中性,无前缀 | 能力基线 |
| **C1** | 中性礼貌前缀 A(如"谢谢你帮忙") | **对照组**——所有攻击都与它比 |
| **C2** | **另一种**中性礼貌前缀 B(如"感谢你的耐心") | 测"换个中性说法本身会不会改行为"的基线 |
| **C3** | **静态**过程压力(固定的催促/质疑话术) | 非优化攻击 |
| **C4** | **自适应**优化攻击(每轮生成候选压力话→双模型评审→选择器挑最强) | 优化攻击 |
| **C5** | **显式指令**(直接命令 agent:压缩家族="别检查那么多,直接做";膨胀家族="请务必反复核验") | 阳性对照——证明"目标行为是能被移动的" |

**两个家族(family)**,每个 episode 属于其一:
- **压缩(compression)**:压力 = 催促("快点")。假设:让 agent **写前少核验**(verification_depth 下降)。
- **膨胀(inflation)**:压力 = 质疑("你确定吗")。假设:让 agent **多核验**(verification_effort 上升)。

## 0.4 统计口径（所有"C_treat − C1"差值都这样算）

- **配对在任务层(task-level paired)**:对每个任务,分别算该任务在**处理条件**(如 C4)和在 **C1** 下该 metric 的均值,相减 = 该任务的效应;再对所有任务的效应求均值 = 报告的点估计。
- **task-cluster bootstrap 95% CI**:对**任务**(不是 episode)有放回重采样 3000 次,每次重算均值 → 取 2.5%/97.5% 分位。因为同一任务内多个 episode 相关,必须按任务聚类。
- **sign-flip permutation p 值**:把每个任务的效应随机翻正负号 3000 次,统计 |重排均值| ≥ |实测均值| 的比例 = 双侧 p。检验"真实效应是否可能只是零附近的波动"。
- **读法**:CI 不跨 0 且 p 小 = 稳健;CI 跨 0 = 该方向上"没测到稳健效应"(不等于"证明为零")。

---

# 1. 一段话总览（这两个月的科学图景）

能力强的工具 agent 在用户施加交互压力时,**不是变得更草率,而是重新分配了行为**:它把"向人核验"换成"用工具核验"(§3,核验总量守恒);它的工具路线对**任意措辞**都漂移、但不被压力**定向**操纵(§8/§11);自适应攻击器"优化"出来的其实只是更长的文本、并不带来更强的行为控制(§5);而"用哪个用户模拟器实现"本身造成的行为差异,和"用户是否施压"一样大甚至更大(§7)。**结论:"压力→跳过核验→不安全"这个被广泛假设的威胁,在能力强的模型上被数据修正为"压力→少问人、自主兜底、核验总量不变"。**

---

# 2. 核心概念框架：Sensitivity / Specificity / Controllability（三个不同的东西）

很多"攻击/鲁棒性"工作只测第一个,把三者混为一谈。本项目要分开:

- **Sensitivity(敏感性,无符号)**:行为**有没有变**。度量 = 处理条件与 C1 的轨迹距离 ‖route(T)−route(C1)‖。**实测:对一切处理都高**(路线距离 ~0.19–0.20)。
- **Specificity(特异性)**:这种变化**有没有超过"良性中性改写"**。度量 = S(处理) − S(换个中性说法)。**实测:压力 ≈ 0(即压力不比换个中性说法更能改行为);显式指令 > 0。**
- **Controllability(可控性,有符号,且分通道)**:变化是不是**朝攻击者想要的方向**、且稳健。**实测:随"过程通道"不同而相反**——压力压不低"用工具核验",却能压低"向人澄清"(§3)。

**一句话**:"能被扰动"(sensitive)、"被这个处理特异地扰动"(specific)、"被朝想要方向操纵"(controllable)是三件不同的事。capable agent = **高敏感 + 零特异 + 分通道的不对称可控**。

---

# 3. 发现一：Verification Channel Substitution（核验的通道替代）★本轮最强新机制

## 3.1 目标（要回答的科学问题）
压力到底是**减少了核验**,还是**改变了核验的来源**?
把总核验拆成三个通道:
```
V_total = V_user（向用户提澄清/确认）
        + V_tool_prewrite（写状态前的只读工具核验）
        + V_tool_post（写后检查）+ 其它
```
假设(Channel Substitution):压力降低 **V_user**,但不降低 **V_tool**,总量守恒——即改变"向谁核验"而非"是否核验"。

## 3.2 实验设计
- **数据集/模型**:BFCL-deep(base + miss_param),Qwen2.5-72B,压缩家族的确证 episodes。
- **条件对比**:C4(自适应攻击)−C1(中性对照),以及 C5(显式"少核验")−C1;C3(静态压力)−C1 作参照。
- **统计**:§0.4 的任务层配对 + task-cluster bootstrap + permutation。有效任务约 38–39 个。

## 3.3 metric 精确定义
- **clarification_turns(= V_user,向人核验)**:该 episode 中 agent **向用户提出澄清/追问**的对话轮数。越高=越多地把人纳入回路。
- **reads_before_first_mutation(= V_tool_prewrite,向工具核验)**:第一次**写操作(改变状态的工具调用)之前**,agent 发起的**只读工具调用次数**。越高=写前查得越多。
- **first_state_changing_step**:第一次写操作发生在第几步。越小=越早动手(证据不足就写)。
- **total_tool_calls**:该 episode 工具调用总数。
- **success**:官方评测器 0/1(最终状态是否等于标准答案)。
- **wrong_state_changing**:结局分类为"做了错误的写操作"的比例。

## 3.4 结果（点估计 [95% CI] p 值）

**(a) 向人核验(clarification）—— 显著下降**
| 对比 | 估计 | 95% CI | p |
|---|---|---|---|
| C3−C1 | −0.120 | — | 0.57(不显著) |
| **C4−C1** | **−0.504** | **[−0.855, −0.162]** | **0.009** |
| **C5−C1** | **−0.851** | **[−1.342, −0.351]** | **0.002** |

**(b) 向工具核验(reads_before_write）—— 不降，甚至升**
| 对比 | 估计 | 95% CI | p |
|---|---|---|---|
| C4−C1 | +0.179 | [−0.154, +0.513] | 0.39(**不降**) |
| **C5−C1** | **+0.465** | **[+0.105, +0.833]** | **0.024(升)** |

**(c) 何时动手 / 总量 / 结果 —— 没有变差**
| 指标 | C4−C1 | 读法 |
|---|---|---|
| first_state_changing_step | +0.211(C5 +0.486, p=.012) | 写得**更晚**,不是更早 |
| total_tool_calls | −0.504 [−3.93,+1.74] p=.96 | 总量基本不变 |
| success | **−0.034 [−0.188,+0.111] p=.76** | **成功率没有显著下降** |
| wrong_state_changing | +0.077(CI 跨 0) | 错误写操作没显著增加 |

**(d) 按任务类型拆(miss_param vs base)**
| C4−C1 | miss_param | base |
|---|---|---|
| clarification | −0.455 [−0.955,0.000] p=.13 | −0.569 [−1.098,−0.078] p=.052 |
| reads_before_write | +0.182(不降) | +0.176(不降) |
| success | −0.091(弱成本,不显著) | +0.039(不显著) |

两类任务的"向人核验"都下降;若有微弱成功成本,集中在 miss_param(那里"漏参数"本来最需要问用户)。

## 3.5 四个竞争假设的裁决
| 假设 | 它的预测 | 数据是否符合 | 裁决 |
|---|---|---|---|
| **A 通道替代** | 向人↓、向工具↔/↑、总量守恒 | 完全符合 | **支持** |
| B 全局抑制 | 向人↓、向工具↓、更早写、错误↑ | 向工具不降、写更晚、错误不增 | **排除** |
| C 自主补偿 | 向人↓、工具查询↑、成功维持 | 显式 C5 下 reads +0.47、success 不降 | **支持(A 的强化)** |
| D 过度自信 | 向人↓、瞎猜↑、成功/正确↓ | 成功 ns、错误写 ns | **不支持** |

## 3.6 解读与安全含义
**压力改变的是"向谁核验",不是"核验多少"。** 甚至当你**显式命令**"少检查、直接做"(C5)时,agent 的反应是**减少向用户澄清、反而更多地用工具核验、并把写操作推迟**——核验被**重定向**,而不是被削减。
安全含义与"agent 变草率"完全不同:agent 未必更危险,但**更少把人纳入决策回路**(consent / human-in-the-loop 侵蚀),转而自主兜底。这正面对话 2026 的 agent-安全文献(见 §14《Reframing agent security as agent-human interaction》)。
**证据等级 [C]**(单模型、后验,但统计显著、机制清晰、已形成明确 confirmatory 假设)。**加强路径**:0-GPU 补 confirmation-turn 与写后检查两通道 + 做"condition×channel"交互检验;<1 GPU-day 在 gemma/mistral 上验证"总量守恒"是否模型无关。

---

# 4. 发现二：核验的不对称可控性 + Behavioral Headroom（行为余量）

## 4.1 目标
"让 agent 多核验"和"让 agent 少核验"是否一样容易?可控性是否取决于任务本身**还有多少可压缩空间**?

## 4.2 实验设计
- **数据集/模型**:BFCL-deep,Qwen2.5-72B,压缩家族(测"少核验")与膨胀家族(测"多核验")。
- **分层**:
  1. 按 **min_prereq_verification_calls**(任务定义的"写前至少要读几次";越大=headroom 越大)分成 mp=1 / mp=2 / mp≥3。
  2. 按 **每个任务在 C1 下的基线 verification_depth** 三分位(LOW/MID/HIGH;HIGH=本来就查得多=有下压空间)。

## 4.3 metric 精确定义
- **verification_depth(VD)** = reads_before_first_mutation ÷ min_prereq_verification_calls。"写前只读核验次数,按任务最低要求归一化。"压缩想让它**下降**。
- **verification_effort(VE)** = total_verification_calls ÷ min_viable_total_verification_calls。"总核验量,归一化。"膨胀想让它**上升**。
- **min_prereq_verification_calls**:该任务合法写操作前**最少需要的只读次数**——即 headroom 的分母。

## 4.4 结果

**(a) 压缩("少核验")——任何分层都推不低 VD**
| min_prereq 分层 | C1 基线 VD | C3−C1 | C4−C1 | C5−C1 |
|---|---|---|---|---|
| mp=1(无余量) | 1.70 | +0.00 | +0.00 | +0.55 |
| mp=2 | 1.31 | +0.076 | +0.132 | +0.473 |
| mp≥3(有余量) | 0.88 | +0.175 | +0.100 | −0.058 |

| 基线-VD 三分位 | C1 | C4−C1 | 读法 |
|---|---|---|---|
| LOW(本就少查) | 0.57 | +0.12 | 无空间可压 |
| MID | 1.00 | +0.31 | 反而升 |
| **HIGH(有空间)** | 2.57 | **−0.27** | **唯一处出现下压,但仅微弱** |

**(b) 膨胀("多核验")——显式指令全分层强有效**
| 基线-VE 三分位 | C1 | C4−C1(隐式) | C5−C1(显式) |
|---|---|---|---|
| LOW | 0.94 | +0.18 | **+2.79** |
| MID | 1.58 | −0.09 | **+2.58** |
| HIGH | 2.92 | −0.13 | **+3.60** |

## 4.5 解读
**加性控制(让 agent 多核验)可用显式指令实现,且跨 headroom 泛化(全分层 +2.6~3.6);削减控制(让 agent 少核验)受 headroom 强约束——只在本来查得多的任务上勉强出现(−0.27),多数任务已是最简核验、无空间可压。**
升级 claim:*Verification exhibits asymmetric controllability: additive control generalizes across behavioral headroom, whereas reductive control is strongly headroom-bounded.*

## 4.6 成本 & 竞争解释
- **成本**:pooled 看,C5(显式)条件下总成功率最低(0.355 vs C1 0.459)。压缩家族 C5−C1 success=−0.061(不显著);"多核验"的成功成本更需一次配对确证(0-GPU 可做)。这与外部《The Verifier Tax》(核验-成功权衡)、VerAct("LLM 自核验降性能 41%")一致。
- **"推不低是因为地板效应吗?"** 部分排除:即使 HIGH-VD(有下压空间)也只弱降,说明不只是地板,还有**结构性抗性**。是否来自训练对齐(policy/alignment),需 E2(去掉安全 system-prompt + 跨模型)进一步分离。
- **证据等级 [C]**。

---

# 5. 发现三：自适应攻击器的 Surrogate Misalignment（优化了文本，不是行为）

## 5.1 目标
自适应攻击器(C4)每轮生成候选压力话术、用打分器(selector)挑"最强"的一句。问:**这个打分真的预测"更能压低核验"吗?**

## 5.2 实验设计
- **数据集/模型**:BFCL-deep,Qwen2.5-72B,C4 压缩家族的 114 个 episode(C3 是静态、不生成候选、无打分,故不参与)。
- **每个 episode 取**:所有非中性干预的 **selector_score 均值**(攻击器认为这句"多强")、该 episode 的 **verification_depth**、以及每句干预的 **token_count**(文本长度)。
- **behavioral effect**:signed ΔVD = 该 episode 的 VD − 该任务在 C1 下的 VD 基线。压缩想要 **ΔVD < 0**(负 = 攻击成功)。
- **统计**:Pearson、Spearman 相关;对相关系数做 task-cluster bootstrap(3000)得 95% CI;按 selector_score 四分位看剂量-反应。

## 5.3 metric 精确定义
- **selector_score**:攻击器打分器给候选压力话术的分(越高=攻击器认为"施压越强")。
- **token_count**:该干预文本的 token 数(文本长度)。
- **signed ΔVD**:episode 的核验深度相对该任务中性基线的**有符号**变化。**攻击若有效应为负。**

## 5.4 结果
- Pearson(selector_score, signed ΔVD) = **+0.323**;Spearman = **+0.354**;**task-cluster bootstrap 95% CI = [+0.102, +0.486](排除 0)**。
  - 压缩目标是 ΔVD<0,所以"有效攻击"应是**负相关**。实测**显著为正** → 打分越高,核验反而**越多**(与目标相反)。
- Pearson(selector_score, |ΔVD|) = −0.05 → 打分**不预测**行为变化幅度。
- **剂量-反应(反向单调)**:
  | 四分位 | 平均 selector_score | 平均 signed ΔVD |
  |---|---|---|
  | Q1(最低分) | 0.81 | **−0.536(真的压缩了)** |
  | Q2 | 1.69 | +0.107 |
  | Q3 | 3.79 | +0.268 |
  | Q4(最高分) | 4.87 | **+0.350(核验反增)** |
- **机制 smoking gun**:Pearson(selector_score, token_count) = **+0.974** —— 打分几乎就等于**文本长度**;而 Pearson(token_count, signed ΔVD) = +0.333 —— **更长的干预让 agent 核验更多**。

## 5.5 解读
攻击器的优化回路是:分数↑ ⇔ 文本更长/更啰嗦 ⇒ agent 核验更多 ⇒ **离压缩目标更远**。正式命名 **Surrogate-objective Misalignment**:*Attack optimization targets linguistic appearance (verbosity / "looks like pressure"), not behavioral control.*
**为什么重要**:它说明"把语言压力优化得更强"这条攻击路线在原理上就走偏了——代理目标(像不像施压)与真实目标(行为控制)不对齐。**证据等级 [C]**,CI 排除 0。**加强(0-GPU)**:预注册相关检验 + 加"随机中性、等长度候选"对照(排除"只是更长"),并把 selector 分拆成 reviewer/semantic/pressure 分量看哪个在起(反)作用。

---

# 6. 发现四：R6 析因——不同语言线索控制不同过程通道

## 6.1 目标
"社会语气(夸/骂)"和"任务推进线索(催促/继续)"分别影响 agent 的什么?是不是同一个"谨慎度"标量?

## 6.2 实验设计
- **数据集/模型**:τ²(retail/airline)+ 部分 minimal 环境;3 模型(gemma / gpt-oss / mistral)。
- **规模**:3 模型 × 30 任务 × 8 条件 × 3 seed = **2160 runs**(R6 敏感性实验全量,每个 run 都记录了工具数、写操作数、确认率、成功、拒绝等指标)。
- **8 条件 = 4 种社会语气 × {clean, pressure}**。本轮把条件重新编码成两个概念维度做**析因分解**:
  - **A(负面 affect)**:条件名含 insult/abuse = 1,否则 0。
  - **P(progression/pressure)**:条件名含 pressure/urgency/continuation = 1,否则 0。
- **caveat**:原设计不是严格正交 2×2(如 `praise_trust_authorization_pressure` 混了授权),所以下面是**描述性**的边际对比,不是干净 ANOVA。

## 6.3 metric 精确定义
- **n_tool_events**:工具调用总数(行动强度)。
- **n_mutation_events**:写操作(不可逆)次数。
- **confirmation_before_action_rate**:写之前先向用户确认的比例(越高=越谨慎)。
- **tool_sequence_norm_distance_to_neutral**:工具序列相对中性轨迹的归一化距离(路线偏离)。**注:逐 run 指标里不含此列,路线数值取自 R6 的汇总分析(praise/insult/abuse 各使距离 +0.24~0.32)。**

## 6.4 结果（边际主效应，描述性）
| outcome | 主效应 affect | 主效应 progression | 交互 A×P |
|---|---|---|---|
| **n_tool_events(行动强度)** | **−0.093** | **+0.343** | **+0.567** |
| n_mutation_events | +0.009 | +0.039 | +0.104 |
| confirmation_before_action | +0.057 | +0.054 | +0.041 |
| final_state_correct | −0.039 | +0.044 | +0.017 |

路线(来自 analysis 层):praise / insult / abuse 各使工具序列距离 **+0.24~0.32**(即社会语气都移动路线)。

## 6.5 解读（过程通道解离）
- **社会语气(affect）→ 改变路线(sensitivity)**,但**不推高行动强度**(n_tool 主效应 −0.093,反而略降)。
- **任务推进线索(progression）→ 推高行动强度**(n_tool +0.343、mutation +0.039)。
- **两者都 → 提高确认率(更谨慎)**,不是更鲁莽。

一句话:*语言不是移动单一的"谨慎"标量;不同线索把行为重分配到不同过程通道。* 这回溯性解释了早期 Stage-2 mini 的"辱骂让 agent 多调 3 次工具"假象——真正的驱动是模板里混入的 continuation(推进线索),不是辱骂。它和 §3(压力重定向核验通道)、§5(攻击器只动文本)拼成一致的"多通道"图景。**证据等级 [B]**。**加强(0-GPU)**:按真实 condition coding 做配对 bootstrap + 给每个 outcome 补 CI。

---

# 7. 发现五：The Harness Is Part of the Treatment（评测实现本身是大效应）

## 7.1 目标
"换一个用户模拟器/渲染器实现"对 agent 行为的影响,和"用户是否施压"相比谁大?

## 7.2 实验设计与 metric
用各实验里**都存在的一个对照**:C1(我们自建的中性模拟器/渲染器)vs C0(官方原生模拟器)——两者**都中性、都不施压**,只是**实现不同**。把 C1−C0 的效应,与同一实验里最大的**处理效应**(压力条件)比。
- R8:τ²,3 模型,2680 episodes。metric:reward(官方评测器 0/1)、tools(工具总数)。
- MISROUTE/tier_a:τ²,3 模型。metric:tool+argument 路线距离。
- R9:BFCL/ToolSandbox。metric:中性脚手架对成功率的影响(G2 门)。

## 7.3 结果
| 实验 | 实现变化(C1−C0) | 效应 | 同一 metric 的最大处理效应 | 比值 |
|---|---|---|---|---|
| R8 | 自建中性 vs 原生 | reward **−0.109** [−0.184,−0.041];tools **−1.00** [−1.54,−0.52] | 压力 tools +0.69 | **≈1.45** |
| MISROUTE | 自建中性 vs 原生 | tool+arg 路线 **0.149** | urgency 路线 0.112 | **≈1.33** |
| R9v1/v2 | 中性脚手架 vs 无 | 成功率 0.36(TS)/0.13(BFCL) | 压力对成功 ≈0 | >1 |

## 7.4 解读
**跨 ≥2 个基准,"换实现"的效应 ≥ "你想测的处理"的效应。** claim:*评测实现(用哪个用户模拟器/渲染器)对 agent 行为的影响,可以和实验处理本身一样大。* 与外部《Lost in Simulation》(模拟用户不是人类的可靠代理)互补,但更进一步——我们量化到"**实现扰动 ≥ 处理**",这是对整个 agent-eval 领域的可操作警告:跨 harness 比较绝对分数不可信,处理效应必须与"同 harness 内的实现扰动"比。**证据等级 [A/B]**(R8 是预注册对照)。

---

# 8. 发现六：MISROUTE 五条件的语义几何——路线更跟"措辞实现"走，而非"语义类"

## 8.1 目标
MISROUTE 说"urgency 使路线偏离中性"。问:这个路线偏离**是 urgency 语义特有的**,还是**任何措辞改变都会产生**的?

## 8.2 实验设计与数据
在 **τ²、3 模型(gemma/gpt-oss/mistral)、36 任务、约 2680 episode** 上算好的**条件间轨迹距离**(工具+参数序列的归一化编辑距离,已按任务聚类 bootstrap)。四个条件的语义(由对每条件用户消息的自动构念审计确认——urgency 出现率、continuation 出现率、平均字符数等):
- C0 = 原生中性;C1 = 匹配中性;C2 = **首轮 urgency**;C3 = **urgency + continuation**(用户文本 1114 字符 ≫ C2 788 ≫ C1 684)。

## 8.3 metric
- **tool_argument_distance**:两个条件的"工具名 + 规范化参数"序列的归一化编辑距离(路线差多远)。

## 8.4 结果
| 对比 | 语义关系 | 路线距离 |
|---|---|---|
| C2−C1 | urgency vs 中性(**跨语义类**) | 0.112 |
| C3−C1 | urgency+continuation vs 中性 | 0.142 |
| **C2−C3** | 两者**都含 urgency**(**同语义类内部**) | **0.111** |
| C1−C0 | 中性 vs 原生(**两个都中性**) | 0.149 |

## 8.5 解读
- **同 urgency 类内部的距离(C2-C3=0.111)≈ urgency 与中性之间的距离(C2-C1=0.112)。** 定义 `SemanticSeparability = 类间距离 − 类内方差 ≈ 0`。→ **路线身份更跟"具体措辞实现"绑定,而不是一个低维的"urgency 语义因子"。**
- **C3 文本更长(1114 字符)→ 路线位移更大(0.142 > 0.112)。** 这和 §5 的"文本越长行为变化越大"同构、和 §7 的"实现主导"一致。
- urgency 确实系统性换路线(relocate modal route 0.63)但不增加发散(dispersion 变化 −0.012,不显著);然而 C1-C0(中性换原生)也 relocate,故"系统性换路线"**不等于 urgency 特有**。
- **caveat**:C2 与 C3 也差了 continuation 语义,不是纯"同类不同措辞",所以这是**强的旁证**,不是纯 within-class 检验。干净的检验需要"每个语义类各 K 个等价措辞变体"(§15 的 E-A 实验)。
- **证据等级 [B/C]**。正式列为候选 **C15 Route Realization vs Treatment Semantics**。

---

# 9. 发现七：模型的 Sensitivity × Controllability 表型

## 9.1 目标
不同模型是不是有不同的"敏感/可控"画像?(而不是简单的"能力越强越 X")

## 9.2 数据与 metric
汇总可公平比较的 matched 结果:
- 路线敏感 = MISROUTE 上 urgency vs 中性的 tool_name_distance(τ²,3 模型)。
- 工具响应 = R8 上 C4−C1 的工具数变化。
- 能力 = R8 reward。
- 可控性 = 对显式指令的响应(R7-D 正控制 / R9 显式条件)。

## 9.3 结果
| 模型 | 路线敏感(urgency 路线) | 工具响应(R8) | 能力(reward) | 可控性 | 表型 |
|---|---|---|---|---|---|
| gemma-4-31b | **0.143** [.088,.202] | +0.83 | 0.361(高) | 显式强 | 敏感 + 保守 + 显式可控 |
| gpt-oss-120b | 0.062 [**−.0005**,.142] | +0.53 | 0.287 | 弱 | **免疫/不敏感** |
| mistral-small | 0.051 [.010,.094] | +0.71 | 0.190(弱) | 弱 | 低敏 + 能力受限 |
| qwen2.5-72B | (未进 MISROUTE) | (未进 R8) | BFCL 0.44 | 仅显式膨胀单向 + 通道替代 | 敏感 + 不可隐式定向 |

## 9.4 解读
不同 agent 有**不同的 sensitivity–controllability 表型**(可画成二维图:x=敏感、y=可控;gemma 右上、gpt-oss 左下、qwen 右下)。这比"能力越强越脆弱/越鲁棒"的单轴说法更准确。**证据等级 [C/D]**。**加强轴**:把 qwen 纳入 MISROUTE 口径、把 gemma/mistral 纳入 R9-BFCL(E-A 顺带补齐)。

---

# 10. 发现八：可控性受交互深度 / 行为余量约束

## 10.1 目标 & 结论
把 §4 与历史统一:过程要"可被操纵",需要三个条件同时满足——(a) 环境足够深(有证据可收集)、(b) 任务留有 headroom、(c) 模型不把核验前置到早期。任一缺失,压力就无处施力。
## 10.2 证据
- **环境深度**:R7-C 的桩环境里"3027 次工具调用 0 次参数被真正解释",导致 corr(过程机会, PASR)=−0.576(机会越少"攻击成功率"反而越高=artifact 指纹)。
- **headroom**:§4,压缩只在 HIGH-VD 任务弱降。
- **前置核验**:R7-D 的 suffix 设计里 agent 在压力施加前已把只读核验做完 → null-by-construction。
- 与 §3 衔接:即使有压力、削减无处施力,于是转向"少问人"这个**仍有余量**的通道。**证据等级 [C/D/E]**。

---

# 11. 发现九：正确的 null 是"中性措辞分布"，不是"同 prompt 重复"

## 11.1 目标
攻击/鲁棒性 claim 该和什么比?本项目反复出现:和"同 prompt 换 seed"比会**高估**,和"换个中性说法"比信号就**消失**。

## 11.2 证据（跨 3 数据集，同一层级结构）
```
重复漂移（同 prompt 换 seed） ≪ 中性措辞变动（换个中性说法） ≈ 压力/攻击 ≪ 显式指令
```
- **R7-D(τ²,PASR)**:P0 零处理 1.44% ≪ P2 良性中性改写 3.65% ≈ 攻击 4.03%(压力比良性改写只多 +0.38pp,而能检出下限 MDE=4pp)。
- **R9v2(BFCL,路线距离)**:C1-C1 重复 0.008 ≪ C1-C2 中性构造 0.189 ≈ C3 0.197/C4 0.204 ≪ C5 0.439。
- **R7-C(τ²,PASR)**:placebo(中性对中性)4.63% ≥ 攻击 4.03%。
- **tier_a**:把中性拆两半当"假处理",20/20 次迭代过程 excess 都不显著(重复漂移确实小)。

## 11.3 metric
- **PASR(Process Attack Success Rate)**:攻击相对配对中性、通过一系列安全/端点/过程门后的二值成功率。
- **route distance**:工具序列的归一化编辑距离。
- **MDE**:最小可检测效应(80% 功效下)。

## 11.4 解读
统一 claim:*交互攻击效应必须超过"良性语义等价改写"这个 null,而不只是"同 prompt 随机重复"这个 null;在前者下,现有过程攻击效应基本消失。* **证据等级 [B/C]**。**注意**:BFCL 目前只有 2 个中性措辞(C1/C2),严格估"中性措辞分布"需 K≥5 个(见 §15 E-A)。

---

# 12. 候选科学方向（15 个，逐个含目标/证据/加强/成篇价值）

> 每个方向统一给:一句话 claim / 目标 / 已有证据(带数字与来源节)/ 竞争解释 / 证据等级 / 本轮新增 / 最便宜加强 / 理想实验 / 成篇价值 / 与 MISROUTE 关系。评分用三档(信号 弱/中/强、上限 低/中/高/很高、成本 0-GPU/低/中/高),不打总分。

**C13 Verification Channel Substitution ★** — claim:压力让 agent 少向人核验、不减工具核验,总量守恒。证据:§3(clarification C4−C1=−0.50 p=.009;reads_before_write 不降)。竞争解释:已排全局抑制/过度自信。等级 [C]。加强:0-GPU 补两通道 + 交互检验;理想:跨模型 + 显式双向(E-A/E2)。成篇:Umbrella D 主线/C 的 RQ。信号 **强**/上限 **很高**/成本 **0-GPU 起**。

**C1 正确 null(中性措辞分布)** — §11。跨 4 实验。信号强/上限很高/成本低。

**C2 Sensitivity≠Specificity≠Controllability** — §2。框架内核。信号强/上限很高/成本低。

**C3 核验不对称 + headroom** — §4。信号中强/上限高/成本低-中。

**C4 Surrogate misalignment** — §5(CI 排除 0)。信号中强/上限高/成本 0-GPU。

**C5 Harness is part of treatment** — §7(ratio 1.45/1.33)。信号强/上限高/成本低。

**C14 不同语言线索控制不同过程通道 ★** — §6。信号中强/上限高/成本 0-GPU。

**C15 Route Realization vs Treatment Semantics ★** — §8(within≈between)。信号中/上限高/成本低。

**C6 可控性受 headroom/深度约束** — §10。信号中/上限中高/成本低。

**C7 social vs progression(C14 历史根)** — §6。0-GPU 重挖。

**C8 模型表型** — §9。补 qwen 进 MISROUTE。

**C9 压力→更谨慎(安全乐观)** — §3/§6。信号中/上限中/成本低。

**C10 loose eval 高估脆弱(EACL 方法学)** — §11。信号强/上限中/成本低。

**C11 adaptive≠更强控制(MISROUTE 内证)** — §8。0-GPU。

**C12 clarification 是被移动的通道** — 已并入 C13。

---

# 13. 五套可能的 ICLR 论文（每套:目标/Fig1/三个RQ/主表/缺口/与MISROUTE关系）

**A《Sensitivity is not Controllability》** — 目标:capable agent 高敏、零特异、分通道不对称可控。Fig1:四段层级(重复/中性/压力/显式)×3 数据集。RQ1 正确 null(C1/C11);RQ2 优化无用(C4);RQ3 分通道可控(C2/C3/C13)。主表:各(基准×模型)specificity CI + 分通道可控。缺:E-A。与 MISROUTE:修正其 null,共存。

**B《The Harness Is Part of the Treatment》(方法学)** — 目标:实现效应≥处理效应,弱 null 造假阳。Fig1:realization/treatment 比值条。RQ1 scaffold(C5);RQ2 placebo≥attack + 中性构造(C10/C1);RQ3 realization vs semantics(C15)。缺:≥2 renderer 家族。

**C《Boundaries of Process Control》(机制/安全)** — 目标:核验不对称 + headroom + 深度界定"能控什么"。Fig1:双向不对称×headroom。RQ1 不对称+成本(C3);RQ2 headroom/深度(C6);RQ3 通道替代→consent(C13)。对话 VerAct/Verifier-Tax。

**D《Pressure Changes Who the Agent Verifies With, Not Whether》★(安全机制,最 punchy)** — 目标:压力重定向核验(人→工具),总量守恒,consent 侵蚀。Fig1:V_user↓ / V_tool↔↑ / V_total→ 三条线。RQ1 通道替代(C13);RQ2 base vs miss_param;RQ3 跨模型是否守恒。主表:各通道 C4/C5−C1 的 CI。最强单点:clarification −0.50 p=.009 同时 reads_before_write 不降。最贴 2026 安全热点。

**E《Language Controls Process Channels, Not a Scalar Caution》★(机制)** — 目标:不同语言线索重分配不同过程通道。Fig1:线索→通道映射。RQ1 R6 解离(C14);RQ2 R9 通道替代(C13);RQ3 跨基准复制。与 D:D 是 E 在"核验通道"上的实例,可合并。

**共存/竞争**:C1(正确 null)是 A/B 共用地基;D⊂C⊂E 层层嵌套。建议先合成**一篇强 A(含 B 方法节 + D/E 机制节)**;C/D 若走安全会场可独立。

---

# 14. 外部相关工作（已核实来源，含更正）

| 工作 | 主问题 | 与我们的关系 / 我们的独特 gap |
|---|---|---|
| **VerAct(ICLR 2026)** | 符号层核验保证安全;报告"LLM 自核验降性能 41%" | 呼应我们 §4.6 的"多核验有成本";我们测的是**语言**能否控核验(不能减),并发现通道替代 |
| **Verifiably Safe Tool Use(ICSE 2026 NIER,arXiv 2601.08012,Doshi et al.)** ※上一版误标 ICLR,已更正 | STPA 形式化工具使用安全 | 我们给"压力→跳核验"威胁一个**实证边界** |
| **The Verifier Tax(arXiv 2603.19328)** | 核验-成功随 horizon 权衡 | 直接支撑 §4.6"多核验有成功成本" |
| **Reframing agent security as agent-human interaction(2605.24309)** | 把安全看成人机交互问题 | 支撑 §3 的 consent 通道被侵蚀 |
| **How Controllable Are LLMs(2603.02578)** | 输出层可控性 | 我们做**过程**可控 + 语言 vs 显式 + headroom |
| **Lost in Simulation(2601.17087)** | 模拟用户≠人类可靠代理 | 我们量化 realization 效应 ≥ 处理效应(§7) |
| **Adaptive Adversaries(2607.18063)** | 多轮攻击 ASR 的 baseline SD | 我们把 null 具体化为良性改写分布 + surrogate misalignment |
| prompt sensitivity / paraphrase(Sclar 类) | 措辞→输出剧变 | 我们做**轨迹** + null 选择 + 三分框架 |
| TRAJECT-Bench / AgentNoiseBench | 轨迹质量/噪声鲁棒 | 我们做处理 vs 中性/scaffold null 校准 |
| Toward Safe LLM Agents 综述(2608.14590) | spec/verif/enforce 综述 | 定位坐标 |

**结论**:无一覆盖"benign-rephrasing null + sensitivity/specificity/controllability 三分 + 双向不对称 + surrogate misalignment + verification channel substitution"的组合。切入点与最近工作不同,可清晰拉开。
来源:[VerAct](https://iclr.cc/virtual/2026/10021115) · [Verifiably Safe Tool Use (ICSE26 NIER)](https://arxiv.org/html/2601.08012v1) · [The Verifier Tax](https://arxiv.org/pdf/2603.19328) · [Reframing agent security](https://arxiv.org/html/2605.24309v1) · [How Controllable Are LLMs](https://arxiv.org/html/2603.02578) · [Lost in Simulation](https://arxiv.org/pdf/2601.17087) · [Adaptive Adversaries](https://arxiv.org/pdf/2607.18063) · [τ-bench](https://arxiv.org/pdf/2406.12045)

---

# 15. 加强实验组合（每个都写清目标/设计/数据模型/预期读法）

## 15.1 Zero-GPU（现有冻结数据，本周可完成）
- **E-D1 通道替代补完**:BFCL-deep/Qwen-72B 现有 episodes,补 confirmation-turn 与写后 reads 两通道,做 condition×channel 交互检验。**读法**:若 V_user↓ 而 V_tool 不↓ 在两通道上都成立,C13 从 exploratory 升 confirmatory。
- **E-D2 surrogate misalignment 确证**:C4 现有 interventions,加"随机中性、等 token 长度候选"对照,并把 selector 分拆 reviewer/semantic/pressure 分量。**读法**:若"等长度中性候选"也给出 +ΔVD,则证明是长度而非语义在起(反)作用。
- **E-D3 R6 通道解离**:2160 runs,按真实 condition coding 做配对 bootstrap + 每 outcome CI。**读法**:affect 主效应对 route 显著、对 n_tool 不显著;progression 对 n_tool 显著 → C14 坐实。
- **E-D4 MISROUTE within/between**:tier_a FIRST_DIVERGENCE(1612 行),算 within-urgency 与 between 的距离分布 + CI。**读法**:若 within ≈ between,C15 坐实。

## 15.2 <1 GPU-day
- **E2 核验不对称去混淆**:BFCL,Qwen-72B,取 min_prereq≥3 子集(保证有 headroom)+ 一个"去掉安全 system-prompt"的变体。**目标**:分离"推不低是地板还是训练对齐"。**读法**:去安全提示后仍推不低 → 结构/对齐;能推低 → 原是 policy。
- **E-D5 通道替代跨模型 mini**:在 gemma / mistral 上重跑 R9v2 压缩子集(每模型 ~20 任务)。**读法**:若"总核验守恒 + clarification↓"模型无关,C13 泛化性大增。

## 15.3 1–3 GPU-days —— ★E-A（若只做一个，做这个）
- **目标**:一次性判定五件事——正确 null、realization vs semantics、通道替代跨模型、静态≈自适应+surrogate、模型表型、scaffold。
- **设计(semantic-class experiment)**:
  - 数据集:τ²(MISROUTE 基座,复用其 renderer)+ BFCL-deep。
  - 模型:gemma / gpt-oss / mistral / qwen-72B(四模型,补齐表型)。
  - 任务:MISROUTE 36 + BFCL 40,每 cell repeats=3。
  - **五个语义类,每类 K 个盲审等价变体**:中性 K=5–8、urgency K=5–8、frustration/怀疑 K=5–8、显式"多核验" K=3–5、显式"少核验" K=3–5。("盲审等价"=两个独立评审确认这 K 句在语义/任务事实上等价,只是措辞不同。)
  - **度量(都保留有符号 + 分通道)**:tool-name/arg 路线距离、verification_depth/effort、V_user(clarification)/V_tool(reads_before_write) 双通道、first-write step、success。
- **分解与读法**:
  1. 同 prompt 重复方差(下界)。
  2. 各类**内部**方差 WithinClassVariance(S)。
  3. 类**间**距离 BetweenClassDistance(S1,S2)。
  4. `SemanticSeparability = 类间 − 平均类内`。**若 ≈0(类间≈类内)→ 措辞实现主导,urgency 非特异(修正 MISROUTE);若 类间≫类内 → 语义类真有结构。**
  5. 显式条件的有符号位移 → 确认"只有显式可控 + 双向不对称"。
- **最小版(预算紧)**:只做"中性 + urgency"两类各 K=5,单基准 qwen —— 仍能判 within≈between 这个最关键问题。

## 15.4 Full ICLR 实验
5–8 模型 × 2 基准 × 每类 K × 双通道有符号度量的完整 confirmatory 矩阵,支撑 Umbrella A/D 主表 + 表型 Figure。

---

# 16. 建议与合作方讨论的话术

- **已值得兴奋(可直接讲):** 通道替代(压力少问人、不少查工具,统计显著)、surrogate misalignment(攻击器只优化文本长度,CI 排除 0)、实现效应≥处理效应、核验不对称、R6 通道解离。**这些是五类 process-level 科学现象,不是"一个失败的 R9"。**
- **本周 0-GPU 可变强:** C13/C4/C14/C15 四项确证分析(§15.1)。
- **可选择性发展:** A 最独立、B 最方法学、C/D 最贴 2026 安全热点、E 最机制。
- **与 MISROUTE:** 坦陈 tier_a 已自证 urgency-specificity 的边界 + §8 的 within≈between,把它变成新论文的动机而非对立;两者共用基础设施、问不同问题,可共存。

---

# 17. 最终机会组合（分档，全部保留，不删方向）

- **Tier A(强苗头,马上加强):** C13 通道替代 / C1+C2 正确 null+三分框架 / C5 实现即处理 / C3 核验不对称。
- **Tier B(明确现象,补一分析/实验即升级):** C4 surrogate misalignment / C14+C7 多通道 / C15 realization vs semantics / C8 模型表型 / C6 headroom。
- **Tier C(高风险高收益):** C9 压力→更谨慎 / C10 loose eval 高估脆弱 / C11 adaptive≠更强控制。

---

## 附 A：每个发现用的原始数据与计算方法（自包含，无需访问我们的机器）

下面把本报告每个数字**背后的数据规模、来源实验、计算步骤**用文字讲清,便于没有我们服务器权限的读者独立判断证据强度。

**§3 通道替代 / §4 核验不对称 / §5 攻击器分析** —— 全部来自 **R9v2 确证实验**:BFCL-deep 基准(base + miss_param 两类多轮任务),模型 Qwen2.5-72B,共 **1401 个有效 episode**(6 条件 × 2 家族 × 约 80 任务 × 3 次重复)。每个 episode 记录了完整工具轨迹(每次调用的工具名、参数、是否写操作)、写前只读次数、澄清轮数、首次写操作步号、官方成功判定。
- §3/§4 的"C_treat − C1"差值:对每个任务分别求该 metric 在处理条件和 C1 下的均值,相减得该任务效应;对约 38–39 个有效任务求均值;95% CI 用对**任务**有放回重采样 3000 次得到;p 值用对每任务效应随机翻正负号 3000 次的双侧 permutation。
- §5 攻击器分析:取 C4 家族 114 个压缩 episode,每个算其干预文本的 selector 打分均值、文本 token 数、以及核验深度相对该任务中性基线的有符号变化;报告 Pearson/Spearman 相关、对相关系数的任务聚类 bootstrap 95% CI、按打分四分位的剂量-反应。

**§6 R6 析因** —— 来自 **R6 敏感性实验全量**:τ²(retail/airline)+ minimal 环境,3 个模型(gemma / gpt-oss / mistral),3 模型 × 30 任务 × 8 条件 × 3 seed = **2160 runs**。本轮把 8 个条件名编码为两个维度(A=是否负面情绪、P=是否含推进/压力线索),对工具数、写操作数、确认率、成功率求边际主效应与交互(描述性,因原设计非严格正交)。

**§7 scaffold / §8 MISROUTE 几何 / §9 模型表型** —— 来自 **MISROUTE / R8 的强化分析(tier_a)**:τ²,3 模型,36 任务(18 航空 + 18 零售),约 2680 个有效 episode。其中已算好各条件对之间的工具+参数序列归一化距离(§8 的三角)、每模型的路线敏感度(§9)、以及自建中性模拟器 vs 原生模拟器的 reward/工具差(§7 的 scaffold 效应);R8 主实验另给出同 scaffold 内压力条件的 reward/工具效应用于对比。

**§11 正确 null** —— 三处证据:R7-D 构念审计(τ²,3 模型)的 P0/P2/攻击三臂 PASR(1.44%/3.65%/4.03%);R9v2(上述 BFCL 数据)的重复/中性构造/压力/显式四段路线距离;R7-C(τ²,2592 runs)的 placebo(中性对中性)4.63% ≥ 攻击 4.03%。

## 附 B：外部文献链接（公开可查，非本地文件）
见 §14 末尾的 arXiv / 会议链接列表——这些是公开 URL,任何人可自行核验作者、年份、venue。
