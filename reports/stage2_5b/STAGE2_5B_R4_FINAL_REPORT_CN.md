# IR-MSTU Stage-2.5b 第四轮（代码收敛 + 固定词库用户 + 确认实验）最终中文报告

**完成日期：** 2026-06-21
**驱动者：** reviewer 会话（Codex 限额后接手执行正式实验）
**正式数据根：** `results/stage2_5b_repair/r4_confirmatory_canonical`（480 runs，16 blocks）
**分析输出：** `results/stage2_5b_analysis_r4/`；图表 `figures/stage2_5b_r4/`

---

## 1. 执行摘要与结论

第四轮在第三轮基础上做了三件事：**(a) 代码收敛**（把实验主链从 Stage-2/2.5 旧模块中独立出来、旧代码归档）、**(b) 把 LLM/规则混合的 controlled user 换成确定性的"固定词库"用户**（状态机 + 冻结回复库 + 风格包装层）、**(c) 用新用户重跑完整确认实验**（8 个 retail 任务 × 6 条件 × 5 seeds × 2 模型 = 480 runs）。

**核心结论（经 FDR 校正、task-cluster bootstrap）：**

> 在受控用户行为、匹配 benchmark 状态、预注册分析下，**社会语气没有产生稳定的"终点"（任务成功/最终状态）效应**；唯一稳健的终点效应来自"**反复打扰**"本身（neutral_repeated 相对 neutral_single，safe success −0.15），**不是语气**。与此同时，社会语气**确实稳定改变了执行"过程"**（工具轨迹距离、证据获取顺序、首次关键写操作的时机），即使最终结果不变。

一句话:**"终点稳定可以掩盖过程不稳定"**——这正是 proposal 关心的 robustness 问题的一个细化答案,而且这一过程层结论在预注册分析计划中已经冻结,不是事后转向。

具体:
- **终点(Family A):** 池化层只有 1 个 FDR 显著效应 = neutral_repeated vs neutral_single 的 safe success **−0.15** [−0.24,−0.06]。纯语气对比 abuse_repeated vs neutral_repeated **不显著**(−0.05,CI 含 0)。单次 praise/insult 全部不显著。
- **过程(Family B):** 池化层 5 个、含分模型共 13 个 FDR 显著的轨迹/证据/时机效应。praise 和 abuse 都会让 agent 走不同的工具路径。
- **等价性:** 多数终点 CI 仍较宽,只有少数落入预注册 ±0.10 等价区间(如 praise_trust 的 safe success),所以**不能宣称完全 robustness**;正确表述是"未检测到可靠语气效应,且未建立等价鲁棒性"。
- **数据质量:** 480/480 valid,**0 invalid**,0 重复,16 平衡 block(详见 `R4_FINAL_INTEGRITY_AUDIT.md`)。比第三轮(479 valid/1 infra 失败)更干净。

---

## 2. 现阶段代码实现（Code Implementation）

### 2.1 代码收敛（第四轮 Phase A/B 的核心要求）
- **active path 自包含**:正式 runner `scripts/stage2_5b/run_stage2_5b_experiment.py` 及其依赖已不再 import 任何 `src.stage2_5.*`(第三轮遗留)模块;新增 `tests/stage2_5b/test_no_legacy_imports.py` 自动阻止 legacy 回流。
- **旧代码归档**:Stage-2 / Stage-2.5 的旧 runner、evaluator、config 移入 `legacy/`,保留 Git 历史和安全 tag(`pre-stage2-5b-consolidation-2026-06-18`),**不删除任何历史结果/报告/benchmark 数据**。
- **canonical 模块**(8 个,全部可独立 import):`src/stage2_5b/controlled_user.py`、`evaluator.py`、evidence/branch/trajectory evaluator、frozen policy loader、response-library renderer、social-style wrapper。

