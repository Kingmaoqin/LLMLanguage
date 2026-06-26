# R6 Smoke Test Report

日期：2026-06-24  
范围：按 `/home/xqin5/llmlanguage/第六轮实验指导` 做合规检查、代码审查、minimal deterministic env smoke。  
结论：R6 静态测试、runner dry-run、minimal deterministic env smoke、metrics extraction、R6 integrity audit 均通过；未启动 live model / live tau2 实验。

## 1. 当前状态

已完成：

1. R6 task/template/policy asset 检查与补齐。
2. `calendar/email/workspace/file/privacy/message/hotel/travel/retail/airline` 等 R6 task 的 minimal deterministic env smoke。
3. R6 controlled-user renderer。
4. tau2-facing R6 controlled-user adapter 接口层。
5. R6 trace validator、metrics provenance、expected field diff coverage。
6. analysis/statistical scripts 默认拒绝 no-model smoke 数据，防止被误当成正式模型实验。

未完成 / 未启动：

1. live tau2 executor 未启动。
2. live model preflight/pilot/full 未启动。
3. 本地 tau2 导入链缺 `tokenizers`，tau2 adapter live-interface 测试被跳过。

## 2. 单元测试

命令：

```bash
python -m pytest tests/r6 -q
```

结果：

```text
98 passed, 1 skipped
```

跳过项：tau2 live-interface adapter test；原因是本地 tau2 导入链缺 `tokenizers`。

编译检查：

```bash
python -m py_compile src/r6/*.py scripts/r6/*.py tests/r6/*.py
```

结果：通过。

## 3. Runner dry-run

命令：

```bash
python scripts/r6/run_r6_experiment.py \
  --phase smoke \
  --config configs/r6/r6_preflight.yaml \
  --dry-run
```

说明：只规划矩阵，不写 trace，不调用模型。

## 4. Minimal deterministic env smoke

命令：

```bash
python scripts/r6/run_r6_experiment.py \
  --phase smoke \
  --config configs/r6/r6_preflight.yaml \
  --output-root results/r6_sensitivity/smoke_minimal_env
```

结果：

| item | value |
|---|---:|
| total_cells | 32 |
| planned_tau2_cells | 16 |
| deterministic_minimal_env_cells | 32 |
| live_tau2_executor_available | false |
| live_model_executor_available | false |
| needs_environment | 0 |
| traces_written | 32 |

输出：

- `results/r6_sensitivity/smoke_minimal_env/run_manifest.csv`
- `results/r6_sensitivity/smoke_minimal_env/run_plan_summary.json`
- `results/r6_sensitivity/smoke_minimal_env/traces/*.trace.json`
- `results/r6_sensitivity/smoke_minimal_env/deterministic_smoke_summary.json`

重要解释：

- `planned_tau2_cells=16` 只表示 retail/airline cells 已有 R6 controlled-user adapter 接口。
- 它不表示 live tau2 executor 已经跑通。
- 所有 trace 都写入 `model_call_performed=false`、`executor_mode=deterministic_env_smoke`。

## 5. Metrics extraction

命令：

```bash
python scripts/r6/extract_r6_metrics.py \
  --root results/r6_sensitivity/smoke_minimal_env
```

结果：

```text
runs: 32
privacy_violations: 0
unsafe_compliance: 0
over_refusals: 0
agent_side_abandonment: 0
```

额外核查：

- 32/32 rows: `model_call_performed=False`
- 32/32 rows: `executor_mode=deterministic_env_smoke`
- mutation/write tasks: `expected_field_diff_coverage=1.0`
- all rows: `unexpected_field_diff_count=0`
- no-model smoke rows: `final_state_correct` 为空，不再硬编码成功。

## 6. Integrity audit

命令：

```bash
python scripts/r6/final_integrity_audit_r6.py \
  --root results/r6_sensitivity/smoke_minimal_env \
  --report reports/r6_sensitivity/R6_SMOKE_MINIMAL_ENV_INTEGRITY.md
```

结果：

```text
R6 integrity: PASS (traces=32, invalid_rate=0.000)
```

## 7. Analysis 防误用 gate

默认分析 no-model smoke 会被拒绝：

```bash
python scripts/r6/analyze_r6_interactional_profile.py \
  --root results/r6_sensitivity/smoke_minimal_env
```

返回：

```text
refusing to analyze 32 no-model deterministic smoke rows as live R6 results
```

统计脚本同样默认拒绝。只有显式 `--allow-deterministic-smoke` 时才生成 pipeline validation 报告：

- `reports/r6_sensitivity/R6_SMOKE_MINIMAL_ENV_PROFILE.md`
- `reports/r6_sensitivity/R6_SMOKE_MINIMAL_ENV_STATISTICS.md`

这些报告仅用于 pipeline validation，不能作为模型实验结论。

## 8. 下一步

1. 修复本地 tau2 依赖：缺 `tokenizers`。
2. 在 tau2 环境可导入后，跑 R6Tau2ControlledUser live-interface smoke。
3. 接 live tau2 executor 后，再申请启动真实 model preflight。
4. preflight 通过后再进入 pilot；pilot 通过后才考虑 full。

