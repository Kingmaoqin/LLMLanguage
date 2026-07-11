# R6 多模型 smoke 审查与修复报告

生成时间：2026-06-26  
范围：只运行尚未干净通过的新增候选模型 smoke；已正确通过的 `gemma4_31b`、`gpt_oss_120b` 未重复运行。

## 1. 本轮修复

### 1.1 preflight runner 输出隔离

修复 `scripts/r6/run_preflight_all_models.sh`：

- 每个模型写入独立子目录，避免复用旧 `results/r6_sensitivity/model_preflight` 导致 manifest/traces 混污染。
- 默认输出根改为带时间戳的新目录；本轮显式使用 clean roots。
- 若模型输出目录已存在，则拒绝复用。

### 1.2 Bash 失败传播

发现原 runner 在 `if run_preflight_for_model; then` 语境下，函数内部失败命令不会可靠触发整体失败，导致 `Phi4 0 traces + integrity FAIL` 被误报为 `PASSED`。

已修复为：

- `run_r6_live.py` 失败：立即 `return 1`
- `final_integrity_audit_r6.py` 失败：立即 `return 1`
- `extract_r6_metrics.py` 失败：立即 `return 1`
- 批处理末尾只要存在失败模型，脚本整体 `exit 1`

### 1.3 OLMo2 启动参数

OLMo2 本地 config 派生最大上下文为 `4096`，原脚本使用 `16384`，vLLM 直接拒绝启动。

已修复：

- `scripts/r6/run_preflight_all_models.sh`: `olmo2_32b --max-model-len 4096`
- `configs/r6/r6_models.yaml`: `olmo2_32b.max_model_len: 4096`

修复后仍失败，原因见第 3 节。

### 1.4 Phi4 reasoning smoke 上限

Phi4-reasoning 在 tau2 live 分支中会长时间输出 `<think>`，原 `run_r6_live.py` 未向 LiteLLM/OpenAI 请求传 `max_tokens`，导致 smoke 第一条长时间不落盘。

已修复：

- `scripts/r6/run_r6_live.py` 支持模型级：
  - `max_tokens_per_turn`
  - `request_timeout_seconds`
  - `max_steps_override`
- `configs/r6/r6_models.yaml` 对 `phi4_reasoning` 设置：
  - `max_tokens_per_turn: 512`
  - `max_steps_override: 12`
  - `request_timeout_seconds: 120`

说明：Phi4 limited smoke 只证明端点、tool parser、trace schema、metrics 管线可用；不用于和其他模型做质量/鲁棒性比较。

## 2. 已通过 smoke 的模型

| 模型 | 运行目录 | traces | schema invalid | integrity | metrics | 备注 |
|---|---:|---:|---:|---|---|---|
| `mistral_small_3p2` | `results/r6_sensitivity/model_preflight_clean_20260626/mistral_small_3p2` | 16/16 | 0 | PASS | PASS | clean-root 重跑通过 |
| `phi4_reasoning` | `results/r6_sensitivity/model_preflight_phi4_limited_20260626/phi4_reasoning` | 16/16 | 0 | PASS | PASS | limited smoke，通过但不作为质量比较 |

### 2.1 Mistral 指标摘要

- `policy_failure_any=True`: 5/16
- `over_refusals`: 2/16
- `agent_side_abandonment`: 2/16
- `privacy_violations`: 0
- `unsafe_compliance`: 0

结论：Mistral 的部署、tool parser、trace schema、指标抽取已经可用；但行为失败必须在报告中保留，不可把 smoke 通过解释为任务质量通过。

### 2.2 Phi4 指标摘要

- `policy_failure_any=True`: 0/16
- `over_refusals`: 0/16
- `agent_side_abandonment`: 0/16
- `privacy_violations`: 0
- `unsafe_compliance`: 0

注意：Phi4 使用 `max_tokens_per_turn=512` 和 `max_steps_override=12`。这使 smoke 可完成，但该结果是“部署/管线 smoke”，不是 full-quality 评估。

## 3. 阻塞模型

### 3.1 `gemma3_27b`

状态：`blocked_incomplete_local_weights`

检查结果：

- 路径：`/home/xqin5/hf_p08_models/gemma-3-27b-it`
- 现有文件：只有 `README.md`
- 缺失：`config.json` 和模型权重 shards

结论：当前不能启动 vLLM，也不能 smoke。需要先重新下载/同步权重。

### 3.2 `olmo2_32b`

状态：`blocked_vllm_checkpoint_weight_mismatch`

已做两步验证：

1. 原始失败：`--max-model-len 16384` 超过本地 config 派生上限 `4096`。
2. 修复为 `4096` 后重试，仍失败：vLLM 报大量 checkpoint weights 未初始化。

结论：这不是 smoke 脚本参数问题了，指向本地 OLMo2 权重不完整、权重格式不匹配，或当前 vLLM 后端不支持该 checkpoint 的加载方式。未重新下载/换 backend 前，不能纳入 R6 full。

## 4. 已跳过模型

以下模型此前已有正确 smoke/preflight，本轮未重复：

- `gemma4_31b`
- `gpt_oss_120b`

## 5. 验证命令

本轮通过：

```bash
bash -n scripts/r6/run_preflight_all_models.sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 conda run -n agentsearch python -m pytest tests/r6 -q
```

结果：

- `105 passed, 1 warning, 30 subtests passed`
- smoke 后 8007 已清理

## 6. 当前 full 实验 gate

可纳入下一步 full 的模型：

- `gemma4_31b`：已通过既有 smoke
- `gpt_oss_120b`：已通过既有 smoke
- `mistral_small_3p2`：本轮 clean-root smoke 通过

暂不建议纳入 full：

- `phi4_reasoning`：limited smoke 通过，但 reasoning 输出异常重复，质量比较需另设专门 capped protocol。
- `gemma3_27b`：本地权重不完整。
- `olmo2_32b`：checkpoint/vLLM 加载失败。

建议：R6 full 先按 `gemma4_31b + gpt_oss_120b + mistral_small_3p2` 三模型主线运行；Phi4 作为单独补充模型，只有在确定 capped protocol 对研究问题合理后再进入正式比较。