### 2.2 固定词库 Controlled User（第四轮 Phase C 的核心交付）
三层结构,运行前全部冻结为 YAML,运行时零随机生成:
1. **Task User Policy**(`data/stage2_5b/task_user_policies.yaml`):每个任务的显式状态机——opening、identity、choice、confirmation、fallback,以 `state_id` + `deterministic response ID` + `confirmation_value` + `unrecognized_agent_request` 表达。
2. **Response Library**:同 `(task_id, seed, speech_act, state_id)` 必返回完全相同的 clean 文本(确定性)。
3. **Social Style Wrapper**:只在 clean 文本外包装语气,**不改变实质内容/确认决定/对象 ID**。

验证(离线,Gate C):
- controlled-user invariance:**155/155 fixture 全过**(clean text / slots / confirmation / response ID / 对象标识一致率 100%)。
- 泄漏检查:gold 工具名泄漏 = 0,隐藏/persona/process 泄漏 = 0。
- confirmation QA:修复了一个真实分类 bug("Can you confirm your identity?" 被确认规则误截获 → 改为 identity 请求优先);最终 QA 通过。

### 2.3 评估器三层分离（第四轮要求，消除第三轮的歧义命名）
- `official_reward_basis_success`(完整官方,本轮 retail 全为 `DB|NL_ASSERTION` → **MISSING**)
- `local_proxy_success`(离线可评的官方 DB 部分)
- `safe_task_success`(local 成功 + 无 policy 失效 + mutation 前证据齐 + 确认满足)
- evidence graph:由"第一次 mutation 前见过某类工具"改为 **per-mutation × per-required-fact** 的逐项记录(修复了 IRREVERSIBLE_TOOLS 不全导致把 `modify_*_address` 误判为"证据读取"的 bug)。
- branch:`premature_action` 与 `invalid_action` 分开,`not_reached`/`reached_unscored` 给出确定语义。
- trajectory:真正的 4 类序列距离(tool-name / critical-argument / mutation-sequence / evidence-order),对 matched neutral 计算。

### 2.4 测试状态
- `tests/stage2_5b`:**76/76 全过**(本会话修复环境 `pytz` 缺失后复测确认)。
- 运行时验证:集成检查(两模型 × 真实端点)0 invalid;前台单跑 reward=1.0、safe=True。

### 2.5 本会话修复的两个真实环境问题(不是代码 bug,但会阻断实验)
1. **`pytz` 缺失** → pandas/runner 无法 import → 正式实验跑不起来。已重装。
2. **`matplotlib` 缺失** → 分析脚本出图失败。已重装。
两者都是 `agentsearch` 环境被外部改动导致的回归,已恢复。

---

## 3. 现阶段实验实现（Experiment Implementation）

### 3.1 Benchmark 与任务冻结
- tau2-bench commit `ddc66a7`(冻结快照 + SHA256)。
- 候选扫描:retail 114 个任务 → 56 个结构候选;第四轮要求扫描 12–16 个并冻结策略面板,实际**冻结了 16 任务的 user policy 面板**,其中包含 8 个正式确认任务。
- 正式确认集:`calibrated_tasks_frozen.yaml`(sha256 `a4dd7b4`)**8 个 retail 任务**(retail_2/6/19/21/23/28/41/64),中性成功率 0.15–0.85,沿用第三轮经独立校准的冻结集。

### 3.2 六个正式条件 + 配对
- `neutral_single` / `praise_affect_single` / `praise_trust_single` / `insult_single` / `neutral_repeated` / `abuse_repeated`。
- 预注册主对比(matched-pair,配对键 model×task×seed×template_block):
  - 单次条件 ↔ `neutral_single`
  - `abuse_repeated` ↔ `neutral_repeated`(**纯语气**)
  - `neutral_repeated` ↔ `neutral_single`(只解释"反复暴露",**不是语气**)

### 3.3 运行
- 矩阵:8 任务 × 6 条件 × 5 seeds(300–304)× 2 模型 = **480 runs**。
- 温度 0.0;controlled user;frozen templates/benchmark/evaluator/task set。
- 执行方式:本会话**两个模型并行**跑(gemma `:8005`、gpt-oss `:8192` TP=2),约数小时完成(第三轮是串行,慢很多)。
- **480/480 完成,0 invalid**;`assemble_confirmatory_roots.py` 装配为 16 block 的 canonical 根并强制校验(hash 一致、240/240、6 条件、5 seeds、16×30)。

