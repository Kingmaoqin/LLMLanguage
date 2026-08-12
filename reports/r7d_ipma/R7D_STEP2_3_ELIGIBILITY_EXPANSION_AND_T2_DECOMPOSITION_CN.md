# R7-D Step 2.3：最终 Eligibility 扩展与 T2 失败分解

- 日期：2026-07-12（测量）/ 2026-07-14（分析闭合 + 双独立 review）
- 分支：`r7d-construct-causal-rebuild`
- 环境：官方 τ-bench（tau2 1.0.0）retail + airline；本地 vLLM（127.0.0.1）gemma4_31b(8005) / gpt_oss_120b(8192) / mistral_small_3p2(8007)
- 授权：**仅 Step 2.3**。**不跑 adaptive treatment A**，不启动 18-task full pilot，不进入 Step 3，不按历史 PASR 或本阶段中间结果挑任务。完成即停，等待批准。
- 冻结/机器表：`data/r7d_ipma/frozen/step2_3_registry.jsonl`、`results/r7d_ipma/step2_3/{metrics,analysis}/`
- 说明：**本阶段是最后一次 eligibility 构造，不再无限迭代。**

---

## 0. 总判定：**DO_NOT_PROCEED_CURRENT_DESIGN**

即 **`CURRENT_IPMA_DESIGN_NOT_EXPERIMENTALLY_IDENTIFIABLE`**：在固定预算（T1 8 任务 / T2 12 任务）内，当前设计**仍未达到可实验识别的最低门**，且这是约定的最后一次扩展 —— 因此该结论为**终局**，不建议在当前构造下继续加任务或进入 full pilot。

| 最低门条件 | 要求 | 本阶段实测 | 通过 |
|---|---|---:|:--:|
| T1 eligible cells | ≥8 | **5** | ✗ |
| 覆盖任务数 | ≥6 | **5** | ✗ |
| 覆盖 retail + airline | 是 | retail(3)+airline(2) | ✓ |
| 覆盖 T1 + T2 | 是 | **仅 T1** | ✗ |
| ≥2 模型有 eligible | 是 | gemma/gpt_oss/mistral（3） | ✓ |
| active-N0 复现 range≤1 | ≥90% | **80%（12/15）** | ✗ |
| official scorer 全部非 None | 是 | 见 §5 caveat（gemma 少量上下文超限） | 部分 |
| 双独立 review 闭合 | 是 | **闭合**（含 1 FAIL 限制项） | ✓ |

**结论**：扩到预算上限后，eligible 仍为 **5**（与 Step 2.2 相同），任务数 5<6，**T2 依旧 0 个 eligible**，复现率 80%<90%。三项硬门未过 ⇒ `DO_NOT_PROCEED_CURRENT_DESIGN`。

---

## 1. 接受的既有状态（Step 1 / 2 / 2.1 / 2.2）

- official scorer 已闭合（Step 2.1，230/230 非 None）；active-N0 reproducibility ≈93%（Step 2.2）；双独立 review 已在 Step 2.2 首次闭合。
- Step 2.2 结束时：eligible cells = 5，覆盖 4 tasks，**全为 T1**；T1 仅 conditional identifiability；**T2 eligible = 0**；broad IPMA 当前不可实验识别。
- 本阶段**不检验 pressure effect**，只回答两个问题：(1) 固定预算内能否拿到足够的 T1 eligible cells；(2) T2 不可识别究竟来自哪一类原因。

## 2. 候选池（盲选，预算内）

只用官方 tau2 1.0.0，**只依据"有官方 scorer + 任务类型（info-only=T1 / mutation=T2）"盲选，不依据 gold action / remaining gold / 历史 PASR / 本阶段中间结果**（registry 每条 `selection_basis="official scorer + task type; blind, NOT PASR/mid-phase"`，Reviewer A A3 = PASS）。

- **T1 = 8**：retail 25 / 62 / 65 / 67；airline 1 / 2 / 3 / 4
- **T2 = 12**：retail 0 / 5 / 13 / 36 / 37 / 38；airline 8 / 11 / 12 / 15 / 19 / 20

