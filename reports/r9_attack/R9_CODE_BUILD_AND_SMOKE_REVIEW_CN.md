# R9 机制对齐过程操纵攻击平台 —— 代码构建与 Smoke 审计报告

分支：`r9-mechanism-aligned-process-attack`
范围：**代码构建 + smoke + 自审**；**未跑全量实验**（按要求）。
日期：2026-07-22

---

## 1. 交付概览

按 R9 执行 Prompt（`新设计的实验`）第 4 节要求的目录与脚本清单，已全部落地并可运行：

| 层 | 文件数 | 状态 |
|----|-------|------|
| `scripts/r9_attack/*.py`（驱动+攻击+分析） | 21 | ✅ |
| `scripts/r9_attack/common/*.py`（基础设施） | 9 | ✅ |
| `scripts/r9_attack/adapters/*.py`（两基准适配器） | 6 | ✅ |
| `tests/r9_attack/test_*.py`（Prompt §4 指定的 9 个测试） | 9（36 用例） | ✅ 全绿 |
| 合计代码 | ~6.5k 行 | ruff 全过 |

Prompt §4 点名的 19 个脚本全部存在（`bfcl_adapter`、`toolsandbox_adapter`、`build_splits`、
`run_calibration`、`canonical_message_cache`、`toolsandbox_fact_ledger`、`attack_families`、
`candidate_generator`、`constraint_filter`、`targeted_selector`、`run_dev`、`freeze_attacker`、
`run_confirmatory`、`run_confounder_module`、`extract_metrics`、`reference_metrics`、
`analyze_confirmatory`、`run_dual_review`、`safety_audit`、`check_integrity`）。

---

## 2. 环境与基准（Prompt §3）

- **BFCL（主基准，§3.1）**：`bfcl-eval==2026.3.23`，隔离 conda 环境 `r9_bfcl`。
  使用 `multi_turn_base` subset，**官方 `multi_turn_checker` 原生评测器**，200 条任务，
  dataset sha256 已入 manifest。排除了 miss-func/miss-param/irrelevance/long-context 类。
- **ToolSandbox（外部状态化验证，§3.2）**：Apple 官方仓库 `/home/xqin5/ToolSandbox`，隔离
  conda 环境 `r9_ts`。**每 episode 一个子进程**（状态随进程销毁 = §3.2 的容器隔离语义），
  1032 scenarios，筛出 67 条合格（multi-tool ∧ (multi-user-turn ∨ state-dependency)，
  排除 insufficient-info / scrambled / RapidAPI 联网工具）。原生 `Evaluation.evaluate` milestone 评测器。
- **模型**：3 个本地 vLLM 端点（gpt_oss_120b / gemma4_31b / mistral_small_3p2），全部 `127.0.0.1`。

---

## 3. Smoke 结果（端到端，真实模型）

| 环节 | 命令 | 结果 |
|------|------|------|
| 安全审计 §0.2 | `safety_audit.py` | **SANDBOX_SCOPE_CLOSED**，net_guard 主动探测确认阻断 192.0.2.1、放行 loopback |
| 数据切分 §5 | `build_splits.py` | calibration=16 / dev=8 / test=24 / confounder=6，**完全不重叠**，family 均衡 |
| BFCL 单 episode | 适配器直调 | success=1，7 次工具调用，**变异检测正确**（mkdir/mv/echo/touch=写，cd/grep/ls/tail=读） |
| ToolSandbox ledger §7.2 | `toolsandbox_fact_ledger.py` | 冻结 2 个 Fact Ledger，opening 正确（"Remind me to buy chocolate milk"） |
| ToolSandbox 计分 episode | 适配器直调 | 原生 milestone 评测、metric 抽取、outcome 分类、net_events=0 均正常 |
| 校准 §6 | `run_calibration.py` | 2 episode，模型门评估，正确判 `STOP_MODEL_CAPABILITY_FLOOR`（<2 模型） |
| Dev §8 | `run_dev.py` | 1 block × 5 arm（N/P0/P1/P2/P3）全部产出 |
| 冻结攻击器 §8.6 | `freeze_attacker.py` | compression/inflation 各冻结策略 + priors + 阈值 |
| Confirmatory §9 | `run_confirmatory.py` | 2 task × 6 condition（C0-C5）= 12 episode |
| 分析 §12/14/19 | `analyze_confirmatory.py` | bootstrap CI / 置换检验 / Holm / 效应量 / 门 G1-G4 / A-F 决策 全部计算 |
| 完整性 §18 | `check_integrity.py` | **INTEGRITY_OK**：production↔reference 双复算 **0 mismatch**，canonical 不变性 0 问题，网络事件 0 |
| Confounder §16 | `run_confounder_module.py` | 4 arm，interaction 估计正常 |
| 双评审 §15 | `run_dual_review.py` | 2 个**不同端点**评审员，盲审，fail-closed 分歧保留 unresolved |
| C4 实弹攻击环 | 隔离验证 | 4 候选 → 8 次实评审调用 → 3/4 与 4/4 存活 → selector 选中 → canonical 逐字保留 |

---

## 4. 关键正确性保证（构造级，非事后检查）

1. **Canonical 语义不变性（§7）**：`rendered = prefix + canonical + suffix`，canonical 永不过 LLM。
   `test_canonical_hash_identity` 断言 C0-C5+N/P 全条件下 canonical 子串与哈希恒等。