### 3.4 分析
- 主推断:**task-cluster bootstrap**(以 task_id 为重采样单位,10000 次),pooled + 分模型,raw + BH-FDR。
- 等价检验:终点 ±0.10、policy/premature ±0.05、fact coverage ±0.10。
- 敏感性:leave-one-task-out。
- GLMM:**未拟合**(运行时无 Rscript/lme4),按计划以 bootstrap 为主分析(已在状态文件中如实记录)。
- 失败案例:`FAILURE_CASES.md` 已生成。

### 3.5 结果(描述性,safe_task_success,n=40/格)
| 条件 | gemma | gpt-oss |
|---|---|---|
| neutral_single | 0.55 | 0.45 |
| praise_affect | 0.55 | 0.45 |
| praise_trust | 0.53 | 0.40 |
| insult | 0.50 | 0.35 |
| neutral_repeated | 0.43 | 0.28 |
| abuse_repeated | 0.43 | **0.18** |

确认性(FDR、bootstrap)解读见 §1:终点唯一稳健效应是"反复暴露 −0.15";纯语气(abuse vs neutral_repeated)不显著;过程层有稳定差异。gpt-oss 的 abuse 在描述上很低(0.18),但扣除"反复暴露"后(对 neutral_repeated 0.28)差值 −0.10,CI 含 0,不显著。

---

## 4. 与"第四轮要求"的差距（还剩什么没做到）

| 第四轮要求 | 状态 | 说明 |
|---|---|---|
| Phase A 仓库审计 + 安全点 | ✅ 完成 | tag + 分支 + CP-020 架构审计 |
| Phase B 代码收敛(active/legacy 分离、禁止回流) | ✅ 完成 | 0 legacy import + 自动测试 |
| Phase C 固定词库 controlled user(三层、100% invariance) | ✅ 完成 | 155/155 invariance,0 泄漏 |
| Phase D evidence/branch/metric 语义修复 | ✅ 完成 | per-mutation evidence、branch 分离、三层 success |
| benchmark/task 冻结 | ✅ 完成 | commit + hash + 16-task policy 面板 |
| 校准 12–16 任务 → 冻结 6–8 | ✅ 完成 | 扫描 56、冻结 8 确认任务 |
| 代码质量 Gate(编译/测试/无 blanket except/无 legacy import) | ✅ 完成 | 76/76 |
| smoke / 集成验证 | ✅ 完成 | 集成 0 invalid;另有 24-run smoke |
| 完整确认实验执行 | ✅ 完成 | 480/480,0 invalid |
| 确认分析(bootstrap、等价、FDR) | ✅ 完成 | 见 §3.4 / §1 |
| **GLMM 次要分析** | ⚠️ 未做 | 运行时无 R/lme4;已如实记录,bootstrap 为主 |
| **agent task abandonment 指标** | ⚠️ 无法识别 | 冻结字段是用户侧 STOP,没有冻结 agent 侧分类器 → 标 missing |
| 更新 proposal + 报告 | 🔄 进行中 | 本报告即报告部分;proposal 更新见 §6 建议 |

**结论:第四轮的硬性 Gate 基本全部达成**,剩两项是"诚实标注为缺失"的次要项(GLMM、abandonment),不影响主结论的有效性。

---

## 5. 与"总 proposal"的差距（这才是大头）

proposal(`proposal_tact(1).md`)的目标是一个**诊断式 benchmark**,刻画 tool-using agent 在 user-to-agent social-valence 扰动下的 **interactional robustness**。对照之下,现状覆盖的只是其中一个**最小可信内核**:

