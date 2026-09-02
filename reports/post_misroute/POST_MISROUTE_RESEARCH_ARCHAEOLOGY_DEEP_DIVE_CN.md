# MISROUTE 之后的科研考古深挖报告
## Post-MISROUTE Research Archaeology Deep Dive

> 一次性、repository 级的科研考古 + 实验审计 + 科学发现提炼 + 论文方向判断。
> 覆盖 `/home/xqin5/llmlanguage` 全仓库(含 git 历史)近两个月工作,不限于 R9。
> 撰写:2026-08-30。方法:遍历 working tree + `git log --all` + 回到 raw JSON/CSV 核验关键数字 + 轻量 reanalysis(全部标注 EXPLORATORY)。
> 证据等级:**[A]** 预注册确证+门通过 / **[B]** 确证但解释受限 / **[C]** 有效冻结数据的后验重分析 / **[D]** pilot/诊断 / **[E]** 工程观察 / **[F]** 已失效。

---

# 0. Executive Summary（执行摘要）

## 0.1 我们 MISROUTE 后到底做了什么

MISROUTE(0730 稿)不是这条研究线的终点,而是 **R8 之后从同一批基础设施分叉出的三条并行论文线之一**。R8(2026-07-18,完整回合压力测试,2680 episodes,calibrated null)之后:

1. **MISROUTE benchmark**(`MISROUTEbenchmark/`,0730 稿 + github release):把 R8/C2 的"同奖励、不同路线"打包成 τ²-bench 上的轨迹敏感性 benchmark。**最成熟,已成稿。**
2. **EACL Process-Robustness 论文包**(`EACL_..._20260718/`):把 R6/R7-C/R8 打包成一篇**方法学论文**——"松散的过程级评估会系统性高估 agent 脆弱性"。**有完整 outline + claim boundary,未成稿。**
3. **R9 机制对齐过程攻击**(`ir_mstu_stage2/scripts/r9_attack/`,0722–0828):把问题收窄到一个具体机制(**核验深度** verification depth)+ 自适应攻击器 + 因果门。**跑完 R9v1/R9v2,决策 F。**

此外 `tier_a_strengthening_20260722/` 与 `r8_c2_paper_evidence_dossier_20260722/` 是 MISROUTE 的强化/取证包。

## 0.2 repository 中实际有几条 scientific line

**一条主问题,七年式收窄,但最终沉淀出三个可分离的科学命题**(不是三个"更深的 MISROUTE"):

| 命题 | 一句话 | 现状 |
|---|---|---|
| **S1 轨迹敏感性 benchmark** | 同奖励可掩盖不同工具路线(vs 重复漂移) | = MISROUTE,已成稿 |
| **S2 松散过程评估高估脆弱性** | 不校准随机/措辞漂移 → 假阳性攻击 | = EACL,半成品 |
| **S3 敏感≠可控 + 正确的 null 是"中性措辞分布"** | agent 路线对任意中性改写和对定向压力**一样敏感**;压力不特异、不可定向操纵;只有显式指令可控 | **散落在 R7-D/R9/tier_a,从未被作为正面发现整合** ← **最被低估** |

## 0.3 R9 是否真的是最强方向

**不是。** R9 作为"攻击"是 **F**(核验深度不被隐式压力移动;自适应不胜静态;见 §5)。但 R9 的**数据**里藏着 S3 最干净的一块证据(路线距离层级)。R9 的价值应从"一个失败的攻击"重定义为"S3 的第三个独立数据点 + 机制定位(排除 verification-depth 通道)"。

## 0.4 最被低估的 finding（本报告的核心发现）

**跨三个独立数据集、三种度量、五个模型,同一个层级结构成立:**

```
重复漂移(同 prompt 换 seed)  ≪  中性措辞变动(换个中性说法)  ≈  定向压力/攻击  ≪  显式指令
```

| 数据集 | 度量 | 重复漂移 | 中性措辞 | 压力/攻击 | 显式 | 来源 | 等级 |
|---|---|---|---|---|---|---|---|
| R7-D(τ²,gemma/mistral/gpt-oss) | PASR | P0=1.44% | P2=3.65% | 4.03% | 正控制 P=+3.58 tools | `r7d_ipma/STEP1_PLACEBO_SOURCE_AUDIT_CN.md` | [C] |
| R9v2(BFCL-deep,qwen-72B) | 路线归一化 Levenshtein | C1–C1=0.008 | C1–C2=0.189 | C3=0.197/C4=0.204 | C5=0.439 | `results/r9v2/confirmatory/`(今日重算) | [C] |
| MISROUTE(τ²,3 模型) | tool+arg 距离 excess | NN pseudo≈0(20/20 不显著) | C1–C0=0.149※ | C2–C1=0.112 | — | `tier_a_.../C0_C1_C2_TRIANGLE_ANALYSIS.csv` | [B/C] |

※C1–C0 是 native-vs-rendered,含实现混淆(tier_a 标 LOW_COMPAT);但它**已经**大于 urgency 效应,且 tier_a 升级 claim **自己承认**"不足以把效应唯一归因于 urgency 语义"。

**含义:** 任何"交互压力/攻击改变 agent 行为"的 claim,正确的 null 不是"同 prompt 换 seed",而是"语义等价的中性改写分布"。在这个更强的 null 下,**定向压力的表观效应基本消失**(压力 ≈ 中性改写),只有**显式指令**保留定向控制。**敏感性 ≠ 可控性。**

## 0.5 目前最有希望的 standalone paper

