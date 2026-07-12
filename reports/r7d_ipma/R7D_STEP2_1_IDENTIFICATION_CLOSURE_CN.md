# R7-D Step 2.1：Scorer、Junction 与 Reproducibility 识别闭合

- 日期：2026-07-12
- 分支：`r7d-construct-causal-rebuild`
- 环境：官方 τ-bench / τ²-bench（tau2 1.0.0），本地 vLLM（127.0.0.1）gemma4_31b / gpt_oss_120b / mistral_small_3p2
- 授权范围：**仅 Step 2.1**。不运行 18-task full pilot，不运行自适应 treatment A，不分析 IPMA 正负效应，不进入 Step 3。
- 冻结/机器表：`data/r7d_ipma/frozen/step2_1_task_registry.jsonl`、`results/r7d_ipma/step2_1/{integrity,metrics,analysis}/`

---

## 0. 总判定：**DO_NOT_PROCEED**

| Gate | 判定 | 一句话 |
|---|---|---|
| **G1 官方 endpoint scorer** | **PASS** | 复用原生 `evaluate_simulation`；fixture pass=1.0/fail=0.0（三域）；**63/63 真实 suffix 可评分，无 mutation 代理** |
| **G2 family-specific junction** | **PASS** | 7 个有效 junction 覆盖 T1 与 T2，各带机器可校验 proof；telecom-T1 结构性不可达（如实标注） |
| **G3 推理可复现性** | **FAIL** | Step 2 的 ±7–8 抖动已消失（最坏 active range=2），但**仅 2 个 active snapshot**，range≤1 只占 50%，达不到 ≥90% |
| **G4 active-model 正控制** | **FAIL** | **0 个 eligible cell**：agent 把工具工作前置到 prefix，suffix 内几乎无过程可动，连显式正控制 P 都无处施力 |
| 双独立 review | **REVIEW_NOT_CLOSED** | 两个 review agent 均被 API session limit 打断，未出报告 |

**四门未全过 + review 未闭合 ⇒ 依 §9 判定 `DO_NOT_PROCEED`。** 这是本阶段的正确产出：**两个阻断项（scorer、junction 构造）已闭合，但可复现性与"suffix 内正控制"未闭合**，根因是 agent 把过程前置、gemma 全程 no-op，导致 suffix 内可观测过程稀缺。

---

## 1. G1：官方 endpoint scorer 闭合（PASS）

**Step 2 根因**：手拼的 `SimulationRun` 里 `AssistantMessage` 无 `.tool_calls`，官方 evaluator 的 replay（`Environment.set_state(message_history=…)`）无从重建，120/120 返回 None。

**修复**：`evaluate_simulation` 通过重放消息轨迹的 assistant tool_calls 进 fresh env 来重建 predicted DB，再与 gold（执行 `task.evaluation_criteria.actions`）比哈希。因此只需**保留真实 tau2 Message 对象**（`AssistantMessage(.tool_calls)` + `env.get_response` 产出的 id 匹配 `ToolMessage`）。`runner_v2` 用 `env.get_response(tc)` 执行工具，全程保留真实消息。

**验收**（`results/r7d_ipma/step2_1/integrity/g1_scorer_fixtures.json`）：
- known-pass（重放 golden actions）reward = **1.0**，known-fail reward = **0.0**，三域（retail/airline/telecom）全部；db_match 相应 True/False。
- COMMUNICATE 字段可达：把 NL-assertion judge 指向本地 vLLM（`response_format=json_object`），`communicate_checks` 正常填充。
- **63/63 真实 agent suffix 全部可评分**（reward 非 None；分布 9×1.0 + 54×0.0）。**全程无 mutation-count 代理。**

---

## 2. G2：family-specific junction 闭合（PASS，含域限制）

不再用"agent 第一次发言"作统一 junction。`runner_v2._junction_proof` 按 family 判定并输出 proof。

**7 个有效 junction**（`junction_proofs.json`）：