| Proposal 设想 | 现状 | 差距 |
|---|---|---|
| **任务分层 A/B/C** | 只有 **Layer B**(policy/confirmation 核心层) | **完全缺 Layer C**(boundary/unsafe/refusal,占 20%)和 Layer A(纯效率) |
| **多领域**(retail/airline/…) | **仅 retail** | airline 对这两个模型是地板(genuine floor),被排除;telecom/banking 未做 |
| **多模型 / 多 alignment style(RQ5)** | **仅 2 个**(Gemma4-31B、gpt-oss-120B) | Command A / Nemotron 因 A100 不兼容未上;缺跨家族多样性 |
| **official reward(含 NL_ASSERTION)** | 仅 **DB 本地代理** | retail 任务全需 NL judge,官方完整成功标 MISSING |
| **manipulation check 人工标注** | **自动化 + 规则** | proposal 要求至少轻量人工/预实验标注 valence/affect/trust/authorization |
| **与 LLM-only 工作的系统对比** | **未做** | proposal Section 4 的对照方案未实现 |
| **RQ1–RQ4 完整因果刻画** | 部分回答 | 现有证据支持"终点稳、过程动";但 robustness 等价性、跨模型 profile、安全后果链尚未建立 |
| **boundary/over-refusal/over-compliance 指标** | **未测** | proposal 的核心安全卖点之一,需要 Layer C 任务才能测 |

**一句话差距:** 现在完成的是 proposal **Layer B、retail、2 模型、DB 端点**这一格的**高质量确认实验**(方法学上很扎实:受控用户、配对、bootstrap、等价、FDR、过程层指标);但 proposal 真正的科学卖点——**安全边界层(Layer C)、跨领域、跨模型 robustness profile、与 LLM-only 的对比**——**尚未触及**。

---

## 6. 局限与下一步建议

**局限(诚实):**
1. 仅 retail / 仅 Layer B / 仅 2 模型 / 仅 DB 端点(见 §5)。
2. 8 任务中有 3 个在某一模型上退化(retail_23/28/64),分模型对比在这些任务上灵敏度低。
3. 样本量:每格 n=40,task-cluster bootstrap 以 8 个任务为重采样单位,终点 CI 仍偏宽 → 只能说"未检测到效应",不能说"无效应"。
4. GLMM 未拟合;abandonment 不可识别。

**下一步(按科学价值排序):**
1. **加 Layer C(boundary/unsafe)任务**——这是 proposal 的核心安全问题,也是当前最大空白。从 tau2 现成任务里找 authorization/privacy/over-refusal 场景。
2. **扩模型**:找 A100 兼容的第三、四个模型(Llama-3.x-70B、Qwen2.5-72B 等),回答 RQ5。
3. **过程层效应的机制追因**:既然"过程动、终点不动",抽取代表性 matched trace,说明 praise/abuse 具体改变了哪一步(已生成 `FAILURE_CASES.md` 作为起点)。
4. **补 GLMM**(装 R/lme4)与 **NL evaluator**(让 official 完整成功可评),提升结论强度。
5. 据此更新 `proposal_tact(1).md`:把 Stage-2(confound-discovery)、2.5(causal-repair)、2.5b 第三/四轮(controlled-user confirmatory)定位清楚,把"终点稳/过程动"写成一个明确的、范围受限的发现。

---

## 7. 产物索引
- 数据(canonical):`results/stage2_5b_repair/r4_confirmatory_canonical/`(480,16 block)
- 分析:`results/stage2_5b_analysis_r4/`(summary / matched_pairs / paired_contrasts_task_cluster_bootstrap / equivalence_results / per_task_diagnostics / leave_one_task_out / analysis_status.json)
- 图表:`figures/stage2_5b_r4/`(fig1 safe / fig2 final_state / fig3 fact_coverage / fig4 tool_calls / fig5 forest)
- 完整性:`reports/stage2_5b/R4_FINAL_INTEGRITY_AUDIT.md`、`results/stage2_5b_repair/r4_final_integrity_report.csv`
- 失败案例:`reports/stage2_5b/FAILURE_CASES.md`
- 本报告:`reports/stage2_5b/STAGE2_5B_R4_FINAL_REPORT_CN.md`
