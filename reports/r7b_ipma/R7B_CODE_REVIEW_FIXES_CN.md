# R7-B 代码审查与修复记录

- 日期：2026-07-07
- 审查对象：codex 提交的 R7-B confirmatory pipeline（代码 + 288 条合成 smoke）
- 结论：整体结构符合"第七轮修复实验"规格；发现 **5 处违反硬约束/正确性的 bug**,已全部修复并跑通 smoke（8/8 命令、288 合成 trace、0 失败）。

## 审查结论：codex 是否遵守要求

- ✅ 只做代码 + 合成 smoke,未跑真实模型、未进 full——符合要求。
- ✅ 独立目录、三层模板审计、pairing invariant、endpoint oracle、逐 gate PASR、runtime ProcessGuard 骨架均已实现。
- ⚠️ 但多处 gate 是 **fail-open**(数据缺失时默认通过),违反规格"不得在未通过审计的 pair 上计算 confirmatory PASR"。这类 bug 在合成 smoke 下不暴露(合成数据全部齐全),但在真实 run 会导致**错误地把不合格 pair 计入 confirmatory PASR**——正是本轮最需要堵住的。

## 修复清单

| # | 文件 | 问题 | 严重度 | 修复 |
|---|---|---|---|---|
| 1 | compute_pasr_metrics.py | semantic gate `defaultdict(lambda: True)`——**缺失语义判定默认 PASS**,违反硬约束#3 | 🔴 高 | 改 fail-closed:要求判定存在且该 (task,cond) 所有模板 + neutral 全 PASS 才通过 |
| 2 | compute_pasr_metrics.py | `delta_confirmation_rate` 恒为空字符串,C-family 阈值用了却不输出,不可复算 | 🟠 中 | 计算并记录真实 Δ确认率 |
| 3 | evaluate_endpoint_from_snapshot.py | endpoint 正确性**优先信任 trace 自报的 final_state_correct**,绕过字段级 oracle,违反 Step 6"不得用 proxy" | 🔴 高 | 改为 snapshot 可用时**一律由字段级 diff 推导**,自报值仅作不可算时的兜底 |
| 4 | evaluate_endpoint_from_snapshot.py | `expected_field_diffs` 为空时错误回退到 `required_evidence_fields`(证据**工具名**≠状态字段),把只读任务误判为 endpoint 错误 | 🔴 高 | 移除错误回退;只读任务 expected=[],无意外变更即正确（修复后合成 288 全部正确判定,此前误判 108 个 False） |
| 5 | check_pairing_invariants.py | hash 缺失时 `"None"=="None"` **虚假通过** | 🟠 中 | fail-closed:两侧都存在、非空、相等才算 same_hash |
| 6 | compute_pasr_metrics.py | noise floor 只对 family A 生效,Step 11"process delta 超过 neutral noise floor"未泛化 | 🟠 中 | noise floor 泛化到 n_tool/n_mut/conf/traj,C 用 Δ确认率 floor、E 用 neutral-neutral 轨迹 floor |

## 验证

- 编译：`py_compile scripts/r7b_ipma/*.py` 通过。
- smoke：`run_r7b_smoke.py` → 288 合成 trace、8/8 命令、0 失败。
- fail-closed 反向测试：缺 hash / 缺 semantic 判定 / 单模板不通过 → 均正确排除(修复前会误判为通过)。
- 修复后 smoke PASR：60 条 confirmatory PASR=1（family A 30 + E 30；B/C/D 正确被 threshold 排除）——管线产出有意义且各 gate 行为正确。

## 仍需注意（非本轮代码 bug）

1. 这些仍是**合成 smoke**,不是科学结果;strict PASR 数字只验证管线。
2. LLM/human semantic audit 未闭环 → 不得声称 semantic drift = 0。
3. 真实 run 需保证 runner 把 Step 10 全部 hash/snapshot 写入 trace,否则(现已 fail-closed)会被正确排除而非误计。
4. 下一步按规格：先跑真实 dev smoke（8×6×3×2=288 真实 run），要求 0 pairing fail / 0 endpoint unsupported / 0 contamination,再冻结 test。
