# R7-B Claude 修复复核与 full queue 决策

日期：2026-07-07

## 1. 复核结论

Claude 标出的 6 个 fail-open / proxy bug 已经在当前代码中修复，并通过新增反向测试验证。

| # | 风险点 | 当前复核结论 |
|---|---|---|
| 1 | `compute_pasr_metrics.py` semantic gate 缺判定默认 PASS | 已改为 fail-closed：attack 条件或 neutral 条件缺 semantic row 时均排除。 |
| 2 | `delta_confirmation_rate` 恒空 | 已从 attack/neutral 的 `confirmation_before_action_rate` 复算，并进入 C family threshold。 |
| 3 | endpoint 正确性信任 trace 自报值 | 已改为 snapshot field diff oracle 优先；支持 oracle 时不信 `final_state_correct` 自报值。 |
| 4 | `expected_field_diffs` 空时回退到 evidence tool 名 | 已移除回退；只读任务 `expected_field_diffs=[]/missing` 不会被 required evidence 误判为 endpoint 错。 |
| 5 | hash 缺失时 `"None"=="None"` 虚假通过 | 已改为双方 hash 必须非空且相等，否则 pairing fail。 |
| 6 | neutral noise floor 只覆盖 family A | 已泛化到 `n_tool / n_mut / conf / traj`，A/C/E 使用对应 noise floor。 |

## 2. 新增复核测试

新增文件：

- `tests/r7b_ipma/test_r7b_fail_closed.py`

覆盖：

1. 缺 pairing hash 必须 fail-closed。
2. endpoint oracle 必须忽略自报 `final_state_correct=True`。
3. 只读任务没有 `expected_field_diffs` 时不得被 `required_evidence_fields` 误伤。
4. 缺 attack semantic judgment 时 PASR pair 必须排除。
5. `delta_confirmation_rate` 必须可复算，并可触发 C family threshold。

执行结果：

```text
python -m py_compile scripts/r7b_ipma/*.py scripts/r7b_ipma/processguard/*.py
python -m pytest tests/r7b_ipma/test_r7b_fail_closed.py -q
..... [100%]
5 passed in 0.23s
python scripts/r7b_ipma/run_r7b_smoke.py
{"synthetic_traces": 288, "commands": 8, "failed": 0, ...}
```

## 3. 当前 full queue 决策

没有启动 R7-B full run。

原因不是 GPU 或模型资源，而是当前仓库还没有符合 R7-B 规格的真实模型 live runner / queue 脚本。直接启动旧 R7 full queue 会产生不合格结果。

### 3.1 当前可用脚本边界

- `scripts/r7b_ipma/run_r7b_smoke.py`：只生成 synthetic trace，用于管线 smoke，不调用真实模型。
- `scripts/r7_ipma/queue_r7_full.sh`：旧 R7-v1 queue，输出到 `results/r7_ipma/`，使用 `data/r6/r7_ipma_conditions_r6fmt.yaml`。
- 当前没有：
  - `scripts/r7b_ipma/run_r7b_live.py`
  - `scripts/r7b_ipma/queue_r7b_full.sh`
  - 能严格执行 R7-B frozen templates 的真实模型 runner。

### 3.2 不能用旧 R7 queue 代替 R7-B full 的具体原因

1. 条件集合不一致。
   - 旧 R7：`trust_pressure / continuation_pressure / implicit_progress_pressure`
   - R7-B：`confidence_without_delegation / matched_presence_pressure / smooth_process_pressure`

2. prompt 资产不一致。
   - R7-B 的审计对象是 `data/r7b_ipma/r7b_condition_templates.jsonl` 中 per-task/per-condition 的 frozen `surface_text`。
   - 旧 R6/R7 runner 使用全局 3-turn condition wrappers 加 R6 task clean turns。
   - 如果用旧 runner，真实模型看到的 prompt 与 R7-B template audit 的 prompt 不是同一批文本，semantic contamination / invariant claim 会失效。

3. trace metadata 不完整。
   - R7-B pairing gate 要求 `policy_spec_hash / tool_permission_hash / clean_task_semantics_hash / required_information_hash / endpoint_evaluator_hash` 等字段。
   - 旧 R6 live trace 不天然写入完整 R7-B pairing invariant metadata；直接跑会导致 pairing fail 或需要事后补丁，后者必须明确实现和测试。

4. endpoint oracle 还需要 R7-B live trace 级验证。
   - 当前 endpoint oracle 在 synthetic trace 上通过。
   - 真实 tau2/custom trace 必须确认 full snapshot、expected field diff、state diff 的字段语义完全一致。

5. R7-B 原始执行要求规定：先真实 dev smoke，再进入 test freeze/full。
   - 当前 288 run 是 synthetic smoke，不是“真实模型 dev smoke”。
   - 因此不应进入 full。

6. 资产数量有一个规格差异需要先决策。
   - 执行要求写的是 `8 dev tasks × 6 conditions × 3 models × 2 seeds = 288 runs`。
   - 当前 `data/r7b_ipma/r7b_task_registry.csv` 实际是 `6 dev / 24 test`。这需要修正为 8 dev，或在报告中正式解释为什么 dev=6。

## 4. 可进入 full 前的最小缺口

要安全挂 R7-B full，需要先补完下面几项：

1. 实现真实模型 R7-B live runner，严格使用 `data/r7b_ipma/frozen/r7b_frozen_templates.jsonl`，而不是旧 R7 YAML wrappers。
2. 真实 trace 必须写入 R7-B required metadata hashes。
3. 对 tau2/custom 环境统一输出 full initial/final snapshot 和 `expected_field_diffs`。
4. 跑真实 dev smoke，并要求：
   - 0 pairing invariant fail；
   - 0 endpoint unsupported in confirmatory dev tasks；
   - 0 template contamination；
   - 每个 PASR=1 都有逐例解释；
   - semantic audit 至少完成当前规定的 LLM/human closure，或把相关 claim 标为 provisional。
5. 真实 dev 通过后，再启动 full queue。

## 5. 当前允许 claim

- SUPPORTED：R7-B 分析管线和审计脚本已实现。
- SUPPORTED：Claude 修复的 6 个 fail-open/proxy bug 经代码复核和新增单测验证。
- SUPPORTED：synthetic smoke 通过。
- FORBIDDEN：R7-B full 已启动。
- FORBIDDEN：R7-B 已有 confirmatory 实验结论。
- FORBIDDEN：旧 R7 full queue 的结果可直接作为 R7-B confirmatory evidence。

