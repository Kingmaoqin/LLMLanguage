# R6 full 启动状态报告

生成时间：2026-06-26

## 1. Gemma3 / OLMo2 完善结果

### `gemma3_27b`

状态：未能完善，外部授权阻塞。

执行下载：

```bash
hf download google/gemma-3-27b-it --local-dir /home/xqin5/hf_p08_models/gemma-3-27b-it ...
```

结果：

```text
Error: Access denied. This repository requires approval.
```

说明：当前 HF 账号可以读取仓库元数据，但没有下载权重授权。需要在 Hugging Face 上接受/获得 `google/gemma-3-27b-it` 的 gated license approval 后才能下载。该问题不是本地脚本问题。

### `olmo2_32b`

状态：权重已补齐，backend 可启动，但不适合标准 R6 full。

处理过程：

- 发现旧 `/tmp/hf_download.py` 进程持有 OLMo2 下载锁。
- 停止旧下载进程。
- 清理本地 HF 下载残留 `.lock`。
- 使用 `hf download allenai/OLMo-2-0325-32B-Instruct --force-download --max-workers 1` 补齐。
- 本地 shard 数从不完整状态补齐到 `14/14`。

后续 smoke：

- vLLM 启动成功。
- `/v1/models` endpoint health 成功。
- 但标准 tau2 R6 smoke 在 retail case 中超过 4096 context：

```text
This model's maximum context length is 4096 tokens.
requested 768 output tokens and prompt contains at least 3329 input tokens,
total at least 4097 tokens.
```

结论：OLMo2 backend 已验证可加载，但其本地 config 最大上下文为 4096，不满足标准 R6 full 的 60-step tau2 协议。除非单独声明 reduced-context protocol，否则不纳入标准 full。

## 2. 标准 full 已启动

启动命令：

```bash
R6_ALLOW_FULL=1 R6_FULL_ROOT=results/r6_sensitivity/full_main_seq_eligible_20260626 \
  bash scripts/r6/run_r6_full_sequential.sh
```

输出目录：

```text
results/r6_sensitivity/full_main_seq_eligible_20260626
```

纳入模型：

- `gemma4_31b`
- `gpt_oss_120b`
- `mistral_small_3p2`

未纳入模型：

- `gemma3_27b`：HF gated 权重下载未获授权。
- `olmo2_32b`：backend 可启动，但 4096 context 不满足标准 R6 full。
- `phi4_reasoning`：只通过 limited smoke，不作为标准 full 质量比较模型。

## 3. 当前运行状态

截至最近检查：

- full 进程仍在运行。
- baseline 阶段运行中。
- 已写入 traces：6
- 当前 trace 示例：
  - `gemma4_31b__r6_retail_01_order_options__neutral_clean__seed300__temp0.0.trace.json`
  - `gemma4_31b__r6_retail_01_order_options__praise_trust_clean__seed302__temp0.0.trace.json`

后续完成后需要自动/手动检查：

```bash
conda run -n agentsearch python scripts/r6/final_integrity_audit_r6.py \
  --root results/r6_sensitivity/full_main_seq_eligible_20260626 \
  --report reports/r6_sensitivity/R6_FULL_INTEGRITY_<timestamp>.md

conda run -n agentsearch python scripts/r6/extract_r6_metrics.py \
  --root results/r6_sensitivity/full_main_seq_eligible_20260626
```

`run_r6_full_sequential.sh` 已在脚本末尾自动调用 integrity、metrics、statistical analysis 和 interactional profile；若中途失败，应先看脚本 stdout 和对应 logs。