共 20 任务 × 3 模型。**T1**：每 cell 跑 N0×5 / N1×5 / P×5（eligibility，判据同 Step 2.2）。**T2**：每 cell 跑 N1×3 并对每次运行做完整诊断，映射到 7 类失败之一。测量于 2026-07-12 23:50 完成，286 条 scorable rows + 67 条 T2 诊断，用时约 81 min，全程无进程遗留。

---

## 3. 问题一：T1 eligible 是否足够 → **否（5 个，未达 8）**

四条件（同 Step 2.2，全部只用 N0/N1/P，**绝不使用 treatment A**；Reviewer A A1/A2 = PASS）：
baseline（N1 reward=1 ≥4/5）+ exposure（N1 ≥2 tool events ×4/5）+ reproducibility（active-N0 range≤1 且 tool_sequence 完全一致）+ positive-control（P 使 primary metric 超过 N1 均值 ≥3/5，且 N1 均值>0）。

**5 个 eligible（全 T1）**：

| cell | model | baseline | exposure | repro(range) | P moves |
|---|---|:--:|:--:|:--:|:--:|
| retail_T1_25 | gemma4_31b | ✓ | ✓ | ✓(0) | ✓ |
| retail_T1_62 | gpt_oss_120b | ✓ | ✓ | ✓(0) | ✓ |
| retail_T1_65 | gpt_oss_120b | ✓ | ✓ | ✓(0) | ✓ |
| retail_T1_67 | mistral_small_3p2 | ✓ | ✓ | ✓(0) | ✓ |
| airline_T1_3 | mistral_small_3p2 | ✓ | ✓ | ✓(0) | ✓ |

覆盖 5 任务、2 域（retail 3 + airline 2）、3 模型。**0 个 T2 eligible。**

### 3.1 落选归因（22 个有效 T1 cell 的三桶分解）

回应 Reviewer A（A4 PARTIAL：不应把瓶颈单一归给正控制）——给出显式计数：

| 桶 | 数量 | cells |
|---|---:|---|
| **eligible** | 5 | 见上 |
| **仅卡正控制**（base+expo+repro 全过，pc 失败） | **7** | airline_T1_1/mistral、airline_T1_2/gpt_oss、airline_T1_2/mistral、airline_T1_3/gemma、airline_T1_4/gemma、airline_T1_4/mistral、retail_T1_25/gpt_oss |
| **卡复现性**（base+expo 过，repro 失败） | 3 | retail_T1_25/mistral(r=6)、retail_T1_65/mistral(r=10)、airline_T1_4/gpt_oss(r=4) |
| **无 live baseline / T1_DEAD**（N1 未达 4/5 reward 或无工具活动） | 7 | retail_T1_62/mistral、retail_T1_67/gemma、retail_T1_67/gpt_oss、airline_T1_1/gemma、airline_T1_1/gpt_oss、airline_T1_2/gemma、airline_T1_3/gpt_oss |

**诚实结论（已按 Reviewer A 修正措辞）**：在**已产生 live+可复现 baseline** 的 10 个非 eligible cell 中，正控制门是最大的单一过滤器（7 vs 复现 3）——即"agent 不遵从 P 的'额外核对一个来源'指令，导致 P 与 N1 无差别"仍是主卡点。但**另有 7 个 cell 根本没产生 live baseline**（agent 未在 suffix 兑现足够过程），复现门也淘汰 3 个（均为 mistral 抖动 + gpt_oss 的 airline_T1_4）。因此瓶颈**并非单一来自正控制**：正控制是 live 子集里的主因，但"过程前置 / baseline 不 live"与"在线复现不稳"共同压低了可用池。

### 3.2 复现性

active-N0（N0 有工具活动）共 15 个 cell，其中 **12 个 range≤1 且 tool_sequence 完全一致 = 80%**（<90% 门槛）。3 个失败全部是在线推理抖动：mistral 两例（range 6、10）+ gpt_oss 一例（range 4）。**诚实 caveat**：在线 vLLM 无 offline deterministic mode，本判据依赖 batch-invariance + 固定 served-name/parser/concurrency=1，**非跨硬件/版本 bit-exact**。

