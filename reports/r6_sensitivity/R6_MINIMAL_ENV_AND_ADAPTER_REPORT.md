# R6 minimal deterministic env 与 controlled-user adapter 实现报告

日期：2026-06-24  
范围：代码实现 + 单元测试 + deterministic smoke；未启动 full/pilot live model 实验。

## 结论

已实现 R6 的最小 deterministic 环境与 controlled-user adapter 基础设施：

- `calendar/email/workspace/file/privacy/message/hotel/travel/retail/airline` 等 R6 task 均可通过 no-model minimal env 生成 schema-valid trace。
- mutation task 现在按 `data/r6/r6_task_policy_annotations.yaml` 的 `expected_field_diffs` 产生业务字段级 diff，例如：
  - `events.start_time`, `events.end_time`
  - `emails.sent_messages`
  - `projects.status`
  - `tasks.created`
  - `messages.sent`
  - `reservations.baggages`, `payments.charges`
  - `orders.return_status`, `refunds.created`
- R6 controlled user 保持三轮 clean task text 不变，只替换 social wrapper；确认策略按 tool scope 决定。
- 新增 tau2-facing R6 user adapter 接口，但当前本地 tau2 导入链缺 `tokenizers`，因此测试中跳过 live tau2 adapter 实例化。runner 仍默认不启动 live tau2/model。

## 关键文件

- `src/r6/controlled_user_adapter.py`  
  R6 deterministic user renderer：读取 task/template/user-policy，生成 3-turn matched styled user turns，并提供 tool-specific confirmation policy。

- `src/r6/minimal_env.py`  
  R6 minimal deterministic tool/state env：不调用模型，执行 read/mutation/refusal/confirmation path，写 canonical trace 和 R6 扩展字段。

- `src/r6/tau2_controlled_user_adapter.py`  
  tau2 `HalfDuplexUser` 接口层：为 retail/airline live tau2 executor 准备 R6 user adapter。该文件不启动 tau2、不调用模型。

- `src/r6/trace_schema.py`  
  R6 trace validator：在 Stage2.5b trace 基础上额外检查 R6 provenance、field diff、confirmation/refusal/privacy/unsafe events。

- `scripts/r6/run_r6_experiment.py`  
  smoke/preflight 可运行 deterministic env；pilot/full 默认拦截，除非显式 `--allow-deterministic-pilot-full`。

- `scripts/r6/extract_r6_metrics.py`  
  增加 provenance 字段和 expected field diff coverage：
  - `executor`
  - `executor_mode`
  - `model_call_performed`
  - `live_tau2_executor_available`
  - `smoke_trace_only`
  - `expected_field_diff_coverage`
  - `unexpected_field_diff_count`
  - `missing_expected_field_diffs`

- `scripts/r6/analyze_r6_interactional_profile.py`、`scripts/r6/statistical_analysis_r6.py`  
  默认拒绝分析 `model_call_performed=False` 的 no-model smoke metrics；只有显式传 `--allow-deterministic-smoke` 才会生成 pipeline validation 报告。

## smoke 结果

命令：

```bash
python scripts/r6/run_r6_experiment.py \
  --phase smoke \
  --config configs/r6/r6_preflight.yaml \
  --output-root results/r6_sensitivity/smoke_minimal_env
```

结果：

- planned cells: 32
- traces written: 32
- domains: retail/calendar/email/airline 各 8
- executor provenance:
  - `tau2_r6_controlled_user`: 16 planned tau2-domain cells
  - `r6_minimal_env`: 16 synthetic-domain cells
- `model_call_performed=false`
- `live_tau2_executor_available=false`
- `live_model_executor_available=false`

metric extraction：

```bash
python scripts/r6/extract_r6_metrics.py --root results/r6_sensitivity/smoke_minimal_env
```

结果：

- runs: 32
- privacy violations: 0
- unsafe compliance: 0
- over refusals: 0
- agent-side abandonment: 0
- expected field diff coverage:
  - mutation/write tasks: `1.0`
  - no-diff/refusal/read-only tasks: blank / not applicable
- unexpected field diff count: 全部 `0`
- `final_state_correct`：blank；不再对 no-model smoke 硬编码为 true。

完整性审计：

```bash
python scripts/r6/final_integrity_audit_r6.py \
  --root results/r6_sensitivity/smoke_minimal_env \
  --report reports/r6_sensitivity/R6_SMOKE_MINIMAL_ENV_INTEGRITY.md
```

结果：`PASS (traces=32, invalid_rate=0.000)`。

## 防误用保护

已验证默认 analysis 会拒绝 smoke metrics：

```bash
python scripts/r6/analyze_r6_interactional_profile.py \
  --root results/r6_sensitivity/smoke_minimal_env
```

返回：

```text
refusing to analyze 32 no-model deterministic smoke rows as live R6 results
```

统计脚本同样默认拒绝 no-model smoke。只有显式 `--allow-deterministic-smoke` 时，才会生成 pipeline validation 报告：

- `reports/r6_sensitivity/R6_SMOKE_MINIMAL_ENV_PROFILE.md`
- `reports/r6_sensitivity/R6_SMOKE_MINIMAL_ENV_STATISTICS.md`

这些报告不能作为模型实验结论使用。

## 测试

```bash
python -m pytest tests/r6 -q
```

结果：`98 passed, 1 skipped`。

跳过项：tau2 adapter live-interface test。本地 tau2 导入链触发 `litellm -> tokenizers` 缺失；adapter 模块已安全捕获该问题。修复本地环境依赖后，该测试可用于验证 tau2 `HalfDuplexUser` 实例化。

```bash
python -m py_compile src/r6/*.py scripts/r6/*.py tests/r6/*.py
```

结果：通过。

## 仍需注意的边界

1. 这不是 live model 实验。所有 smoke trace 都明确写入：
   - `executor_mode=deterministic_env_smoke`
   - `model_call_performed=false`
   - `smoke_trace_only=true`

2. tau2 retail/airline 当前完成的是 R6 controlled-user adapter 接口层，不是 live tau2 executor 跑通。runner summary 已改为：
   - `planned_tau2_cells`
   - `live_tau2_executor_available=false`
   - `needs_live_tau2_executor=true`

3. minimal env 是为 pipeline/schema/metric contract 验证服务的 deterministic env；它不会替代真实 tau2 DB/evaluator 或真实 agent trajectory。

4. 本地 tau2 live adapter 进一步 smoke 前，需要先修复 Python 环境依赖：当前缺 `tokenizers`。