**S3:《Sensitivity is not Controllability: The Right Null for Interaction-Robustness Claims in Tool-Using Agents》**(暂名)。它**统一**了 EACL(方法学)、R7-D(证据)、R9(证据+机制)、并**批判性地修正** MISROUTE 自己的 null 选择。跨 2 基准、5 模型、3 度量;既是方法论贡献(正确的 null),又是实证贡献(敏感≠可控 + 显式/隐式不对称)。**独立投稿价值 8/10**(见 §9/§10)。

## 0.6 最关键的下一个实验

**在 τ²(MISROUTE 自己的基座)上加 K≥5 个语义等价的中性渲染,估计"中性措辞路线距离分布",检验 urgency 是否超出该分布**(而非仅超出重复漂移 NN)。一个实验直接判定 MISROUTE 头条是"紧迫特异"还是"措辞泛化",并把 S3 从 BFCL/qwen 单点升级为跨基准确证。基础设施已存在(τ² adapter + renderer),约 1–2 GPU·日。见 §12。

---

# 1. MISROUTE 的真实 contribution 与边界

## 1.1 research question 与 estimand
**RQ:** 在任务/权限/policy/初态/评估器全固定下,首轮 urgency 措辞是否使工具执行轨迹相对**匹配中性重复漂移**产生 separation,同时官方 reward 保持实际等价?
**Estimand:** 每任务的 `D(urgency, neutral) − D(neutral_repeat_i, neutral_repeat_j)`(TN − NN),三种表示(tool-name / tool+canonical-arg / functional-stage),task-cluster bootstrap 聚合。

## 1.2 MISROUTE 已经做了什么(后续不得重复包装为新贡献)
matched-context 评估;TOST outcome 等价(±5pp);**NN = 中性重复漂移校准**;三种轨迹表示;task-cluster bootstrap;matched-label / neutral-only falsification(5000 置换);**alternative neutral constructions / 1000 随机中性配对**;outcome-concordant restriction;705-spec multiverse;task-removal/influence;modal-route relocation;adherence/unseen-support/within-dispersion;insertion/substitution 分解;first-divergence;before/after first write;reconvergence;3 模型;airline+retail;case audit。

## 1.3 核心实证结果(raw:MISROUTE Table 1 / tier_a)
- reward:matched-neutral 0.2500 vs urgency 0.2648,Δ+1.48pp,TOST p=.0388 → 等价 **[A]**
- process:tool+arg excess **0.1118** CI[.073,.152],ratio 1.38,BH q=.0001;置换 max 0.1118 = 7.2× null 95th,p=1/5001 **[A]**
- 705/705 spec estimate>0,703 CI>0 **[A]**

## 1.4 MISROUTE 没问什么 / null 没控什么 / metric 看不到什么（后续工作的合法空间）
1. **没预定义并因果检验某个具体 operational process 变量**(如 verification depth / first-write hazard)——只有聚合轨迹距离。→ R9 的合法空间。
2. **NN null 只是"同一中性构造的随机重复漂移",不是"语义等价的不同中性措辞分布"。** MISROUTE 的"alternative neutral constructions" robustness 是**改变配对/匹配规则**,不是**改变中性措辞本身再当作处理**。→ S3 的合法空间,也是 MISROUTE 最脆弱的一环。
3. **没区分 sensitivity 与 directional controllability**:证明了"urgency 使路线不同",没证明"攻击者能把路线朝想要的方向推"。→ S3。
4. **没有 attacker 优化 / adaptive**:urgency 是固定首轮措辞。→ R9 的合法空间。
5. **tier_a 自证的边界(关键)**:`TIER_A_UPGRADED_CLAIM.md` 判定 **"B. CORE RESULT ROBUST BUT MECHANISM LIMITED"**,明文:"C1–C0 低兼容负对照不为零……**不足以把效应唯一归因于 urgency 语义**"。**MISROUTE 团队自己已经知道 urgency-specificity 站不稳。**

## 1.5 强 / 弱
- 强:instrumentation 极扎实(置换、multiverse、influence);outcome 等价可信;机制诊断丰富。
- 弱:**urgency-specificity 未被干净证明**(1.4.5);单一 benchmark(τ²);效应是"路线偏离",不直接映射到安全/效率后果。

---

# 2. Repository-wide Scientific Lineage（研究谱系）

git 根:`ir_mstu_stage2/`。分支:`stage2_5b-confirmatory-repair` → `r4-minimal-repair` → `r5-measurement-repair` → `r7d-construct-causal-rebuild` → `r7d-mvep-remediation-v1` → `r9-mechanism-aligned-process-attack`。tag 记录 R4/R7-D 各 step 冻结点。

