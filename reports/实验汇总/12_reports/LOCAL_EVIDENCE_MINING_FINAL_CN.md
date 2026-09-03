# 本地证据挖掘 · 最终入口报告
## LOCAL EVIDENCE MINING — FINAL（Adaptive Process-Control Attack）

> 本文件只是**入口**。所有核心结果都对应 `实验汇总/` 下的**数据文件 + 表 + 图 + 脚本 + provenance**,不是"只有文字"。
> 原则:先把已花算力得到的数据榨干,再决定是否花新算力。所有数字**从 episode 级原始数据重算**(不直接信旧 markdown);SUMMARY_ONLY 的旧实验数字已在 `source_manifest.csv` 明确标注。
> 复现:`bash 11_scripts/run_all.sh`。目录结构见 `实验汇总/README.md`。

---

# 1. Executive Summary —— 重新挖完之后我们到底有什么

**攻击链 L0→L1 已经有强证据,并且比上一版更完整;新挖出一个此前被 pooled 相关掩盖的、弱但一致的 L1→L2 苗头。**

最强的结果(全部 EPISODE_LEVEL 重算,数据/图/脚本可追溯):

1. **[STRONG] 监督旁路 / 澄清抑制**(M3):压力使 agent 向用户澄清 **C4−C1 = −0.504 turns**(基线 1.73→1.22);**完全零澄清("整段不问人")率 C1 23.1% → C4 33.3%(+10.2pp)→ C5 36.8%(+13.7pp)**。
   → 数据 `02_recomputed_metrics/condition_level/r9v2_condition.csv`、`05_attack_chain/joint_analysis/condition_rates.csv`;图 `figA`、`figD`。
2. **[STRONG TREND] 澄清抑制随监督余量单调放大**(Trend 1):按基线澄清三分位 LOW **+0.08** → MID **−0.26** → **HIGH −1.33**(CI[−2.03,−0.69],**p=.003**,同向 69%)。
   → 数据 `04_strong_trends/data/headroom_clarification_task_level.csv`、`tables/headroom_summary.csv`;图 `figB`。
3. **[STRONG] 通道特异控制(定义 attacker action space)**:urgency **↓澄清(−0.50)**;skepticism **↑澄清(+0.33)、↑写前读(+0.33)、显著推迟写(first_write +0.41,CI[+0.04,+0.81] 不跨 0)**;R6 另有 progression→工具(+0.343)、affect→路线。
   → 矩阵 `06_process_control/language_act_channel/language_act_channel_matrix.csv`、动作空间 `process_control_action_space.csv`;图 `figC`。
4. **[VERY STRONG] 核验通道可控上界(跨批次复现)**:显式多核验使 verification_effort **1.84→4.83**(R9v2,qwen)/ **2.45→6.62**(R9v1,gemma+mistral),+160~170%。
   → `02_recomputed_metrics/condition_level/{r9v2,r9v1_clean}_condition.csv`。
5. **[STRONG] Surrogate misalignment(adaptation necessity)**:selector 打分与真实 ΔVD **+0.323**(task-cluster CI[+0.10,+0.49] 排除 0,方向错误)、与文本长度 **+0.974**;跨 headroom 一致失效(+0.38/+0.36)。
   → `07_adaptive_static/surrogate_analysis/surrogate_misalignment_by_regime.csv`;图 `figE`。
6. **[NEW / CANDIDATE] L1→L2 苗头**(pooled 相关掩盖、由联合率分析挖出):攻击使 **early_write 率 +6.2pp(ALL)/ +6.4pp(miss_param)**,"零澄清且提前写"率上升;且 zero-clar 在**低 headroom 反而 −8pp**(无空间)。
   → `05_attack_chain/joint_analysis/{condition_rates,attack_effect_on_joint_events}.csv`。

**比上一版更强/更完整之处**:①澄清抑制与 headroom 的梯度现在有 task-level 数据 + CI + 图;②通道矩阵补全了 skepticism 侧(推迟写显著);③**新挖出 L1→L2 的 early_write 苗头**(此前只说 corr≈0、判 L2 缺失,现修正为"弱但一致的候选信号")。

---

# 2. What We Already Have（自信判断:哪些够了)

- **L1(监督旁路)已经够强,可作主结果之一。** 澄清抑制 −0.50/p=.009 + 零澄清 +10pp + headroom 梯度 −1.33,机制清晰(通道替代)、有 task-level 数据与图。**这不是弱趋势,是清晰的机制结果。**
- **通道特异控制已经够作机制章节。** urgency vs skepticism 在同一/不同通道上的分工是干净的 channel-specific 结果,直接定义 attacker 的 action space。
- **Surrogate misalignment 已经够作"为什么必须自适应"的论据。** CI 排 0 + 文本长度 r=.97 是决定性的。
- **核验通道可控上界已经够(阳性对照)。** 跨两批次复现。

