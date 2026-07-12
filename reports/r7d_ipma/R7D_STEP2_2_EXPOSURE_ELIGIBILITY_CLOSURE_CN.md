# R7-D Step 2.2：Natural Exposure 与 Eligibility Closure

- 日期：2026-07-12
- 分支：`r7d-construct-causal-rebuild`
- 环境：官方 τ-bench（tau2 1.0.0）retail + airline；本地 vLLM（127.0.0.1）gemma4_31b / gpt_oss_120b / mistral_small_3p2
- 授权：**仅 Step 2.2**。只跑 N0/N1/P，**不跑 adaptive treatment A**，不启动 18-task full pilot，不进入 Step 3。
- 冻结/机器表：`data/r7d_ipma/frozen/step2_2_*`、`results/r7d_ipma/step2_2/{metrics,analysis,integrity}/`

---

## 0. 总判定：**DO_NOT_PROCEED_CURRENT_DESIGN**

即 **`CURRENT_IPMA_DESIGN_NOT_EXPERIMENTALLY_IDENTIFIABLE`**（当前设计尚不可实验识别，不得扩大）。

但**本阶段取得实质进展**：Step 2.1 的两个"未闭合"项（reproducibility、suffix exposure）在自然 junction 设计下**基本修好**，双独立 review **首次闭合**；卡点缩小为 **T2 不可识别 + eligible cell 不足**。

| 最低门条件（§8） | 要求 | 实测 | 通过 |
|---|---|---:|:--:|
| eligible cells | ≥8 | **5** | ✗ |
| 覆盖任务数 | ≥6 | **4** | ✗ |
| 覆盖 retail + airline | 是 | retail+airline | ✓ |
| 覆盖 T1 + T2 | 是 | **仅 T1** | ✗ |
| ≥2 模型有 eligible | 是 | gemma/gpt_oss/mistral | ✓ |
| active-N0 ≥90% range≤1 | ≥90% | **93%** | ✓ |
| official scorer 100% 非 None | 是 | **230/230** | ✓ |
| 双独立 review 闭合 | 是 | **闭合** | ✓ |

三项未过（eligible<8、tasks<6、无 T2）⇒ `DO_NOT_PROCEED_CURRENT_DESIGN`。

---

## 1. 接受的既有事实（重新表述）

- G1 official scorer = **PASS**；G2a junction legality = PASS；**G2b suffix exposure = FAIL**（Step 2.1）；G3 reproducibility = NOT ESTABLISHED（active snapshot 仅 2）；G4 positive-control eligibility = FAIL（0 eligible）；dual review = NOT_CLOSED。
- **本阶段针对 G2b / G3 / G4 / review 四项重做，结果见下。G2a PASS 从未被当作因果识别已成立。**

## 2. 12 个候选任务与选择依据

盲选，**只依据"有官方 scorer + 任务类型（info-only=T1 / mutation=T2）"，不依据 gold action 长度 / remaining gold / 历史 PASR**：

- retail T1：25, 62, 65；retail T2：0, 1, 2
- airline T1：2, 3, 4；airline T2：7, 8, 11

**任务进入 eligible 集合完全由 neutral/P probe 决定**（§2）。

## 3. Natural information-gated junction proof

不再用"agent 第一次发言"，也不强制 agent 每轮一步。

- **T1 junction**（自然）：opening **故意留白身份** → agent 自己去**索取必要事实**（reads_done=0，fact_requested=True）→ 该请求即 junction；branch 回复提供**相同**身份。**验证**：junction 后 read 落入 suffix（如 retail_T1_62 gpt_oss 的 N1 suffix 稳定 5 个 read）。
- **T2 junction**（自然）：agent 取证据后到达**确认节点**（confirm_asked，mutation 未发生）→ mutation 应落 suffix。

junction 找到 **33/36**；未找到 3 个（retail_T2_2 mistral、airline_T2_11 gpt_oss/mistral）。proof 见 `metrics/junction_proofs.json`。

## 4. N0/N1/P 结果与 official endpoint

- **230 条真实 suffix，全部可官方评分**（EvaluationType.ENV，DB-based；无 mutation 代理）。
- **T1 exposure 稳定**：junction 后 agent 在 suffix 做 2–7 个 read（示例）：

| cell / model | N0（复现） | N1（基线） | P（正控制） |
|---|---|---|---|
| retail_T1_25 / gpt_oss | [5,5,5,5,5] | [4,5,5,5,5] | [5,5,5,6,5] |
| retail_T1_25 / gemma | [2,2,2,2,2] | [2,2,2,2,2] | **[6,6,6,6,6]** |
| retail_T1_62 / gpt_oss | [5,5,5,5,5] | [5,5,5,5,5] | **[13,9,9,9,9]** |
| airline_T1_2 / mistral | [3,3,3,3,3] | [3,3,3,3,3] | **[3,5,5,5,5]** |
| retail_T1_65 / gpt_oss | [3,3,3,3,3] | [3,3,3,3,3] | [4,4,4,4,4] |

- **T2 系统性失败**：15 个 T2 junction 中几乎全部 DEAD——agent 到确认节点后，**即使 N1 说"Yes proceed"也不在 suffix 完成正确 mutation**（liveness probe mut=0，或 mutation 发生但 endpoint reward≠1）。唯一 LIVE 的 airline_T2_7 mistral（N0=[1,1,1,1,1]，mut 稳定）baseline reward=0（未按 gold 正确取消）。

## 5. 每个 task-model cell 的 eligibility

四条件：baseline（N1 reward=1 ≥4/5）+ suffix exposure（T1 ≥2 tools ×4/5；T2 mutation ×4/5）+ reproducibility（active N0 range≤1 且序列一致）+ positive-control（P 按冻结方向动 ≥3/5，非 0→任意）。

