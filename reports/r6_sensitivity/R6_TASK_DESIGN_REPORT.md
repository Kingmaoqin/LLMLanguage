# R6 任务设计报告

日期：2026-06-24  
范围：第六轮 P1 task construction。  
状态：已生成静态任务、用户策略、policy annotations 与 seed-state descriptor；未启动模型实验。

## 1. 输出文件

| 文件 | 作用 |
|---|---|
| `data/r6/r6_tasks.yaml` | 30 个 R6 task 的静态规格 |
| `data/r6/r6_task_user_policies.yaml` | deterministic user policy scaffold；禁止 runtime LLM user |
| `data/r6/r6_task_policy_annotations.yaml` | confirmation/privacy/unsafe/refusal/field-diff 指标标注 |
| `data/r6/r6_environment_seed_states/seed_states.yaml` | P1 seed-state descriptor；P2/P3 需要生成或适配可运行 env snapshot |
| `tests/r6/test_r6_task_schema.py` | task 数量、domain、layer、schema、Layer B/C gate |
| `tests/r6/test_r6_task_policy_coverage.py` | user policy、annotation、seed-state 覆盖与 metric declaration |

## 2. 任务矩阵

总任务数：30。

| domain group | 数量 | 说明 |
|---|---:|---|
| retail | 8 | 复用 R5 retail 任务结构，含 read-only、confirmed write、prohibited cancel boundary |
| calendar | 6 | 新增 synthetic minimal env 设计，覆盖 lookup/reschedule/invite/cancel/private event |
| email_workspace | 6 | 新增 email/workspace 设计，覆盖 search/draft/send/status/follow-up/confidential/unsafe |
| travel_airline_hotel | 6 | airline 参考 tau2，本轮新增 hotel minimal env 设计 |
| file_message_privacy | 4 | 新增 file/message/privacy 设计，覆盖 checksum/send/private export/delete boundary |

Layer 分布：

| layer | 数量 | 意义 |
|---|---:|---|
| A | 8 | benign read-only / diagnostic |
| B | 14 | benign write，但必须证据 + confirmation |
| C | 8 | privacy/refusal/unsafe/boundary/prohibited mutation |

## 3. 关键设计约束

已落实：

1. 每个 task 都有 `clean_user_turns`，且严格为 3 turn。
2. 每个 task 的 `expected_min_tool_calls >= 5`。
3. Layer B 全部 `requires_confirmation: true` 且有 mutation tools。
4. Layer C 全部 `requires_refusal: true`，并带 privacy/boundary/correct_refusal/unsafe/prohibited mutation 等风险标签。
5. 所有 task 都有 deterministic user policy 覆盖。
6. 所有 task 都有 policy annotation 覆盖。
7. 所有 task 引用的 seed-state descriptor 均存在。
8. R6 新指标已在 annotation 中声明：field-level diff、agent-side abandonment、privacy_violation、unsafe_compliance、correct_refusal、over_refusal、confirmation requested/obtained/before-action、continued_task_after_boundary。

未完成但已显式标记为 P2/P3 的部分：

1. `calendar/email/workspace/hotel/file/message/privacy` 当前是 synthetic minimal env 设计，还没有 runner 可执行环境。
2. `data/r6/r6_environment_seed_states/seed_states.yaml` 目前是 descriptor，不是完整 DB snapshot。
3. field-level DB diff 还没有 evaluator 实现。
4. correct_refusal / over_refusal / unsafe_compliance / privacy_violation 还没有 runner/evaluator 实现。
5. 模型 preflight 尚未开始。

## 4. 与 R5 诊断问题的对应

R5 主要弱点：

- retail-only；
- 只有 8 task cluster；
- Layer C/privacy/refusal/unsafe 覆盖不足；
- endpoint 稳定但过程指标没有强稳健的显著性；
- valence 操作偏温和。

R6 task design 对应修复：

| R5 弱点 | R6 修复 |
|---|---|
| retail-only | 扩到 5 个 domain group |
| task cluster 少 | 扩到 30 tasks |
| 缺 Layer C | 8 个 Layer C task |
| 缺 privacy/refusal/unsafe | policy annotations 显式定义 privacy/unsafe/refusal |
| 缺 field-level causal diff | annotations 先定义 expected field diffs，后续 runner/evaluator 实现 |

## 5. 当前测试状态

已运行：

```bash
python -m pytest tests/r6 -q
```

结果：

```text
92 passed in 17.24s
```

## 6. Review agent 复查后修复项

按用户要求，P1 新增 Python 测试与 YAML 资产写好后已交给 review agent 做只读审查。审查指出原 gate 偏弱，随后已完成以下修复：

1. 增强 `tests/r6/test_r6_task_schema.py`：增加字段类型、枚举、Layer A/B/C 行为约束。
2. 增强 `tests/r6/test_r6_task_policy_coverage.py`：增加 annotation layer 与 task layer 一致性、seed-state domain/diff 粒度一致性、confirmation scope 覆盖 mutation tools、prohibited tools 在 task/annotation/user policy 三源对齐。
3. 增加 hybrid Layer C 标注：`r6_retail_08_prohibited_cancel_boundary` 明确 `must_continue_allowed_subtask`、`allowed_mutations_after_boundary`、`must_refuse_only`。
4. 修正两个 Layer B clean user turns，避免用户第三轮形成预授权；真实确认留给 deterministic user policy。
5. 补齐 `privacy_sensitive: true` 任务的 `privacy_rules`，并要求 `unsafe_request: true` 任务有 `unsafe_rules`。
6. 增强 template contamination 测试：从 `r6_tasks.yaml` 动态抽取高信息 task/tool/source terms，而不是只靠手写 domain word list。
7. 根据复审建议继续加固 schema：user policy 增加 `policy_type` enum、confirmation bool/scope、never_authorize_tools 类型检查；annotation 增加 refusal_policy enum、confirmation/privacy/unsafe/prohibited tools 类型检查；seed-state 增加 state_family、required_entities、diff_granularity 类型检查。
8. Layer C annotation 现在显式包含 `continued_task_after_boundary_expected`；并新增 `prohibited_tools` alias，避免后续 evaluator 把受保护 read/access tool 误解为只有 mutation 才需检查。
9. 新增 `scripts/r6/extract_r6_metrics.py` 后，`tests/r6` 增加 R6 metric extractor 的 synthetic trace 测试；当前 R6 静态与 extractor 测试合计 78 项通过。

## 7. 下一步 gate

下一步可以继续 P1/P2，但仍不能启动 pilot/full：

1. 把 R6 synthetic minimal env 从 descriptor 变成可执行 deterministic env。
2. 写 `scripts/r6/run_r6_experiment.py` 前，应先明确 runner 如何复用 R5 trace bundle 与新 R6 field-level diff。
3. 每新增一个 `scripts/r6/*.py` 后，必须让 review agent 审查并修复问题。
4. 模型扩展只能先做 preflight，不能直接 full。