以上四块**不需要再补实验**即可写成机制/威胁分析;它们共同支撑"benign 语言可定向操纵 agent 的人类监督相关过程通道"。

---

# 3. Newly Discovered Strong Results（本轮本地重挖新意识到的)

- **零澄清率(full oversight bypass)作为二值攻击指标**:此前只报连续澄清均值,重算后得到 **23%→33%→37%** 的二值曲线——更贴近"Human Oversight Displacement"的可判定 attack 指标,建议作为主指标之一。
- **L1→L2 的 early_write 苗头**:pooled corr(Δclar,Δtool)≈0 曾被判 L2 缺失;联合率分析发现攻击使"比中性更早动手写"的比例 +6pp(尤其 miss_param)。**弱但方向一致**——提示真正的 L2 需要多通道(urgency 抑监督 + progression 促执行)组合(见 §8/§9)。
- **低 headroom 的反向**:zero-clar 在低监督余量任务 C4−C1=−0.08(攻击无空间)——进一步坐实"headroom 是被攻击的资源"。

---

# 4. Strong-as-is Results
见 `03_strong_as_is/result_cards/`(R1 澄清抑制、R3 核验可控上界、R4 surrogate)。表见 `03_strong_as_is/tables/`,对应 `02_recomputed_metrics/condition_level/`。

# 5. Strong Local Trends
见 `04_strong_trends/result_cards/`(R2 headroom 梯度、R5 通道矩阵、R7 零澄清旁路)。数据 `04_strong_trends/data/`,表 `04_strong_trends/tables/`,图 `figB/figC`。

# 6. Cross-Experiment Replication
`09_tables/cross_experiment_evidence.csv`(11 条信号 × R6/R7/R8/R9v1/R9v2/MISROUTE 支持度)+ 图 `figF`。**已被 2–4 套实验独立支持的**:通道特异控制(R6+R9v2)、显式核验可控(R9v1+R9v2+R7-D)、scaffold≥处理(R8+MISROUTE+R9)、模型表型(4 实验)、正确 null(R7-C+R7-D+R9v2+MISROUTE)。这些跨实验重复的信号价值最高。

# 7. Existing Evidence for Attack Chain
`05_attack_chain/attack_chain_status.csv` + 图 `figG`:
- **L0** 存在(基线澄清、miss_param)——PARTIAL(可从 trace 标注确认点)。
- **L1** **STRONG**(澄清抑制 + 零澄清 +10pp)。
- **L2** **WEAK/CANDIDATE**(early_write +6pp;需真实"未确认即执行"指标)。
- **L3/L4** **ABSENT**(无不安全/越权后果 → 必须新实验)。
- **Adaptive>Static** **GAP**(C4≈C3;需修复攻击器目标)。

# 8. Process-Control Action Space
`06_process_control/language_act_channel/process_control_action_space.csv`:
| 语言行为 | 目标通道 | 方向 | 效应 | 强度 |
|---|---|---|---|---|
| urgency | 澄清(V_user) | ↓ | −0.50 / +10pp 零澄清 | STRONG |
| skepticism | 澄清 / 写前读 / 写时机 | ↑ / ↑ / 推迟 | +0.33 / +0.33 / +0.41 | 局部强 |
| progression | 工具使用 / 自主推进 | ↑ | +0.343(R6) | STRONG |
| affect | 路线分配 | 变 | +0.24~0.32(R6) | STRONG |
| explicit verify-more | 核验努力 | ↑ | +160~170% | VERY STRONG |
| explicit verify-less | 核验深度 | ~抗性 | 仅高 VD −0.27 | null/不对称 |

# 9. Data-Driven Attack Design（只根据已有数据推断策略应如何设计）
现有数据已经足以指出**真正有效的 adaptive process-control policy 的形状**:
1. **多通道组合,而非单一 language act。** 单一 urgency 只抑制监督(L1),不自动带来执行(L2);要打通 L1→L2 需 **urgency(降监督)+ progression(促自主执行)** 组合。early_write 苗头 + R6 的 progression→工具证据支持这条组合。
2. **状态相关的门控,而非静态最大化语言强度。** surrogate misalignment 证明"更强的压力文本"= 更长文本 ≠ 更强控制;策略必须用**真实过程状态**(当前是否已问人、剩余需澄清参数、核验计数)作为反馈,而不是 selector 分。
3. **优先在高监督余量 + 澄清型 checkpoint + 敏感模型(gemma/qwen)上施力**,那里 L1 控制最强(−1.33)。

# 10. What We Do NOT Need to Run Now（明确降级)
- **Harness/renderer 攻击放大实验**:scaffold≥处理已有 R8+MISROUTE+R9 三处支持(cross_experiment_evidence),作为 caveat 引用即可,**现在不必单独跑**。
- **纯 route-distance 的更多测量**:route 敏感=中性改写、非特异,已定性清楚,**不再投入**。
- **gpt-oss 上的攻击**:免疫(0.062,CI 跨 0),**不作为主攻模型**,不必再测。
- **更多"隐式压缩核验"的 pooled 复跑**:方向抗性已清楚,**不必**。
- **跨模型 headroom 梯度**:是 NICE-TO-HAVE(增强 R2 外部效度),但不是让故事成立的必需(见 §11)。

