# R6 模型选择与本地部署记录

日期：2026-06-25

## 当前可用本地端点

| 模型别名 | 端口 / served id | GPU | 状态 | 说明 |
|---|---:|---:|---|---|
| `gemma4_31b` | `8005 / g4` | GPU0 | 已部署，可用 | R5 对照模型，vLLM + gemma4 parser |
| `gpt_oss_120b` | `8192 / gpt-oss` | GPU1-2 | 已部署，可用 | R5 对照模型，TP=2，OpenAI tool parser |
| `llama3_3_70b_fp8` | `8007 / llama33-70b-fp8` | GPU3 | 已部署，可用 | R6 新候选 fallback；8192 context 失败，4096 context 可运行 |

## 资源处理

- 停止了旧的 `multiaiagent/scripts/run_phase2_full_dual.sh` 及其子进程；这些进程会反复调用 `8005/8192`，会污染 R6 preflight。
- 停止了另一个并发 R6 runner：`results/r6_sensitivity/preflight_live_20260625_0459`，避免两个 R6 live 进程同时打同一端点。
- 当前 R6 主 preflight 使用新输出根：`results/r6_sensitivity/model_preflight_mixed_reviewfix_20260625`，未覆盖旧结果。

## R6 候选模型可行性核对

基于 Hugging Face Hub 元数据和本地部署状态：

| 候选 | HF 状态 | 本地状态 | R6 处理 |
|---|---|---|---|
| `CohereLabs/c4ai-command-a-03-2025` | gated；`cohere2` 架构 | 未部署 | 保留为候选；需要权限/兼容性预检 |
| `nvidia/Llama-3_3-Nemotron-Super-49B-v1_5` | 可见；`nemotron-nas` custom code | 未部署 | 保留候选；需要单独 vLLM/Transformers 兼容性预检 |
| `meta-llama/Llama-4-Scout-17B-16E-Instruct` | gated；多模态架构 | 未部署 | 暂不进入 full |
| `mistralai/Mistral-Large-Instruct-2411` | vLLM tag；约 122B | 未部署 | 4×A100 可行性未确认；暂不进入 full |
| `meta-llama/Llama-3.3-70B-Instruct` | gated；70B | 本地 FP8 fallback 已部署 | 可作为 Mistral fallback；已做 custom smoke |

结论：R6 指导中“新增 4 个非中国模型”的目标尚未完全满足。当前只能安全进入的 live preflight 是 R5 两个对照模型 + Llama3.3 70B FP8 fallback 的局部预检；不能声称 4 个新模型 full-ready。