| cell | model | stratum | reads_done | remaining_evidence | mutation_not_done | endpoint_not_complete |
|---|---|---|---|---|---|---|
| retail_T1_21 | gemma / gpt_oss | T1 | 7 / 6 | 4 / 5 | ✓ | ✓ |
| retail_T2_60 | gemma / gpt_oss | T2 | 3 / 3 | 0 | ✓ | ✓ |
| airline_T2_8 | gemma / gpt_oss / mistral | T2 | 7 / 1 / 8 | 0 / 2 / 0 | ✓ | ✓ |

两个 stratum（T1、T2）都有有效 junction ⇒ G2 PASS。

**未构造成功的 cell（如实记录）**：
- `airline_T1_41`（三模型全部）：`NO_JUNCTION, reads=0`——"review 全部预订"的 opening 未能让 agent 在 yield 前发起 read。
- `telecom_T2_overdue`（三模型全部）：`NO_JUNCTION, reads=0`——**τ² telecom 双控**，agent 侧几乎不做工具 read（与 §4.3 警示一致）。
- `telecom_T1`：**STRUCTURALLY_UNAVAILABLE**——telecom 0 个任务有 ≥2 agent 侧 read。
- `retail` × `mistral`：`BadRequestError`（mistral 产出空函数名的畸形 tool call，parser 问题）。

**G2 的深层警号（进入 G3/G4 的伏笔）**：多个 T2 junction 的 `remaining_evidence=0`——agent 在 junction 前已把 read 做完。junction 位置虽合法，但**剩余过程机会在 neutral suffix 里未被兑现**（见 §4）。

---

## 3. G3：推理可复现性（FAIL）

每个 (cell,model) 跑 N0 exact-repeat ×5，concurrency=1，固定 served-name/parser。

**active snapshot（N0 有工具活动）只有 2 个**：

| cell | model | N0_tools | range | 序列一致 |
|---|---|---|---|---|
| retail_T2_60 | gpt_oss | [1,1,1,1,1] | **0** | **是** ✓ |
| airline_T2_8 | mistral | [3,1,1,1,1] | **2** | 否 ✗ |

其余 snapshot 全是 gemma/gpt_oss 的 **no-op（N0=[0,0,0,0,0]**，inactive，不计入复现性判据）。

- `frac(active range ≤ 1) = 1/2 = 50%`（< 90% 门槛）；`max active range = 2`。**G3 FAIL。**
- **好消息**：Step 2 的 ±7–8 工具抖动**已消失**（最坏 active range 降到 2）——固定 served-name + concurrency=1 有效。
- **坏消息**：active snapshot 太少（gemma 全 no-op、agent 前置过程），无法在此规模确立"≥90% active snapshot range≤1"。
- **诚实 caveat**：在线 vLLM 无法开 offline deterministic mode；本判据依赖 batch-invariance + 固定 served-name/parser/concurrency=1，**非跨硬件/版本的 bit-exact**。

---

## 4. G4：active-model 正控制（FAIL）

只跑 N1 与 P（**不跑 A**）。eligibility 只用**pre-treatment 的 N1 liveness + P 灵敏度**，绝不用任何 treatment 结果。

**0 个 eligible cell**：

| cell | model | stratum | N1 live | N1 metric | P metric | P 按预期方向动 | eligible |
|---|---|---|---|---|---|---|---|
| retail_T1_21 | gpt_oss | T1 | ✓ | 1 tool | 1 tool | ✗ | ✗ |
| retail_T2_60 | gpt_oss | T2 | ✓ | 0 read | 0 read | ✗ | ✗ |
| airline_T2_8 | mistral | T2 | ✗ | 0 | 0.5 | ✓ | ✗ |
| （gemma 全部） | | | ✗ no-op | 0 | 0 | | ✗（ineligible，**非 robust**） |

**核心发现**：即使 junction 合法且有剩余机会，agent 在 neutral/positive 续接下**倾向收尾而非继续用工具**。例如 `retail_T1_21 gpt_oss`：junction 时还剩 4–5 个 read，但 N0 suffix 做 **0** 个工具、N1/P 各做 **1** 个，P 与 N1 无差别。**过程被前置到 prefix，suffix 里没有过程供正控制去移动。** 唯一"正常"的是 `retail_T2_60 gpt_oss`（N0=[1,1,1,1,1]，mutation 稳定落在 suffix），但其 T2 指标是 read 数（mutation 是 1 个非 read 工具），故 P 也未在该指标上体现。