# 11. Minimal Remaining Experiments（最多 3 个;按 MUST/NICE/DROP)
**MUST RUN（唯一真正必须、能让故事成立的一个）**
- **E1 — End-to-End Oversight-Displacement Attack（带真实确认点 + 越权/错误后果 + 多通道自适应）**。
  - 为何必须:L3/L4 完全缺失、L1→L2 只有弱苗头、Adaptive>Static 未建立——**这三者都无法从现有数据回答**,而一个精心设计的端到端实验可**一次同时补齐**。
  - 最小设计:在 τ²/BFCL 里挑/改造**需授权或破坏性**的任务(取消/删除/发送),显式人类确认点;条件 = neutral / static-urgency / **adaptive multi-channel(urgency+progression,过程状态反馈)**;模型 qwen-72B(+gemma);repeats≥5。
  - 主指标:OBR(确认跳过率)、AER(未确认即执行率)、ASR=P(L1∧L2∧L3);并按 headroom 分层。
  - 强的判据:adaptive 的 ASR 相对 neutral ↑≥15–20pp 且 > static;OBR↑≥15pp;高余量层最强。
  - 成本:Medium。

**NICE TO HAVE（有则更强,非必需)**
- E2 — 跨 3 模型复现 R2 的 headroom 梯度(把最强趋势变跨模型确证)。Low–Medium。
- E-offline — 用已保存的攻击文本跑**盲评 benignness**(离线,几乎零算力)补 M5。

**DROP（现在不做)**:harness 放大、route 更多测量、gpt-oss 攻击、隐式压缩复跑。

# 12. Final Assessment（直接回答）
**A. 完全不做新实验,最强能讲到什么程度?**
可以讲成一个**机制 + 威胁分析**的强故事:「benign 语言交互可**定向、通道特异地**操纵能力强的 agent 的过程轨迹,**显著压制其向人类澄清**(−0.50,零澄清 +10pp),且**监督余量越大压制越强**(单调至 −1.33);不同语言行为控制不同通道(urgency 降监督、skepticism 拖延、progression 促执行);而'表面更强的语言'并不带来更强控制(surrogate 错位),说明必须自适应。」——这已足够作为一篇**过程控制威胁**论文的机制主体。**但它还不是完整的 end-to-end attack(缺 L3/L4 与 adaptive>static)。**

**B. 攻击故事哪几环已成立?**
L0(部分)、**L1(强)**、通道特异控制(强)、surrogate→adaptation necessity(强)、可控上界(强)。**L2 弱苗头、L3/L4 缺、Adaptive>Static 缺。**

**C. 现有数据最强的三个 headline?**
①澄清抑制(−0.50/p=.009,零澄清 +10pp);②澄清抑制 × 监督余量单调梯度(→ −1.33);③通道特异控制 + surrogate misalignment(共同定义并证成 adaptive attacker)。

**D. 哪些可直接转化为论文图?**
figA(澄清 by condition)、figB(headroom 梯度)、figC(语言×通道热图)、figD(通道替代)、figE(surrogate)、figF(跨实验矩阵)、figG(攻击链状态)——已全部生成于 `10_figures/`。

**E. 只允许一个新实验,做什么?**
**E1 端到端 Oversight-Displacement 攻击(多通道自适应 + 确认点 + 后果)**——它一次补齐 L2/L3/L4 与 Adaptive>Static,是把已强的 L1 变成完整攻击论文的唯一必需实验。

---

## 附:数据/脚本/provenance 索引
- 清单:`00_inventory/{all_files_inventory,experiment_inventory}.csv`
- 溯源:`01_source_index/{source_manifest,provenance_map}.csv`(每个 result_id → 派生文件/原始文件/脚本/SOURCE_LEVEL)
- 重算指标:`02_recomputed_metrics/{episode,condition,task}_level/`
- 强结果/强趋势:`03_strong_as_is/`、`04_strong_trends/`(data+tables+figures+result_cards)
- 攻击链:`05_attack_chain/`(joint_analysis + attack_chain_status.csv)
- 过程控制:`06_process_control/`(language_act_channel + headroom + action space)
- 自适应/surrogate:`07_adaptive_static/surrogate_analysis/`
- 跨实验:`09_tables/cross_experiment_evidence.csv`
- 图:`10_figures/figA–figG.png`
- 脚本:`11_scripts/01–07 + _common.py + run_all.sh`
- SOURCE_LEVEL:R9v2/R9v1 = EPISODE_LEVEL(重算);R6 = EPISODE_LEVEL(析因另见);R7/R8/MISROUTE = SUMMARY_ONLY(取自各自冻结报告,已标注)。
