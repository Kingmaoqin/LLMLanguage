# R6 Claude 后续改动审查报告

日期：2026-06-26

## 审查结论

Claude 的后续工作有有效推进：移除了几个 A100 上不可行或失败的本地模型，并新增了 Mistral Small 3.2、Gemma3 27B、OLMo2 32B、Phi-4 reasoning 等候选配置。其中 `mistral_small_3p2` 已有 16-cell live preflight 结果，trace schema 全部通过。

但原新增 runner/config 不能直接用于 full run。我已修复两个硬错误和两个实验管理风险：

1. `scripts/r6/run_r6_full_sequential.sh` 调用了不存在的 `make_single_model_cfg_pair`，运行时会直接失败。
2. `scripts/r6/run_preflight_all_models.sh` 对 Mistral 使用了与 `r6_models.yaml` 注释相冲突的参数：脚本使用 `--load_format mistral`，配置说明写明不要使用该格式。
3. preflight runner 把所有模型写入固定目录 `results/r6_sensitivity/model_preflight`，导致旧 `run_manifest.csv` 污染新 live traces，完整性审计失败。
4. full runner 默认写入固定 `results/r6_sensitivity/full_main`，且没有强制人工 gate，存在误启动/覆盖同一 R6 root 的风险。

## 已修复内容

### 1. 重写 preflight runner

文件：`scripts/r6/run_preflight_all_models.sh`

修复后行为：

- 默认写入新 root：`results/r6_sensitivity/model_preflight_new_<UTC timestamp>/`
- 每个模型单独子目录：`.../<model_alias>/`
- 每个模型独立生成：
  - `live_run_plan.json`
  - `live_run_summary.json`
  - `traces/`
  - `interactional_metrics/`
  - integrity report
- 拒绝复用已有输出目录。
- Mistral serve 参数改为 HF format，不使用 `--load_format mistral`。

### 2. 重写 full runner

文件：`scripts/r6/run_r6_full_sequential.sh`

修复后行为：

- 默认拒绝运行 full；必须显式：

```bash
R6_ALLOW_FULL=1 bash scripts/r6/run_r6_full_sequential.sh
```

- 默认写入新 root：`results/r6_sensitivity/full_main_seq_<UTC timestamp>/`
- 拒绝使用非空输出目录。
- 先跑 R5 baseline，再按 GPU3 顺序跑新模型。
- 结束后自动执行 integrity、metrics、statistics、profile。
- 当前 GPU3 full 默认只包含 `mistral_small_3p2`；`gemma3_27b`、`olmo2_32b`、`phi4_reasoning` 仍是 pending，不进入 full。

### 3. 修正 full 配置

文件：

- `configs/r6/r6_full_main_v2.yaml`
- `configs/r6/r6_full_3model.yaml`
- `configs/r6/r6_models.yaml`

修正后：

- full 默认模型为：
  - `gemma4_31b`
  - `gpt_oss_120b`
  - `mistral_small_3p2`
- 移除失效的 `llama3_3_70b_fp8` full 配置引用。
- `gemma3_27b`、`olmo2_32b`、`phi4_reasoning` 标记为 pending，不进入 full。
- Mistral preflight 状态改为 `passed_tool_preflight_2026-06-25`，并明确记录行为失败：16/16 schema-valid，但 4/16 policy failure。

## 结果核对

### Mistral Small 3.2 preflight

Root：`results/r6_sensitivity/model_preflight`

- traces: 16
- invalid traces: 0
- metrics: 成功
- policy_failure_any:
  - False: 12
  - True: 4
- final_state_correct:
  - True: 1
  - False: 7
  - 空值: 8（tau2 hash-only final state 不可直接评价）

完整性审计在该 root 上 FAIL，原因不是 schema，而是目录中残留旧 `run_manifest.csv`：

- manifest: 96
- traces: 16

这正是 runner 需要改成“每模型独立 root”的原因。

### Airline repair preflight

Root：`results/r6_sensitivity/airline_repair_preflight_live_20260625`

- traces: 8
- invalid traces: 0
- integrity: PASS
- metrics: 成功
- policy_failure_any:
  - False: 7
  - True: 1

该结果说明 airline task 文本修复有效，但仍有一个 Gemma praise condition 出现 over-refusal/abandonment，需要作为行为 finding 报告。

### Full main 尝试

Root：`results/r6_sensitivity/full_main_live_20260625`

- 计划：1440 runs
- 实际 traces：7
- 没有完整 summary / metrics

结论：这是 aborted/partial full attempt，不能用于任何 R6 结论。

## 当前验证

已运行：

```bash
bash -n scripts/r6/run_preflight_all_models.sh
bash -n scripts/r6/run_r6_full_sequential.sh
python -c "yaml.safe_load(...)"  # R6 configs load OK
R6_ALLOW_FULL=0 bash scripts/r6/run_r6_full_sequential.sh  # 正确拒绝
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 conda run -n agentsearch python -m pytest tests/r6 -q
```

结果：

- R6 tests: `105 passed, 1 warning, 30 subtests passed`

## 是否可以 full run

当前仍不建议 full run。

原因：

1. 新模型中只有 `mistral_small_3p2` 完成 tool/trace preflight；其余新模型仍 pending download/preflight。
2. Mistral preflight 有 4/16 policy failure，虽然不是 parser/schema failure，但必须写入报告。
3. Airline repair preflight 仍有 1/8 policy failure。
4. 旧 `full_main_live_20260625` 是 partial output，不可复用，也不能继续在原目录追加。

## 下一步

建议顺序：

1. 用修复后的 runner 重新跑 Mistral 独立 preflight，生成干净 root：

```bash
bash scripts/r6/run_preflight_all_models.sh mistral_small_3p2
```

2. 下载并逐一 preflight：

```bash
bash scripts/r6/run_preflight_all_models.sh gemma3_27b
bash scripts/r6/run_preflight_all_models.sh olmo2_32b
bash scripts/r6/run_preflight_all_models.sh phi4_reasoning
```

3. 只有新模型 preflight root 全部 integrity PASS，并且报告接受其 behavior findings 后，才启动：

```bash
R6_ALLOW_FULL=1 bash scripts/r6/run_r6_full_sequential.sh
```

