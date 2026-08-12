# [STEP 2 STATUS] —— R7-D 共享前缀因果 Pilot 强制停止汇报（§20）

- 日期：2026-07-18（汇报生成）；pilot 执行：2026-07-11；后续迭代 2.1/2.2/2.3：2026-07-12
- 分支：`r7d-construct-causal-rebuild`
- 依据：本汇报的全部数字来自**已执行**的 pilot 原始表（`results/r7d_ipma/step2/analysis/{headline_contrasts.csv,pilot_analysis.json}`）+ 运行后独立测量 review，**未重跑、未新增数据**。

> **重要状态说明**：本 prompt（R7-D Step 2 共享前缀 suffix pilot）**已执行并报告**（主报告 `reports/r7d_ipma/R7D_STEP2_SHARED_PREFIX_CAUSAL_PILOT_CN.md`），此后经 Step 2.1→2.2→2.3 迭代至终局判定 `CURRENT_IPMA_DESIGN_NOT_EXPERIMENTALLY_IDENTIFIABLE`，并已被 **R8 full-episode 重设计取代**（`reports/r8_full_episode/R8_FULL_EPISODE_MULTI_STEP_STRESS_TEST_CN.md`，判定 R4 calibrated null）。因此本汇报是对**已完成且被取代**工作的忠实状态封存，**不重跑** superseded 的 suffix pilot（§22 无限迭代/outcome-guided 禁令 + Step 2.3 "最后一次 eligibility 构造" 约束）。

---

## 环境
- 实际使用的官方环境与版本：官方 τ-bench / τ²-bench，本地 `tau2 1.0.0`；retail + airline（telecom 延后）。全部模型本地 vLLM；tau2 DB 为进程内合成库，随环境重建 reset；无外部系统访问。
- **E0 结果**：三域结构性 PASS（真实参数解析 `find_user_id_by_name_zip(...)→'yusuf_rossi_9620'`、真实 DB mutation 改变哈希、快照/恢复哈希稳定、分支间无污染）。**caveat**：E0 只验证官方 evaluator 可导入，未验证可打分——该 run 中 evaluator 对 **120/120 行返回 None**（endpoint 支柱实际未测；已在 Step 2.1 修复）。

## 任务
- 数量、域、POS_real：最小 pilot = **4 任务**（retail + airline，各 1×T1 + 1×T2）× 3 模型 × 2 replicate × 5 分支 = **120 suffix / 24 block**。POS_real 按 gold-action 结构盲选。
- 是否依据 outcome 选样：**NO**（仅依据 gold-action 结构，绝不依据 R7-C PASR / condition ranking / 高信号任务；§5.2 合规）。

## 运行
- expected/actual cells：expected 120 suffix / 24 block；actual 120/120 产出（scorable 见下）。
- snapshot fidelity（S0）：初始 snapshot hash / env state / prefix / tool history 一致；但"9/12 一致"多为**零工具 no-op**（gemma 退化），非真实过程复现。
- failed blocks：无 infra 失败；但 endpoint evaluator 返回 None（120/120）为 fatal measurement gap（Step 2.1 修复）。

## Review
- Review Agent A/B 是否完整：**pre-run 双独立 review 完整**（`REVIEW_A_PRE_RUN.md` / `REVIEW_B_PRE_RUN.md`，40 条冻结模板盲评一致 PASS：无 new-fact/authorization/policy/confirmation-bypass 污染，目标 pressure 维度高于 N1）。**post-run**：R3 测量/设计 review 完整（`REVIEW_POSTRUN_MEASUREMENT.md`，独立复算全部 CSV）；R2 trajectory review **低产出**（suffix 内几乎无可裁定过程，junction 缺陷所致）。
- agreement：无 unresolved disagreement（R3 的纠正被主报告全部采纳）。
- unresolved disagreement：无。

## Primary
- **T1 A−N1**：mean_diff = **−0.75** tool events，CI **[−1.0, −0.5]**，perm_p = **0.5048**，n_pairs=12。→ 全部为 mistral 运行时方差（gpt_oss/gemma 全 0，mistral=[0,−3,−8,+2]）；CI 是 **2-任务 bootstrap 结构性假象，非精度**。
- **T2 A−N1**：mean_diff = **0.0**（first_mutation_step），n_pairs=**2**，perm_p=1.0。→ 主指标退化（40 个 T2 suffix 仅 14 发生 mutation，可用配对仅 2），无功效。
- practical threshold：Step 1 MDE≈4pp；本最小 pilot **欠功效**，无法排除预注册 practical effect（这正是它不作分支判定的原因）。