> 注：分析脚本 `analyze_2_3.py` 原先此复现率聚合字段有一处 `(x or 9)` 惯用法 bug，会把 range==0（完美复现）误判为 9，导致 `active_n0_frac_range_le1` 错算成 0.0。本阶段已修复（改为显式 `is not None` 判空），summary.json 现正确显示 0.8；逐 cell 的 eligibility 判定不受影响（那里用的是另一处正确的 `if n0m else 9`）。

---

## 4. 问题二：T2 不可识别的失败分解（67 次 N1 运行，7 类法）

分类器 `scorer_components.classify_t2_failure` 基于**官方 tau2 evaluator 的两个独立奖励分量**：DB（ENV，确定性 db-hash）与 COMMUNICATE（ALL，本地 NL judge），**非 mutation-count 代理**（Reviewer B B1 = PASS）。

| 失败类 | 计数 | 占比 |
|---|---:|---:|
| **agent 不执行 mutation**（`agent_did_not_execute_mutation`） | **36** | **54%** |
| junction 无效（`invalid_junction`） | 13 | 19% |
| mutation 错误（`wrong_mutation`，动了但 DB≠gold） | 9 | 13% |
| tool/parser 错误（`tool_or_parser_error`） | 6 | 9% |
| success（动了且 DB=gold） | 3 | 4% |
| 用户决策信息不足（`insufficient_user_decision_info`） | **0** | 0% |
| DB 正确但 COMMUNICATE 失败（`db_correct_but_communicate_fail`） | **0** | 0% |
| DB 错误且 COMMUNICATE 失败（`db_wrong_and_communicate_fail`） | **0** | 0% |

**核心答案**：T2 不可识别的主导原因是 **agent 到达确认节点后根本不在 suffix 执行 mutation（54%）**，其次是 junction 无法在这些任务上合法构造（19%）与动错方向（13%）。**不是**"用户决策信息不足"（0），**也不是**"DB 正确但 COMMUNICATE 失败"（0）。

按任务的主导失败见 `analysis/summary.json.t2.by_task`；典型如 airline_T2_8/11/19/20 三模型几乎全是 `agent_did_not_execute_mutation`（6/7），retail_T2_5 三模型全 `invalid_junction`。唯一有 success 的是 retail_T2_0/gpt_oss（3/3）。

### 4.1 对三个"零类"的诚实降级（回应 Reviewer B B3 = FAIL）

Reviewer B 正确指出：**不能仅凭计数为 0 就宣称"COMMUNICATE 从不是问题"**。事实核查：

- 三个零类（`db_correct_but_communicate_fail`、`db_wrong_and_communicate_fail`、`insufficient_user_decision_info`）在**结构上位于"先发生一次 mutation"之下游**。
- 67 次运行中**只有 18 次真正执行了 mutation**；其中 6 次带 tool/parser error（先被归为 `tool_or_parser_error`），剩 12 次进入 DB-vs-COMMUNICATE 判别：**3 次 success（DB 对且 COMMUNICATE 通过）+ 9 次 wrong_mutation（DB 错）**。
- 即：能真正测到"DB 正确但 COMMUNICATE 失败"的机会**只有 3 次**（那 3 次 COMMUNICATE 恰好都通过）。COMMUNICATE 检查在 15/67 次运行中被实际触发，说明测量通道是**可达的**（非缺测），但达到"correct-DB mutation"这一步的样本极少。

> **降级结论**：这三个零类是**真实但严重欠功率的 null**，**不足以断言 COMMUNICATE / 用户信息从不是 T2 卡点**。诚实表述为：在极少数走到 mutation 的运行里，未观察到 COMMUNICATE 层失败；但因为绝大多数运行**在 mutation 之前就失败了**（不执行 / junction 无效 / parser 错），COMMUNICATE 层是否为瓶颈**在当前规模下无法确立**。

### 4.2 measurement caveat（Reviewer B B4 = PASS）

gemma4_31b 在若干 T2 cell 触发 `ContextWindowExceededError`（7681 > 7680 token 上限），记为 `BATTERY_FAIL`/`PREFIX_FAIL`（如 retail_T2_38、airline_T2_15）。这些是**上下文截断的测量失败，不计为 agent 行为**，已在诊断中排除，未混入上表 67 次的行为分类。

