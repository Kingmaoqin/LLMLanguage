# R5 模型覆盖范围审计

日期：2026-06-24  
目的：解释本地存在其他大模型权重/部署脚本时，R5 measurement-complete 实验为什么只使用 Gemma4-31B 与 GPT-OSS-120B。

## 1. 当前实际在线服务

`nvidia-smi` 与 `ss -ltnp` 显示当前实际在线的 OpenAI-compatible vLLM 服务为：

| 端口 | served id | 权重路径 | GPU 使用 |
|---:|---|---|---|
| 8005 | `g4` | `/home/xqin5/hf_p08_models/gemma-4-31B-it` | GPU2，约 79GB |
| 8192 | `gpt-oss` | `/home/xqin5/hf_p08_models/gpt-oss-120b` | GPU1+GPU3，TP=2，约 74GB×2 |

端口 `8002`、`8003`、`8004` 当前没有可访问的 `/v1/models` 服务。

## 2. R5 配置为何只纳入两个模型

R5 使用的配置是：

- `configs/stage2_5b/measurement_complete_rerun.yaml`
- `configs/stage2_5b/models.yaml`

其中矩阵明确写死为：

```yaml
matrix:
  models: [gemma4_31b, gpt_oss_120b]
```

`configs/stage2_5b/models.yaml` 也只定义了两个可运行候选：

- `gemma4_31b` → `http://127.0.0.1:8005/v1`
- `gpt_oss_120b` → `http://127.0.0.1:8192/v1`

同一文件中明确记录了未纳入模型的原因：

| 模型 | 状态 | 原因 |
|---|---|---|
| `command_a_plus` | 未纳入 | `vLLM 0.20.2 / local transformers path does not support cohere2_moe; W4A4 path is not validated on A100.` |
| `nemotron_super_120b` | 未纳入 | `ModelOpt FP8 checkpoint requires compute capability >= 8.9; A100 is 8.0.` |

因此 R5 没有用其他模型，不是分析脚本漏读，而是实验矩阵主动限定。

## 3. 本地确实存在其他模型权重

本地 `/home/xqin5/hf_p08_models` 下存在：

| 模型目录 | 大小 | 备注 |
|---|---:|---|
| `Llama-3.3-70B-Instruct-FP8` | 68G | 有权重，但未写入 R5 stage2_5b 模型配置 |
| `Nemotron-3-Super-120B-A12B-FP8` | 120G | 有权重，但配置中标记 A100 不兼容 |
| `command-a-plus-w4a4` | 123G | 有权重，但配置中标记 vLLM/transformers/硬件路径未验证 |
| `gemma-4-31B-it` | 59G | R5 已使用 |
| `gpt-oss-120b` | 183G | R5 已使用 |

另外发现 `/home/xqin5/start_engine.sh` 和 `/home/xqin5/kvprobe.sh` 中有 Qwen3.6-27B 的 vLLM 启动脚本，目标端口 `8190`，但当前 `ss -ltnp` 没有看到 `8190` 在线服务，且该模型不在 R5 `stage2_5b` 配置中。

## 4. 为什么不能直接把这些模型混进 R5 主结果

R5 是 confirmatory / measurement-complete 复现实验，关键要求是与 R4.1 的任务、模板、用户、evaluator、模型集合保持可比。直接加入新模型会改变实验矩阵与多重比较族，导致：

1. 与 R4/R4.1 的复现比较不再一一对应；
2. 原 480 runs 设计会变成 720/960/1200+ runs，需要重新定义功效和 FDR family；
3. 新模型必须先通过 OpenAI tool-call 兼容性、served id、temperature、max context、工具解析器、controlled-user trace 完整性等预检；
4. Command A+ / Nemotron 在现有记录里已有硬件或 vLLM 兼容性风险；
5. Llama/Qwen 虽然本地存在或有脚本，但还没有进入 `configs/stage2_5b/models.yaml`，也没有 R5 级别的 smoke/preflight 证据。

## 5. 后续建议

如果要扩展模型覆盖，应作为 R6 / RQ5 多模型扩展，而不是回改 R5 主实验。

建议流程：

1. 新建 `configs/stage2_5b/models_r6_extended.yaml`，保留 R5 两模型，同时新增 Llama/Qwen 等候选。
2. 对每个新模型先启动独立端口，并跑 `/v1/models` 与 tool-call preflight。
3. 先跑 2 tasks × 6 conditions × 1 seed 的 smoke。
4. smoke 通过后再决定是否跑 full。
5. R6 报告单独建分析族，不与 R5 的 480-run confirmatory 结果混合。

当前最现实的候选顺序：

1. **Llama-3.3-70B-Instruct-FP8**：权重完整，A100 上更可能可跑；但需要验证工具调用格式。
2. **Qwen3.6-27B**：已有启动脚本，但属于另一路径 `/home/xqin5/agentsearch/models/Qwen3.6-27B`，需确认模型文件与 parser。
3. **Command A+ / Nemotron**：已有配置层失败原因，不建议优先投入，除非先解决 A100/vLLM/工具解析问题。