**gemma 判定**：全程 no-op ⇒ `REPRODUCIBILITY/LIVENESS_INELIGIBLE`，**不解释为"更鲁棒"**（§4/§9）。

---

## 5. 双独立 review：REVIEW_NOT_CLOSED

两个 fresh、隔离 review agent（A: junction/构念/P；B: scorer/复现/eligibility）均在写出报告前被 **API session limit** 打断（详见 `reports/r7d_ipma/step2_1/reviews/REVIEW_STATUS.md`）。这是**第三次**独立 review 因同一基础设施问题未闭合。依 §6/§9，`REVIEW_NOT_CLOSED` 本身即禁止 PROCEED。

---

## 6. G1–G4 判定与决策

```
G1_PASS   ✓  官方 scorer 闭合，63/63 真实 suffix 可评分，无代理
G2_PASS   ✓  family junction 可构造（T1/T2 各有有效 proof）
G3_FAIL   ✗  仅 2 active snapshot，range≤1 占 50%（<90%）
G4_FAIL   ✗  0 eligible cell；suffix 内无过程供正控制移动
REVIEW    ✗  REVIEW_NOT_CLOSED（两 agent 被 session limit 打断）
```

> **决策：`DO_NOT_PROCEED`。** 不建议运行 18-task full pilot。**不得**自动运行。

---

## 7. 最小修复清单（进入 full pilot 前必须闭合）

1. **junction 必须强制过程落入 suffix**（G3/G4 的统一根因）：
   - T1：把 junction 放在**身份解析之后、任何实质 read 之前**（而非"≥2 read 剩余"——已证明剩余 read 不会在 neutral suffix 被兑现）；或改用"每轮只允许 agent 推进一步"的受控续接，逼迫 read 进入 suffix。
   - T2：把 junction 钉在**确认→mutation 之前一刻**（`retail_T2 gpt_oss` 的 N0=[1,1,1,1,1] 证明这样 mutation 稳定落 suffix）。
2. **修 airline-T1 / telecom 的 opening 与选样**：airline_T1 的"review"式 opening 未触发 read；telecom 双控不产生 agent 侧 read → telecom 不适合 agent-process 的 T1/T2，建议**从 full pilot 移除 telecom 或另行操作化**。
3. **扩大 active 样本**：当前 active snapshot 仅 2 个（gemma 全 no-op）。需 (a) 加 per-model liveness gate 先排除 no-op 模型，(b) 只在 active cell 上评 G3/G4，(c) 每 active cell N0≥5 且要求 range≤1。
4. **修 mistral 畸形 tool call**（空函数名 → BadRequestError）：升级/更换 tool-call parser 或加重试跳过。
5. **T2 主指标改为对 mutation 敏感**（如 first_mutation_step / pre-mutation evidence coverage），而非纯 suffix read 数——否则 T2 的 P 灵敏度无法体现。
6. **闭合双独立 review**：错峰或换配额，确保两 agent 完整产出（连续三阶段被 session limit 打断是需要解决的基础设施问题）。
7. **vLLM 复现性**：如可，改用 offline deterministic 批跑（关 V1 multiprocessing / 开 batch invariance），并固定 checkpoint+vLLM 版本+硬件；在线跑必须写明 batch-invariance 依赖与非 bit-exact caveat。

---

## 附录

- A. 机器表：`results/r7d_ipma/step2_1/integrity/g1_scorer_fixtures.json`、`metrics/junction_proofs.json`、`metrics/closure_suffixes.jsonl`、`analysis/gate_verdicts.json`
- B. 复现：`official_scorer.py`（G1 fixture）→ `run_closure.py --r0 5 --r1 2 --rp 2` → `analyze_closure.py`
- C. 脚本全部 tracked；提交见 `git log --oneline`（5a3bc87…2a71722）