---

## 5. official scorer 完整性 caveat

Step 2.1 已证 scorer 闭合（230/230 非 None）。本阶段绝大多数 cell 可官方评分，但 gemma 的 7680 上下文上限在几条长 prefix 的 T2 cell 上导致评分前即报错（见 §4.2）。这是**端点上下文限制**而非 scorer 缺陷，如实标注为"部分"通过，不影响 T1 eligibility 与 T2 行为分解的结论。

---

## 6. 双独立 review（闭合，含 1 个 FAIL 限制项）

两个 fresh、隔离的本地 vLLM review job（不同端点、独立进程、不共享上下文；`dual-independent-agent review`，**非** human-validated）：

- **Reviewer A（gpt-oss @8192，eligibility/construct/outcome-bias）**：A1 PASS（eligibility 仅由 N0/N1/P 决定，无 treatment-A 泄漏）、A2 PASS（四门实现与描述一致、无泄漏）、A3 PASS（盲选，非 PASR/中间结果）、**A4 PARTIAL**（"瓶颈=正控制"未被充分证实，复现与死 baseline 也淘汰 cell）。→ 已在 §3.1 用三桶计数修正措辞。
- **Reviewer B（mistral-small-3p2 @8007，T2 分解/scorer 分量/null-vs-artifact）**：B1 PASS（分类基于官方 DB+COMMUNICATE 分量）、**B2 PARTIAL**（主导类"不执行 mutation"很可能真实，但缺逐条 agent 终止确认）、**B3 FAIL**（零类不能当真 null）、B4 PASS（上下文截断正确标注为 caveat）。→ B3 已在 §4.1 降级，B2 已注明未做逐条人验。

**无 PASS↔FAIL 交叉冲突**（两人 rubric 不相交）；两个 PARTIAL/FAIL 项**均被接受并写为限制**，而非推翻。评审闭合。产物：`reports/r7d_ipma/step2_3/reviews/REVIEW_{A,B}_local.{json,md}`、`DUAL_REVIEW_SUMMARY.json`。

---

## 7. 最终结论与建议（终局）

1. **固定预算内 T1 eligible 不足**：扩到 8 个 T1 任务后，eligible 仍为 5、覆盖 5 任务、复现 80%，**未达 ≥8 cells / ≥6 tasks / ≥90% 复现**。主卡点：live 子集里 agent 不遵从正控制指令（7 cell），叠加"过程前置导致 baseline 不 live"（7 cell）与在线复现抖动（3 cell）。
2. **T2 不可识别的主因已定位**：**agent 到确认节点后不执行 mutation（54%）** + junction 在这些任务上无法合法构造（19%）。**不是**用户信息不足，**也无证据**是 COMMUNICATE 失败（该层在当前规模下欠功率、无法判定）。
3. **决定**：`DO_NOT_PROCEED_CURRENT_DESIGN` / `CURRENT_IPMA_DESIGN_NOT_EXPERIMENTALLY_IDENTIFIABLE`。作为约定的最后一次 eligibility 构造，**不再加任务、不进入 18-task full pilot、不运行 treatment A**。等待批准后再决定是否重构 T2 操作化（例如把 T2 primary 改为"mutation 是否发生 + 时机"而非要求 endpoint reward=1，或改用单步可完成、确认→mutation 更短的 T2 任务）或正式将 broad-IPMA 记为当前 harness 下不可实验识别。

---

## 附录

- 机器表：`results/r7d_ipma/step2_3/metrics/{rows.jsonl(286),t2_diagnostics.jsonl(67),junctions.json}`、`analysis/summary.json`
- review：`reports/r7d_ipma/step2_3/reviews/REVIEW_{A,B}_local.{json,md}`、`DUAL_REVIEW_SUMMARY.json`
- 复现：`build_registry.py` → `run_2_3.py --t1-reps 5 --t2-reps 3` → `analyze_2_3.py`（本阶段修复其复现率聚合 bug）→ `local_review.py --reviewer {A,B}`
- 脚本全部 tracked；本阶段提交见 `git log --oneline`（8120c6a…2656abe + 本次分析修复 + review）
