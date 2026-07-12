# R7-D Step 1-G：Endpoint 与环境真实性审计

- 日期：2026-07-10
- 机器表：`results/r7d_ipma/step1/endpoint_crosscheck.csv`
- 脚本：`scripts/r7d_ipma/step1g_endpoint_environment_audit.py`

---

## 0. 结论（这是本轮 Step 1 最重要的单项发现）

> **R7-C 的工具环境不返回任何任务信息。** read 工具是空操作：它回显调用方传入的参数、复述任务的 policy 标志，然后返回一个不透明的 state hash。"数据库"里装的是形如 `"initial::orders.items"` 的**字面占位符字符串**——没有 users、没有 orders、没有 products。
>
> **全部 2592 条 trace、3027 次工具调用中，参数被解释过的次数是 0。**
>
> 因此：**agent 无法收集证据，因为根本没有证据可以收集。** 48 个所谓的 "tau2 任务"，是 tau2 的**目标句子**接在一个桩环境上。

这不是一个可以靠"降级表述"处理的 caveat。它决定了整个实验能否回答它的科学问题。

---

## 1. 官方 tau2 evaluator 是否可用？——**是**

| 检查 | 结果 |
|---|---|
| `tau2` 包安装 | ✅ `/home/xqin5/tau2-bench`，pip `tau2 1.0.0` |
| `from tau2.evaluator.evaluator import evaluate_simulation` | ✅ 可导入 |
| `registry.get_domains()` | `['mock', 'airline', 'retail', 'telecom', 'telecom-workflow', 'banking_knowledge']` |
| retail 官方任务数 | 114，全部带 `evaluation_criteria` |
| R7-C 的 48 个任务中映射到真实 tau2 任务的 | **28**（retail 24 + airline 4） |
| 这 28 个任务是否有官方评估标准 | **28/28 有**。例：`airline_12` → `actions=5; env_assertions=0; nl_assertions=2` |

**R7-C 审计把 Phase H 标为 NOT_AUDITABLE，理由是"本地不存在官方 evaluator"——这个理由不成立。官方 evaluator 一直都在，而且能跑。**

更进一步：**R6 曾经用过真实 tau2。** `scripts/r6/run_r6_live.py:45` 定义了 `TAU2_DOMAINS = {"retail", "airline"}`，第 352 行按域选择 `executor = "tau2_live_model" if domain in TAU2_DOMAINS else "r6_minimal_live_model"`，并 `from tau2.run import EvaluationType, build_orchestrator, run_simulation` 走官方编排与官方评估。

**R7-B/R7-C 的 runner（`scripts/r7b_ipma/run_r7b_live.py`）里没有任何 tau2 代码路径。** R7-C 把这 28 个 tau2 任务**从真实环境降级到了合成桩环境**。

---

## 2. 那为什么官方 evaluator 仍然不能用于 R7-C 的 trace？

因为**没有可供评分的东西**。官方 evaluator 需要两样：

1. **带真实参数的 action**（例如 `modify_pending_order_address(order_id='#W123', address1=...)`），用于 `actions` 检查；
2. **真实的数据库终态**，用于 `env_assertions`。

R7-C 两样都没有：

### 2.1 工具返回值：全量扫描 3027 次调用

read 工具**只有一种**返回形状：

```
('arguments_received', 'available_expected_field_diffs', 'domain', 'layer',
 'mutation', 'ok', 'policy', 'state_hash', 'task_id')
```

mutation 工具只有一种：`('mutation', 'ok', 'updated_paths')`。

含真实业务字段（`user_id` / `order_id` / `price` / `first_name` …）的调用数：**0 / 3027**。

模型传进去的 `query` 参数（如 `"user_id=1001"`、`"category='camera'"`）被原样塞进 `arguments_received` 回显，**从不解释**。`get_order_details` 不返回订单；`find_user_id_by_name_zip` 不返回 user id。

### 2.2 环境状态

```json
"initial_environment_state": {"state": {
  "state_family": "tau2_retail_derived",
  "task_id": "...", "domain": "retail", "layer": "B", "seed": 301,
  "records": {"<task_id>": {"status": "initial", ...}},
  "orders":    {"items":   "initial::orders.items"},
  "exchanges": {"created": "initial::exchanges.created"}
}}
```

state 的 key（`orders` / `payments` / `reservations` / `users` …）只是**空容器**，值是哨兵字符串。mutation 工具做的事就是把 `"initial::X"` 翻成别的字符串。所谓 `r7c_minimal_field_diff` endpoint oracle，检查的就是这些哨兵字符串有没有按预期翻转。

**判定：`official_evaluator_applicable_to_r7c_trace` = NO，48/48。**

---

## 3. 三方交叉验证的状态

指导 §13 要求对 ≥12 个代表任务做三方交叉：

| 腿 | 状态 | 说明 |
|---|---|---|
| (1) 官方 tau/tau2 evaluator | **NOT_AUDITABLE（对现有 R7-C trace）** | 不是因为工具缺失——工具在、能跑、28 个任务有官方标准。是因为 **R7-C 从未跑过 tau2 simulation**，没有 action 参数、没有 DB 终态可供评分。 |
| (2) minimal field-diff evaluator | 可复算 | 但它检查的只是哨兵字符串是否翻转 |
| (3) 人工任务结果判断 | **NOT_CLOSED** | 无标注者。不伪造。 |

**关键区分（必须写进论文）**：这一项的 NOT_AUDITABLE 是 **R7-C 的属性，不是工具链的属性**。R7-C 审计报告 §9 的表述（"本地不存在官方 evaluator 或无法在真实环境重放"）会让读者以为是资源限制。事实是：能力一直都有，R6 也用过，是 R7-C 主动改用了桩环境。

---

## 4. 这解释了什么

这一个事实，把 Step 1 其余模块的发现串成了一条因果链：

| 观察到的现象 | 由桩环境解释 |
|---|---|
| **60.1% 的运行（1557/2592）一个工具都没调**，三个模型的中位数工具调用数都是 0 | 工具不返回任何信息，模型自然直接作答 |
| **46/48 个任务没有任何可替代的 evidence source**（Step 1-C，D2=2/48） | 没有证据，何来"替代来源" |
| **纯重排序在所有家族的检出率都是 0%**（Step 1-F） | evidence-path steering 在这里唯一可能的形式就是重排序，而它不可见 |
| **corr(POS, 任务 PASR) = −0.576**（Step 1-H）：过程机会越少的任务 PASR 越高 | PASR 测的不是 steering，是短轨迹上的阈值抖动 |
| **零处理 PASR = 1.44%（匹配后），A 家族 10.8%**（Step 1-B） | 短而不稳的轨迹 + hair-trigger 阈值 |

> **你无法在一个"没有证据可收集"的环境里，测试"对话压力是否能操纵证据收集"。**

---

## 5. Step 2 的硬前置

1. **必须换回真实 tau2 环境**（retail / airline 至少 28 个任务），走 `tau2.run.build_orchestrator` + 官方 `evaluate_simulation`。R6 的代码路径已经存在，可直接复用。
2. 非 tau2 域（calendar / email / file / hotel / workspace / privacy）**必须要么实现真实的工具语义（返回真实数据、解释参数），要么从 primary 分析中移除**，只作 appendix。
3. 在任何新的 IPMA 实验之前，必须先证明：**agent 在 neutral 条件下确实会调用工具、确实会收集证据、确实会在证据基础上分支。** 否则再精巧的攻击也无处施加。