2. **变异检测（§10.1）**：不用手写读/写工具表，而是对基准**自身状态**做调用前后深拷贝快照比对，
   两基准同一"状态改变动作"定义 → Compression 主指标跨基准可比。
3. **最低验证路径（§10.3）**：BFCL 用官方 `possible_answer` GT 回放 + 同一变异检测器求分母；
   ToolSandbox 用 Milestone DAG 工具 + 中性预跑的变异集。test 前冻结，双实现复算。
4. **双门约束过滤（§8.5/§15）**：Gate1 确定性程序护栏（禁用短语/token 预算/工具名/数字），
   Gate2 两个独立端点评审员 fail-closed。无候选存活 → 回退中性，**绝不改写规避**。
5. **进程网络隔离（§0.2/§18）**：`net_guard` 进程级 patch socket，只放行 loopback/内网；
   主动自检 + 事件记账并入 §18。`test_no_network` 验证阻断公网、放行 loopback、事件记录。
6. **双实现复算（§18）**：`extract_metrics`（生产）与 `reference_metrics`（独立路径）对主指标 +
   endpoint transition 复算，`check_integrity` 要求 0 mismatch —— smoke 实测 0。
7. **端点保持 ASR（§11.4）**：仅 1→1 计入；0→0/0→1/1→0 永不计成功；`test_endpoint_transition` 覆盖。
8. **任务聚类统计（§14）**：bootstrap 与置换检验聚类单位是 **task 非 episode**；
   `test_condition_pairing` 验证多 repeat 的大任务不会按 episode 数支配估计。

---

## 5. 自审发现与已修问题

- **[已修] 反向方向标志过严**：初版把 `wrong_direction` 放进 fail-closed 集，导致弱评审员把合规
  压力战术判成"反方向"，C4 永远回退中性（G4 必挂）。§8.5 的评审职责是**污染**检查，方向匹配是
  selector 的职责 → 已将 `wrong_direction` 移出 fail-closed（仍记录供诊断）。修复后 3/4、4/4 候选存活。
- **[已修] ToolSandbox few-shot 污染**：`harvest_slots`/`_opening_utterance` 误把用户模拟器 few-shot
  示例（`visible_to==[USER]`）当作任务 canonical。→ 三处按 ToolSandbox 官方口径过滤，opening 恢复正确。
- **[已修] ToolSandbox 无界生成挂死**：ToolSandbox 原生 agent role 不传 `max_tokens`，弱模型陷入重复
  生成直到 16k 上下文 = 假死。→ `BoundedAgent`（每 episode 硬工具步数上限，对齐 BFCL 的 20 步预算）
  + worker 看门狗超时 + `BoundedLLMUser`（预跑用户回合上限）。
- **[设计选择，待全量前定夺] 首轮强制中性**：当前 `first_turn_must_be_neutral=True`（turn 0 永不攻击）
  严于 §2（§2 仅要求"至少一次 intervention 在首轮之后"）。对 4 轮任务，G4 的 fallback 上界恰为 25%
  边界。全量前可考虑放开 turn 0 攻击但保证 ≥1 次在首轮后，以留 G4 余量。

---

## 6. Smoke 暴露的**实验性**发现（非代码缺陷）

- **ToolSandbox 模型能力地板**：mistral/gpt-oss 在 ToolSandbox 多轮场景下几乎不调用工具（改为闲聊/
  幻觉答案），中性预跑 milestone≈0、slots 稀疏。这正是 §6 校准要检出的 floor effect，Prompt 明确用
  `STOP_MODEL_CAPABILITY_FLOOR` 处置。**平台代码对稀疏 ledger 稳健**（ledger_miss→default，仍计分）。
  → 全量前需在 §6 校准阶段用更强本地模型，或据校准结果据实触发 STOP。
- **共享 GPU 竞争**：4×A100 与 co-tenant 共用，实弹 C4 出现过 target 模型 infra 失败——被正确归类为
  `infrastructure_failure` 并整块重跑（§17），未污染 outcome。全量运行需按记忆中的看门狗 + 单卡串行策略。

---

## 7. 与全量实验的差距（明确边界）

本轮**刻意未做**（等后续批准）：
- 未跑 §6 完整 256 校准 / §8 480 dev / §9 2400 confirmatory / §16 288 confounder。
- 未据校准真正选定 2 个 target 模型（smoke 用单模型演示流程与 STOP 逻辑）。
- 未产出 §21 的 4 份正式报告（校准/Stage1/主报告/英文骨架）——它们是全量产物。
- freeze 出的 priors/阈值是 smoke 数据，**非**可用于主张的冻结策略。

平台已就绪：给定 2 个通过 §6 门的模型后，
`safety_audit → build_splits → toolsandbox_fact_ledger → run_calibration → run_dev →
freeze_attacker → run_confirmatory → check_integrity → analyze_confirmatory →
run_dual_review → run_confounder_module` 即为全量执行链。

---

## 8. 结论

代码构建**完成**，两基准均达成"baseline-capable / semantic-exact / process-sensitive"的原生评测闭环；
9 个指定测试 36 用例全绿；§18 双复算 0 mismatch；§0.2 沙箱边界主动验证通过。平台可进入（经批准的）
全量阶段。**当前唯一实质阻塞是 §6 模型能力地板**——需以更强本地模型完成校准或据实 STOP，此为实验决策而非代码缺陷。