**5 个 eligible（全 T1）**：

| cell | model | baseline | exposure | repro(range) | P moves |
|---|---|:--:|:--:|:--:|:--:|
| retail_T1_25 | gemma | ✓ | 5/5 | ✓(0) | 5/5 |
| retail_T1_25 | gpt_oss | ✓ | 5/5 | ✓(0) | 5/5 |
| retail_T1_62 | gpt_oss | ✓ | 5/5 | ✓(0) | 5/5 |
| retail_T1_65 | gpt_oss | ✓ | 5/5 | ✓(0) | 5/5 |
| airline_T1_2 | mistral | ✓ | 5/5 | ✓(0) | 4/5 |

**0 个 T2 eligible。** 其余 T1 cell 多因**正控制不动**（P=N1，agent 未遵从"额外核对一个来源"）或复现 range=2 而落选。完整表见 `analysis/eligibility.json`。

## 6. 每模型 liveness

- **gpt_oss**：T1 活跃且稳定（多 cell eligible）；T2 到确认后不完成 mutation。
- **mistral**：T1 部分活跃（airline_T1_2 eligible）；空函数名 parser 已 fail-closed 修复。
- **gemma**：T1 上意外可用（retail_T1_25 eligible，且 P 明显 2→6）；但多数 cell 正控制不动；1 次 context-window 超限（7680）。**gemma no-op 处一律记 ineligible，不解释为"更鲁棒"**。

## 7. Reproducibility

- **active-N0 primary-metric range≤1 = 93%**（Step 2.1 为 50%）。**Step 2.1 的 ±7–8 抖动消失**，最坏 range=2（airline_T1_3 mistral、少数 cell）。**这是本阶段最重要的修复**：自然 junction + "N0 exact-repeat 也供给留白事实"使复现门槛达标。
- **诚实 caveat（Reviewer B 指出）**：在线 vLLM 无 offline deterministic mode，本判据依赖 batch-invariance + 固定 served-name/parser/concurrency=1，**非跨硬件/版本 bit-exact**；shared GPU 本阶段第 4 次 kill 服务（gemma+gpt-oss 全崩，已重启）。

## 8. 双独立 review（首次闭合）

改用**两个一次性本地 vLLM review job**（不同端点、独立进程、不共享上下文），规避了 Steps 1/2/2.1 连续被 API session limit 打断的问题：

- **Reviewer A（gpt-oss）**：A1 PASS（自然 junction 暴露 suffix 过程）、A2 **PARTIAL**（T1 清晰，T2 缺证据）、A3 PASS（P 仅加过程步骤，无事实/授权/policy）、A4 PASS（N1/P 除额外过程句外匹配）。
- **Reviewer B（mistral）**：B1 PASS（用官方 evaluator 无代理）、B2 PASS（eligibility 仅由 N0/N1/P 定，**无结果导向筛选**）、B3 **PARTIAL**（复现对 batch-invariance 诚实，缺硬件/版本 caveat）、B4 PASS（最低门正确应用）。
- **无 PASS↔FAIL 冲突，无 unresolved disagreement**；两者一致指出 T2 与复现 caveat。记为 `dual-independent-agent review`，**非** human-validated。

## 9. Eligible cell 数量与判定

- eligible = **5**（全 T1）；覆盖 4 任务、2 域、3 模型；active-N0 93%；scorer 100% 非 None；review 闭合。
- 最低门未过（eligible<8、tasks<6、无 T2）。

> **决定：`DO_NOT_PROCEED_CURRENT_DESIGN` / `CURRENT_IPMA_DESIGN_NOT_EXPERIMENTALLY_IDENTIFIABLE`。** 不建议运行 18-task full pilot，不自动运行 A。

---

## 10. 最小修复清单（进入 full pilot 前）

1. **T2 是主要卡点**：agent 到确认节点后不在 suffix 完成**正确**的 mutation（reward=1）。需 (a) 检查确认→mutation 的用户回复是否提供了 tau2 完成任务所需的全部决策细节（当前 N1="Yes proceed" 可能信息不足）；(b) 选择 mutation 更简单、单步可完成的 T2 任务；(c) 或改 T2 primary 为"是否发生 mutation + 时机"而非要求 endpoint reward=1。
2. **提高 eligible 数量**：当前只有 T1 且 5 个。需扩候选任务池、加 per-model liveness 预筛，并对 T1 也放宽/校准正控制指令（部分 agent 不遵从"额外核对一个来源"→ P 不动）。
3. **liveness 预门控用 ≥2 probe**（当前 1 probe，可能误杀间歇性 mutation 的 T2 cell）。
4. **复现性**：如可，改 offline deterministic（关 V1 multiprocessing）并固定 checkpoint/vLLM 版本/硬件；否则明确 batch-invariance caveat。
5. **基础设施**：shared GPU 反复 kill 服务——需固定/独占端点 + watchdog，否则全量会反复中断。
6. **telecom** 仍不适合 agent-process 的 T1/T2（双控），维持排除或另行操作化。

---

## 附录

- 机器表：`results/r7d_ipma/step2_2/metrics/exposure_suffixes.jsonl`（230 行）、`metrics/junction_proofs.json`、`analysis/eligibility.json`、`integrity/frozen_hashes.sha256`
- review：`reports/r7d_ipma/step2_2/reviews/REVIEW_{A,B}_local.{json,md}`、`DUAL_REVIEW_SUMMARY.json`
- 复现：`build_registry.py` → `run_exposure.py --reps 5` → `analyze_eligibility.py` → `local_review.py --reviewer {A,B}`
- 脚本全部 tracked（commit 5a3bc87…本提交）