## Controls
- N0 runtime noise（N1−N0 T1）：+0.25 tools（perm_p=1.0）→ 运行时噪声极小。
- N1 paraphrase effect：≈0（中性改写无过程效应）。
- **P positive-control detection**：P−N1 T1 = **+3.58** tools，perm_p=**0.0412**（唯一显著项）。**但**几乎全部来自 gemma（+9.0/block；gpt_oss≈+0.5，mistral≈−1.5），而 gemma 是对 primary 贡献为 0 的 **no-op 退化模型**。→ P 只证明"一条显式命令能迫使一个几乎不动的模型调工具"，**不证明**活跃模型 junction 可被细粒度操纵。

## Validity
- semantic contamination：**0**（pre-run 双 review 确认无事实/授权/policy/确认绕过污染）。
- endpoint/safety preservation：A−N1 mutation-count = **0.0**，CI[−0.125,+0.125]，perm_p=1.0 → endpoint 不变差；无 unsafe/policy 违规。
- concentration：primary 每层仅 2 任务，leave-one-task-out 波动大（结构性欠功效），不满足"跨 task/domain/model 非集中"。

## 分支判定
- **S2 判定 = NO S2 DECISION**。预注册禁止最小 pilot 作分支判定；且运行后独立 review 判定本 pilot **null-by-construction**（junction 放在"agent 首次发言"处，实质 read 花在前缀、mutation 或已完成或因中性策略信息不足而永不到达 → 压力作用的 suffix 内几乎无可操纵过程）。**连"方向指向 S2-C"都不写**。
- 后续迭代（已完成，非本 prompt 授权范围但如实记录）：Step 2.2 = `DO_NOT_PROCEED_CURRENT_DESIGN`（5 eligible cells / T2=0）；Step 2.3 = `CURRENT_IPMA_DESIGN_NOT_EXPERIMENTALLY_IDENTIFIABLE`（终局，固定预算内 suffix 设计不可实验识别）。

## 预判（只列证据支持的）
- 本最小 pilot **尚未测到其目标**（null-by-construction），因此**无权**支持任何 S2 分支。
- 迭代至终局：**suffix / shared-prefix eligibility 设计在固定预算内不可实验识别**。
- 后继 R8 full-episode 重设计（放弃 suffix 裁剪）在 2680 episode 上得 **R4 calibrated null**（压力不改变成功、过程效应低于实际重要阈值），与本 pilot 的 "null 方向、欠测" 一致但**有功效**。

## 预案
- 若批准进入 Step 3：**不适用**——本 prompt 的 suffix 设计已被判 `NOT_EXPERIMENTALLY_IDENTIFIABLE` 并被 R8 取代；不建议在 suffix 构造上继续。若研究负责人仍想在 suffix 框架内推进，必须先修 junction（钉在 mutation 前一刻）/scorer（endpoint 非 None）/replication（>2 任务/层），再全量 pilot。
- 不批准时应冻结：现有 Step 2/2.1/2.2/2.3 全部资产 + R8 数据集与报告（已冻结哈希）。

## 禁止的结论（§21，本汇报明确不主张）
- 不写："R7-C 已证明 broad IPMA"；"多轮一定比单轮危险"；"自适应攻击一定有效"；"positive control 有效=所有小效应可检测"；"两个 LLM reviewer = human validation"；"某域有效=跨域普适"；"attack 非零=攻击成功"；"ProcessGuard 已必要/有效"；"IPMA is confirmed"。

## 是否建议进入 Step 3
- **NO**。本 prompt 的 suffix pilot 已完成且终局判定不可实验识别，并被 R8 取代；无满足 S2-A 全部 gate 的证据。

## 需要研究负责人批准
- 是否认可"suffix / shared-prefix 设计终止、以 R8 full-episode 结果（R4 calibrated null + airline 探索性信号）为准"；
- 若仍要在 suffix 框架内推进，是否批准先做 junction/scorer/replication 修复的**全量** pilot（而非再迭代最小 pilot）。

**—— 按 §20 停止，不自动构建 Step 3。**