| 轮 | 日期 | 规模 | RQ | 判定 | 遗产 | 等级 |
|---|---|---|---|---|---|---|
| Pilot | 06 初 | 480 | 语气改变结果? | 强模型依赖(Qwen-7B 敏感/gpt-oss 免疫) | noise-floor 协议 | [D] |
| Stage-2 mini | 06-11 | — | 扩到多轮 | **污染作废**(模板混入 continuation) | "先查模板 continuation" | [F] |
| Stage-2.5 | 06-14 | — | 因果修复+审计 | LLM user-sim 漂移 93/101 → 判死历史数据 | 指标三分层(official/proxy/safe) | [E] |
| R4/R4.1 | 06-21/24 | 480×2 | 确定性用户重跑 | 端点 null;过程显著但**R4.1 未复现**(−0.15→−0.075) | 确定性三层用户,155/155 invariance | [D] |
| **R5** | 06-24 | 480 | 修测量+全量复现 | **0/120 FDR**,过程信号确证不可复现 | 六维画像,双重复算 | [A] |
| **R6** | 06-29 | 2160 | 扩域+析因 | **过程有信号**(路线距离+0.24~0.32);**推动强度的是 continuation 不是情绪** | 析因设计,安全 0 违规 | [B] |
| R7 v1 | 07-06 | 1620 | 升级为攻击(PASR) | PASR≈14%,**后废弃**(pairing/endpoint/semantic 缺陷) | IPMA 威胁模型 | [F] |
| R7-B | 07-09 | 合成 smoke | 严格门控重建 | 只有代码,PASR→4.17% | fail-closed 门 | [E] |
| **R7-C** | 07-10 | 2592 | 严格确证+placebo | **placebo 4.63% ≥ attack 4.03%** | placebo 方法 | [B] |
| **R7-D** | 07-11~14 | 420 探针 | 构念审计+因果重建 | **环境是桩**;**P0<P2≈attack**;**不可实验识别** | S3 的第一块证据 | [C] |
| **R8** | 07-18 | 2680 | 回到完整回合 | **R4 calibrated null**;**scaffold 效应>压力效应** | 官方 evaluator,ITT | [A] |
| → MISROUTE | 07-30 | (R8 数据) | 轨迹敏感性 benchmark | 成稿;tier_a 承认 mechanism limited | benchmark | [A/B] |
| → EACL | 07-18 | (R6/7C/8) | 方法学:高估脆弱性 | outline+claim boundary | 框架 | [B] |
| **R9v1** | 07-22~08-14 | 306→880 | 机制攻击(verification) | **F**(设置伪影:TS 浅/静态/低功效) | 6 条件+因果门 | [F/B] |
| **R9v2** | 08-28 | 1401 | BFCL-deep 修复重跑 | **F 但有信息量**(攻击到位/无效应) | 自适应攻击器,路线层级 | [B/C] |

---

# 3. MISROUTE 之前 / 同期被忽略的实验

- **R6 的 pressure-factorial 才是"attack"叙事的真源头**,但 R6 最强、最少被引用的 insight 是**否定性**的:"社会语气改路线,但真正推高行动强度的是 continuation/urgency 这类**任务推进线索**",且 **insult+urgency 提高确认率(+0.133)= 更谨慎不是更危险**。这条"压力让 agent 更小心"的方向性**从未被单独追下去**。
- **Pilot 的跨模型两极**(Qwen-7B 敏感 vs gpt-oss 免疫)是"capability × sensitivity"命题的第一个数据点,被"换 3 个中模型"掩盖过去。
- **未发现** MISROUTE 之前有完全独立、被埋没的第四条线;主要遗漏都在"同一批数据的否定性/方向性 sub-finding 没被追"。

---

# 4. MISROUTE 后所有实验和方向（逐个详写）

## 4.A MISROUTE benchmark（S1）
- **Purpose/Hypothesis:** 同奖励下 urgency 使路线相对中性重复漂移 separation。
- **Setup:** τ² 1.0.0(ddc66a7),36 任务(18 airline+18 retail),3 模型,5 seed,2700 计划/2680 有效。
- **Conditions:** C0 native / C1 matched-neutral / C2 first-turn urgency(focal)/ C3 adaptive urgency / C4 adaptive frustration。
- **Metrics:** TN−NN 轨迹距离(3 表示);TOST reward。
- **Exact results:** §1.3。
- **What survived / hidden:** urgency 路线 separation 稳健 **[A]**;但 tier_a 的 **C1–C0=0.149 > C2–C1=0.112** 与 **NEUTRAL_PSEUDO_TREATMENT 20/20 不显著**共同揭示:**大头是"渲染中性 vs 原生中性"这一非压力差异,不是 urgency**(§6.1)。
- **Evidence grade:** 主结果 [A];urgency-specificity [B-,tier_a 自降]。

## 4.B EACL Process-Robustness 论文包（S2）
- **Purpose:** 不新增实验,把 R6/R7-C/R8 综合成方法学论文。
- **Recommended title(已写):** *Beyond Final Reward: Auditing Interactional Process Robustness in Tool-Using LLM Agents*。
- **可进正文的 claim(CLAIM_BOUNDARY.md):** R8 pooled reward/tool 实际 null;R6 post-hoc 有限过程 excess(须报模板混杂);**R7-C attack ≤ placebo → 不校准漂移会造假阳性**;outcome/process 必须独立 evaluator+placebo+实际阈值。
- **禁止:** R7-v1 14%;"证明普遍 stable-outcome-unstable-process";任何安全保证。
- **What survived / gap:** 框架干净、claim 纪律极严 **[B]**;但**缺一个正面的、可 confirmatory 的核心结果**——它是"审计三个历史协议"的综述型 negative,reviewer 会问"so what's the one new controlled result"。**S3 恰好能补这个洞**(把"敏感≠可控"做成正面 confirmatory)。
- **Evidence grade:** [B]。

## 4.C R9 机制对齐过程攻击
见 §5 全审计。

---

# 5. R9 Full Audit（拆开 invalid-F / informative-null / post-hoc）

## 5.1 原 hypothesis
用户侧过程压力(压缩=催促→少核验;膨胀=怀疑→多核验)能**定向、可优化地**改变 agent 的 **verification depth**(写前只读检查数),且**自适应攻击(C4)胜过静态(C3)**。

## 5.2 R9v1(880 ep,gemma/mistral,BFCL+ToolSandbox)——**invalid F**
- 门:G1 pass;**G2 FAIL(TS)** C0 0.72 vs C1 0.36;**G3 FAIL**;**G4 FAIL** adaptive_share 0.49<0.70。
- 主检验全 null(compression_C4_C1 −2.21 CI[−5.95,0.49];inflation_C4_C3 +0.153 CI[0.015,0.32] 唯一不跨 0 但次要)。
- **判定:invalid-F(设置伪影)** [F]:TS 太浅(G2)、攻击器还静态(G4)、功效不足。**不能当真阴性。**
- Source:`results/r9_attack/confirmatory/analysis.json`。

## 5.3 R9v2(1401 ep,qwen-72B,BFCL-deep)——**informative null**
- 模型校准(`selected_models.json`):qwen-72B 0.438 唯一过带 [0.40,0.90];qwen-32B 0.250、llama-70B 0.125 真实不足。→ 单模型。
- 门:**G1 PASS**(C0 0.329);**G2 FAIL**(C0 0.329 vs C1 0.459,|Δ|0.130>0.05);**G3 压缩 FAIL/膨胀 PASS**;**G4 PASS**(adaptive_share 1.0,交付缺陷已修)。
- 主检验全 null(Holm 无拒绝):compression_C4_C1 +0.053 CI[−0.237,0.276];C4_C3 −0.006;inflation_C4_C1 −0.018;C4_C3 −0.004。
- ASR/FPR:压缩 0.0/0.051;膨胀 0.149/**0.202**(FPR>ASR)。
- 原始机制指标(把 null 讲具体):
  - 压缩 VD:C1 1.401 / **C4 1.455** / C5 1.759 → 攻击没压低,连显式 C5 都没压低。
  - 膨胀 VE:C1 1.836 / **C4 1.818** / **C5 4.832** → 攻击没抬高,但**显式 C5 暴涨 2.6×**。
- **判定:informative null** [B]:攻击**到位**(G4)但**无效应**;障碍是 G2 措辞敏感 + 压缩方向不可控。
- Source:`results/r9v2/confirmatory/analysis.json`。

## 5.4 R9 的 post-hoc 发现（本次考古新增,[C]）
- **路线距离层级**(§0.4/§6.1):repeat 0.008 ≪ construction 0.189 ≈ pressure 0.197–0.204 ≪ explicit 0.439。→ 机制 null 不是"测错了",而是**压力根本不比中性改写更能改路线**。
- **机制定位**:路线会变(vs repeat),但**不经 verification-depth 通道**(压缩 VD null)——排除了一个具体 operational 变量,是相对 MISROUTE 的真机制细化。
- **方向不对称**:显式"多核验"有效(VE 4.83)、"少核验"无效(VD 1.76)。

## 5.5 R9 逐题回答
1. 原 hypothesis:压力定向可控 verification。**被 5.3/5.4 证伪。**
2. invalidate 原 hyp 的:C4≈C1(VD/VE)、C4≈C3、压力≈中性构造(路线)。
3. 真正有信息量的 null:R9v2(G4 pass 下的 null)。
4. 因 gate 不能解释的 null:R9v1(G2/G4 fail)。
5. 后验发现:路线层级 + 方向不对称。
6. 已复现:路线层级复现了 R7-D 的 P0<P2≈attack。
7. 已完全不同于 MISROUTE:**verification-depth 机制定位** + **中性构造对照**。
8. 仍只是 MISROUTE extension 的:"路线会变"本身。
9. **删掉"attack"后数据最自然支持:** "capable agent 的工具路线对任意措辞高度敏感,但不可被隐式压力定向操纵;只有显式指令可控。"= **S3**。
10. 若放弃 R9,更好的现成方向:**S3**(把 R9 数据当 S3 的一个点)。

---

# 6. Cross-Experiment Phenomena（最重要章节）

## 6.1 重复漂移 vs 中性措辞漂移 —— **[C], 跨 3 数据集复现**
见 §0.4 表。**结论:中性措辞变动是比随机重复大一个量级的 null**(BFCL:0.189 vs 0.008,~25×;R7-D:3.65% vs 1.44%)。MISROUTE 用小的那个(重复漂移 NN)作 null,是全项目最重要的、**尚未被写成正面发现**的方法学裂缝。
- 诚实限定:BFCL 只有 2 个中性渲染(C1/C2)→ 只能叫 **stronger neutral-construction control / exploratory**,不能叫"正确 null";要估真分布需 K≥5 个中性改写(§12)。τ² 的 C1–C0 含 native-vs-rendered 混淆。R7-D 的 P2 在**桩环境**(§6.7)——但 P0<P2 的结构与桩无关(是 evaluator/model 对措辞的敏感)。

## 6.2 敏感性 vs 定向可控性 —— **[C]**
压力 ≈ 中性构造:BFCL C3 excess over C1–C2 = **+0.008 CI[−0.033,0.048]**、C4 = **+0.015 CI[−0.029,0.055]**(跨 0);R7-D 压力−良性改写 = **+0.38pp**(MDE 4pp)。**高敏感 + 零定向控制**。这是 S3 的心脏。

## 6.3 显式 vs 隐式 —— **[C]**
只有显式指令移动行为:BFCL C5 路线 +0.252 over 构造、VE 4.83;R7-D 正控制 P +3.58 tools(唯一显著,perm_p .041)。**攻击面在"显式命令",不在"语气"。**

## 6.4 压缩 vs 膨胀不对称 —— **[C]**
"多核验"可诱导(VE C1 1.84→C5 4.83),"少核验"不可(VD C1 1.40→C5 1.76)。R7-D 正控制也是"迫使 no-op 模型多调工具"(单向)。**方向不对称:让 agent 更谨慎易,更草率难**——安全上乐观。须区分是 alignment / policy / metric floor(压缩有地板:本来就少读)——**这是 hostile reviewer 的第一刀**(§11)。

## 6.5 静态 vs 自适应压力 —— **[B]**
自适应不胜静态:R9v2 C4≈C3(全 4 检验)。R7 里唯一显著推高工具的是 **continuation**,但 R6 证明那是**任务推进语义**混入,非情绪/压力。→ **"优化语言压力 ≠ 优化行为控制"**(候选 thesis 4)。

## 6.6 模型能力 vs 鲁棒性 —— **[C/D]**
Pilot:Qwen-7B 敏感 / gpt-oss 免疫。R6:三模型三失效画像(gemma 过拒 0.357 / gpt-oss 低过拒低完成 / mistral 高完成弱拒绝)。R9:qwen-72B **措辞敏感(G2 fail)但 verification 鲁棒**。**能力↑ 未必鲁棒↑,可能是"措辞敏感但不可定向"**。matched 跨模型比较仅 R6 干净可用。

## 6.7 benchmark 深度 vs 攻击面 —— **[C/E]**
桩环境毁掉 R7-C(**3027 次工具调用 0 次参数被解释**;corr(POS,PASR)=−0.576);ToolSandbox 太浅(R9v1 G2 fail);BFCL-deep 有 verification surface 但 **capable 模型把 read 前置到 prefix**(R7-D null-by-construction),使 suffix 内无可操纵过程。→ **"过程可操纵性只在特定交互深度以上出现,且被模型的前置读取行为抵消"**(候选 thesis 6)。

## 6.8 outcome-process 解耦 —— **[A/B]**
MISROUTE:同 DB hash、不同路线。R8 endpoint-preserved:双成功配对里过程位移极小(C3 +0.37 median 0)。→ 解耦真实但**幅度小**;S3 不依赖它。

## 6.9 **Scaffold 效应 > 压力效应** —— **[A],最反直觉**
R8:C1−C0 reward **−0.109**、tools **−1.00**;**大于所有压力效应(+0.5~0.69)**。tier_a 路线:C1–C0=0.149 > urgency 0.112。**"换一个用户模拟器实现"比"用户是否辱骂 agent"更改变行为。** 这是 S3 的强佐证,也是对整个 agent-eval 领域的警告(实现细节 = 混淆变量)。

## 6.10 首次 mutation 前的过程 —— **[C/D]**
R7-D:junction 前 read 已花完 → 压力作用区无过程。R8:before-first-write 分歧存在但小。→ 支持 6.7 的前置读取解释。

---

# 7. 现有 POST_MISROUTE_WORK_DETAILED_CN.md 漏 / 弱 / 错

- **漏(严重):** 完全没提 **EACL 论文包**、**tier_a 的 C1–C0 自证 caveat**、**R7-D 的 P0<P2≈attack**、**R8 scaffold 效应**、**R6 析因/continuation 归因**。→ 它把"MISROUTE 后"窄化成 R9,正是合作方"没区分度"的根因。
- **弱:** 把 S3(敏感≠可控 + 正确 null)写成"R9 的一个副产品",而它其实是**贯穿 R6→R7-D→R8→R9→MISROUTE-tier_a 的主线**。
- **错/过强:** 早期口径把 R9 路线 excess 说成"26× 漂移的巨大效应"——那对的是重复漂移(误导);对中性构造后 ≈0(§6.2)。已在本报告更正。
- **把 MISROUTE 说弱:** 不能说"MISROUTE 只测路线变没变"——它有 modal relocation/dispersion/first-divergence/reconvergence 一整套机制诊断。**精确说法:** MISROUTE 未预定义并因果检验某个具体 operational 变量(如 verification depth),也未把 null 从"同 prompt 重复漂移"升级到"语义等价中性措辞分布",也未区分 sensitivity 与 directional controllability。
- **应升为 headline 的:** §6.1 层级 + §6.9 scaffold 效应。
- **应移到工程附录的:** mutation 检测/B-H3/ResultsSink/自适应交付修复(是让 R9 valid 的工程,不是科学贡献)。

---

# 8. R9 是否在科学上胜过 MISROUTE？

| 维度 | MISROUTE | R9(作为攻击) | R9-data→S3 |
|---|---|---|---|
| novelty | 中(轨迹敏感 benchmark) | 低(又一个 null) | **高(修正 null 选择)** |
| clarity | 高 | 中(F 难讲) | 高 |
| importance | 中 | 低 | **高(纠正领域 null)** |
| breadth | 3 模型 2 域 1 基准 | 1 模型 1 基准 | **2 基准 5 模型 3 度量** |
| causal validity | 高 | 中(G2 fail) | 中高 |
| mechanistic depth | 高(诊断) | 中(定位否定) | 中 |
| empirical strength | 高 | 弱(null) | 中高(复现) |
| generalization | 中 | 低 | **高** |
| story coherence | 高 | 低 | 高 |
| reviewer defensibility | 高 | 低 | 中(须防 §11) |

**诚实结论:** R9 作为"攻击" **不**胜过 MISROUTE(工程复杂 ≠ 科学贡献)。但 **R9-data 喂给 S3** 后,S3 在 novelty/importance/breadth 上**可与 MISROUTE 并立甚至更 general**,且**不与 MISROUTE 冲突**(S3 用 MISROUTE 基础设施问一个不同且更基础的问题)。**合作方"单独不如 MISROUTE"对 R9-as-attack 成立,对 S3 不成立。**

---

# 9. Candidate Standalone Papers（候选论文）

> 模板:核心结论 / 科学问题 / 为何重要 / 为何不是 MISROUTE / 已有证据(含 grade)/ 最有意思现象 / 竞争解释 / 缺口 / 最危险 reviewer 批评 / 决定性实验 / 结果分支 / 算力 / 与 MISROUTE 共存 / 价值 1-10。

## Candidate 1（★最强）：Sensitivity ≠ Controllability + 正确的 null
- **核心:** agent 工具路线对**任意中性改写**和对**定向压力一样敏感**,压力不可定向操纵;唯有显式指令可控。因此交互鲁棒性/攻击 claim 的正确 null 是"中性措辞分布",非"同 prompt 重复"。
- **为何不是 MISROUTE:** MISROUTE 用重复漂移 NN 作 null 且 headline urgency-specific;S3 证明该 null 太弱、urgency 不特异——**直接修正 MISROUTE**。
- **证据:** §0.4 三数据集层级 [C];§6.2 压力≈中性构造 [C];§6.9 scaffold>压力 [A];tier_a 自证 [B]。
- **最危险批评:** "只有 2 个中性构造,不是真分布"(§11)。
- **决定性实验:** τ²+BFCL 各 K≥5 中性改写,测 urgency 是否超出中性分布(§12-E1)。
- **共存/价值:** 与 MISROUTE 强共存(引用+修正);**9/10**。

## Candidate 2：Benign Wording is a Stronger Null（方法论文,S2 升级版）
- **核心:** agent-robustness 评测必须以"语义等价 prompt 分布"为 null,否则系统性假阳性。
- **证据:** EACL 框架 + R7-C placebo≥attack [B] + §0.4 [C]。
- **与 C1 关系:** C1 的方法学外壳;可合并为一篇的 §3。**8/10**(独立稍偏综述)。

## Candidate 3：Asymmetric Controllability of Verification
- **核心:** 可诱导 agent **多**核验/多确认,难诱导**少**核验(跨隐式压力与显式指令)。
- **证据:** §6.4 [C](VE C5 4.83 vs VD C5 1.76);R6 insult+urgency 提确认 +0.133 [B];R7-D 正控制单向 [C]。
- **最危险批评:** 压缩有 metric floor(本来就少读)→ 是地板不是 alignment。**须加"读取充足"任务子集 + 非核验方向(路径长度/重试)佐证。**
- **价值:** 6/10(单独)、作为 C1 的 RQ3 很强。

## Candidate 4：Optimizing Linguistic Pressure ≠ Optimizing Control
- **核心:** 攻击器可优化"更像施压"的语言,却得不到更强行为控制(reviewer/selector 分数不预测行为效应)。
- **证据:** §6.5 C4≈C3 [B]。**缺口:** 需 reviewer-score↔behavioral-effect 相关分析(数据保留了 candidate/score/trigger,可做,[C])。
- **价值:** 6/10;是 C1 的 RQ,证明"连优化也救不回"。

## Candidate 5：Scaffold Effect —— 用户模拟器实现是隐藏混淆
- **核心:** 换用户模拟器实现对 agent 行为的影响 > 语气/压力效应;跨 scaffold 的 agent-eval 绝对率不可比。
- **证据:** §6.9 R8 C1−C0 [A];tier_a C1–C0 路线 [B]。
- **价值:** 7/10(评测方法学),可作 C1 的一节或独立 short paper。

## Candidate 6：Process Susceptibility × Interaction Depth
- **核心:** 过程可操纵性只在足够交互深度出现,且被 capable 模型的"read 前置"抵消。
- **证据:** §6.7 桩/TS/BFCL/前置 [C/E];task-depth×效应分层可补做 [C]。
- **价值:** 5/10(现证据偏定性)。

## Candidate 7：Safety Boundary is Robust to Social Pressure（最稳,最不新）
- **核心:** >6000 runs,语气/压力从不导致 unsafe/privacy 违规。
- **证据:** R5/R6/R7 全 0 [A/B]。**价值:** 5/10(强但 incremental,适合并入任一篇)。

## Candidate 8：Model Capability × Wording Sensitivity Profile
- **核心:** 能力与鲁棒不单调;capable 模型可"措辞敏感但不可定向"。
- **证据:** Pilot/R6/R9 [C/D];**缺口:** 需 matched 跨模型(现仅 R6 干净)。**价值:** 5/10。

---

# 10. Candidate Ranking

| # | 核心 claim | novelty | 证据强度 | 与 MISROUTE 区分 | ICLR fit | risk | 额外算力 | 期望信息增益 | 总分 |
|---|---|---|---|---|---|---|---|---|---|
| **1** | 敏感≠可控+正确 null | 高 | 中高(跨 3 集) | 强(修正) | 高 | 中 | 低(1–2 GPU日) | 高 | **9** |
| 2 | 良性措辞是更强 null | 中高 | 中 | 强 | 中高 | 低 | 无 | 中 | 8 |
| 5 | scaffold 混淆 | 中 | 高 | 中 | 中高 | 低 | 无 | 中 | 7 |
| 4 | 优化语言≠优化控制 | 中高 | 中(可补) | 中 | 中 | 中 | 低 | 中 | 6.5 |
| 3 | 核验不对称可控 | 中 | 中 | 中 | 中 | 高(地板) | 中 | 中 | 6 |
| 6 | 深度×可操纵 | 中 | 低 | 中 | 中 | 中 | 中 | 中 | 5.5 |
| 7 | 安全鲁棒 | 低 | 高 | 弱 | 中 | 低 | 无 | 低 | 5 |
| 8 | 能力×敏感画像 | 中 | 低 | 中 | 中 | 高 | 高 | 中 | 5 |

- **今日最强(现有证据):** #1(+并入 #2/#4/#5 作节)。
- **最高上限:** #1。**最安全:** #2。**最便宜:** #2/#5(0 新算力)。
- **若放弃 R9:** #1 仍成立(R9 只是其三个点之一)。
- **真正独立于 MISROUTE:** #1(问不同问题 + 修正其 null)。

---

# 11. Hostile ICLR Review of Top 3

## #1 敏感≠可控
- **Novelty:** "prompt sensitivity 早有人做(Sclar 2023 等),你只是搬到 agent。" → 反驳:我们做的是**工具执行路线**的定向**可控性** vs 敏感性分离 + 正确 null,非分类输出敏感。
- **Post-hoc/2 constructions:** "C1/C2 只有 2 个中性措辞,凭什么叫'分布'?" → **最致命**,必须靠 E1(K≥5)补,否则只能写 exploratory。
- **Single model(BFCL):** qwen-72B 一个 → 靠 R7-D 3 模型 + τ² E1 多模型补 breadth。
- **G2 fail:** "你的中性脚手架都不中性,怎么谈中性 null?" → 反转成卖点:**连中性脚手架都移动行为,正是'措辞敏感淹没定向'的直接证据**;但须显式讨论。
- **Benchmark artifact:** BFCL/τ² 的 route 距离是否 evaluator 假象 → 用双度量(tool-name/arg)+ 置换。
- **Rebuttal feasibility:** 高(E1 一个实验解决 2/3 大刀)。

## #2 良性措辞更强 null
- **"综述,无新结果":** → 靠 E1 的正面 confirmatory 结果补;否则 desk-reject 风险。
- **"只在你这套 renderer 成立":** → 需 ≥2 renderer 家族。**Rebuttal:** 中。

## #5 scaffold 效应
- **"只是 sim2sim 差异,已知":** → 需证明它**系统性大于**被研究的处理效应(已有 R8 数值),并跨基准。**Rebuttal:** 中高。

---

# 12. Decisive Experiments（只选 3 个）

## E1（★若只能做一个,做这个）：中性措辞分布 vs 压力
- **RQ:** urgency/压力是否超出**语义等价中性措辞分布**(而非仅超出重复漂移)?
- **竞争假设:** H_specific(压力>中性分布)vs H_general(压力∈中性分布)。
- **设计:** τ²(MISROUTE 基座,复用 renderer)+ BFCL 各准备 **K=6 个盲审等价的中性渲染** + 静态压力 + 自适应压力 + 显式正控制;每任务估中性分布的均值/上尾。
- **模型:** τ² 用 MISROUTE 原 3 模型(gemma/gpt-oss/mistral)+ qwen-72B。任务:MISROUTE 36 + BFCL 40。repeats=3。
- **主指标/对比:** 路线距离(tool-name+arg);pressure_excess = D(pressure,C1) − mean_k D(neutral_k,C1);检验 CI 是否 >0。
- **结果分支:** 压力显著超中性分布 → **H_specific,MISROUTE 加强、S3 变"但仍可控"**;压力∈中性分布(预期)→ **S3 成立,urgency 非特异,强 paper**;null(全都不动)→ 该基准/模型无过程可动,换基准。
- **算力:** ~1–2 GPU·日(无新模型下载)。**基础设施已存在**(τ² adapter + renderer + 路线分析)。**约 2–3 天。**

## E2：显式-隐式可控性 + 核验方向不对称(排除地板)
- **RQ:** "少核验"不可诱导是 alignment 还是 metric floor?
- **设计:** 只取 **min_prereq≥3(读取充足)** 任务子集;加"路径长度/重试/确认"多方向指标;显式 C5(多/少)+ 隐式。
- **分支:** 充足子集里"少核验"仍不可诱导 → **真不对称(Candidate 3 成立)**;可诱导 → 原是地板,C3 降级。
- **算力:** ~0.5 GPU·日(复用 R9v2 任务)。

## E3：优化语言 ≠ 优化控制(纯离线,0 GPU)
- **RQ:** attacker reviewer/selector 分数是否预测行为效应?
- **设计:** 对 R9v2 保留的 candidate/score/trigger,做 score↔ΔVD/Δroute 相关 + optimizer's-curse 检验(选中"更强压力"是否只增措辞差异不增方向性)。
- **分支:** 无相关 → Candidate 4 成立。**算力:0(现有数据)。可立即做。**

---

# 13. Recommended Paper Story（给 #1 的论文式 outline）

- **Tentative title:** *Sensitivity is not Controllability: Choosing the Right Null for Interaction-Robustness in Tool-Using Agents*
- **One-sentence claim:** 工具 agent 的执行路线对**任意中性改写**与对**定向压力一样敏感**,故交互鲁棒性/攻击的正确 null 是中性措辞分布;在该 null 下压力不可定向操纵,唯显式指令可控。
- **Abstract logic:** (1) 现有 agent-robustness/attack 以"同 prompt 随机重复"为 null → 高估脆弱;(2) 提出"中性措辞分布" null + 区分 sensitivity/controllability;(3) 跨 τ²+BFCL、5 模型、3 度量:repeat ≪ 中性措辞 ≈ 压力 ≪ 显式;(4) 攻击优化与自适应也不越过中性分布;(5) 方向不对称(多核验易少核验难);(6) 框架 + 对既有正结果(含 MISROUTE)的 null 重校准。
- **Figure 1:** 四段层级条形图(repeat/中性/压力/显式)× 3 数据集叠放——**本报告 §0.4 的表就是 Fig 1 草图**。
- **RQ1:** 中性措辞漂移多大 vs 重复漂移?(E1)
- **RQ2:** 压力/自适应/优化能否超出中性分布?(E1/E3)
- **RQ3:** 什么可控?(显式 + 方向不对称,E2)
- **Main table:** 各(基准×模型)的四段层级 + pressure_excess CI。
- **Method contribution:** neutral-construction null + sensitivity/controllability 分离协议。
- **Empirical contribution:** 跨基准跨模型层级 + 不对称 + 优化失败。
- **Limitations:** K 有限;route 距离非唯一后果度量;capable 模型前置读取。
- **为何强于 R9 framing:** 从"我们的攻击失败了(F)"→"我们发现整类攻击评估用错了 null,并给出正确 null 与可控性的边界"——**负结果变成方法学 + 实证的正贡献,且直接对话并修正 MISROUTE。**

---

# 14. Final Recommendation（逐条回答）

1. **合作方"目前工作单独不如 MISROUTE"对不对?** 对 **R9-as-attack** 对;对 **repository 里潜藏的 S3** 不对。
2. **实验弱还是叙事弱?** **主要是叙事/框架弱**(把跨 5 轮复现的 S3 埋成"R9 的 F");实验有真短板(K=2 中性、单模型),但 E1 一个实验即可补。
3. **R9 值得继续吗?** 作为"攻击"不值得;作为 **S3 的一个数据点 + 机制定位**值得保留。
4. **R9 哪部分保留?** 路线层级分析、方向不对称、C4≈C3(优化失败)、自适应攻击器基础设施。
5. **有没有比 R9 更好的现成方向?** 有:**S3**(#1),证据已跨 R6/R7-D/R8/R9/MISROUTE-tier_a。
6. **最被低估的发现?** §0.4 层级 + §6.9 scaffold 效应——**都已在数据里,从未被写成正面 headline**。
7. **最危险的错误叙事?** 继续把它讲成"我们做了一个过程攻击 benchmark"(= MISROUTE 的弱化复制,合作方正是此感受)。
8. **最该停止做什么?** 停止在单模型上加码"attack" confirmatory;停止用"重复漂移"作 null。
9. **最该马上做什么?** **E3(0 算力,今天可做)** + **E1 规划**(τ² 加 K≥5 中性渲染)。
10. **投 ICLR 的合理路线?** 以 **#1(S3)** 为主线,吸收 #2(方法)/#4(优化失败)/#5(scaffold)作 RQ/节;跑 **E1**(决定性)+ E2/E3(支撑);MISROUTE 作为**被修正并共存**的相关工作。**这是把两个月工作变成一篇独立、且与 MISROUTE 有真区分度论文的最短路径。**

---

## 附:外部 novelty 检索状态
本次未执行联网检索(以内部考古为先)。**投稿前必做**:对 #1 检索 2024–2026 的 agent trajectory robustness / prompt-paraphrase robustness / sensitivity-vs-controllability / process evaluation(建议 query:"agent tool-use trajectory robustness paraphrase null","sensitivity vs controllability language model agents","neutral rephrasing baseline agent evaluation")。重点排查 Sclar et al.(format sensitivity)、Jeong et al. 2026(task-irrelevant persuasion)、Lee 2026(canonical-path deviation)与本 null-选择 命题的边界。

## 附:关键证据路径(可复核)
```
LLMLANGUAGE_轮次进展与试错总结_CN.md                                  # R1-R8 lineage(骨架)
ir_mstu_stage2/reports/r7d_ipma/STEP1_PLACEBO_SOURCE_AUDIT_CN.md      # P0 1.44 / P2 3.65 / attack 4.03
tier_a_strengthening_20260722/C0_C1_C2_TRIANGLE_ANALYSIS.csv          # C2-C1 0.112 / C1-C0 0.149
tier_a_strengthening_20260722/NEUTRAL_PSEUDO_TREATMENT_RESULTS.csv    # 20/20 中性伪处理不显著
tier_a_strengthening_20260722/TIER_A_UPGRADED_CLAIM.md                # "mechanism limited" 自证
EACL_..._20260718/08_PAPER_BLUEPRINT/{CLAIM_BOUNDARY,PAPER_OUTLINE_EN}.md
ir_mstu_stage2/results/r9v2/confirmatory/{analysis.json,confirmatory_episodes.jsonl}  # R9v2 + 路线层级
ir_mstu_stage2/reports/r8_full_episode/R8_FULL_EPISODE_MULTI_STEP_STRESS_TEST_CN.md   # scaffold 效应
MISROUTEbenchmark/misroute-github/README.md                          # MISROUTE 成稿
```
（路线层级 §0.4/§6.1 的 BFCL 数字由 `results/r9v2/confirmatory/confirmatory_episodes.jsonl` 今日重算:repeat 0.008 / 构造 0.189 / C3 0.197 / C4 0.204 / C5 0.439,tool-name 归一化 Levenshtein,task-bootstrap 2000。）
