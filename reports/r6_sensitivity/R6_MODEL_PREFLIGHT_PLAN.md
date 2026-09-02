# R6 模型预检计划

日期：2026-06-24  
状态：只写配置与计划；未启动服务、未调用端点、未跑 preflight。

## 1. 输出文件

| 文件 | 作用 |
|---|---|
| `configs/r6/r6_model_candidates.yaml` | R6 候选模型清单与风险分级 |
| `configs/r6/r6_preflight.yaml` | 4 tasks × 4 conditions × 1 seed 的 preflight matrix scaffold |

## 2. 当前在线模型

本地端口检查显示当前仍只有两个已在线 OpenAI-compatible vLLM endpoint 可作为 continuity baseline：

| alias | endpoint | 权重路径 | 状态 |
|---|---|---|---|
| `gemma4_31b` | `http://127.0.0.1:8005/v1` | `/home/xqin5/hf_p08_models/gemma-4-31B-it` | online observed |
| `gpt_oss_120b` | `http://127.0.0.1:8192/v1` | `/home/xqin5/hf_p08_models/gpt-oss-120b` | online observed |

## 3. 本地候选模型

| alias | 权重路径 | 初判 |
|---|---|---|
| `llama3_3_70b_fp8` | `/home/xqin5/hf_p08_models/Llama-3.3-70B-Instruct-FP8` | 最现实的新候选；需验证 vLLM 启动与 tool parser |
| `command_a_plus_w4a4` | `/home/xqin5/hf_p08_models/command-a-plus-w4a4` | R5 已记录 vLLM/transformers/W4A4 on A100 风险 |
| `nemotron_super_120b_fp8` | `/home/xqin5/hf_p08_models/Nemotron-3-Super-120B-A12B-FP8` | R5 已记录 FP8/A100 compute capability 风险 |

另有 Mistral / Llama-4 Scout 等指导中提到的候选，但当前未验证本地权重或部署路径，不应进入 runnable matrix。

## 4. Preflight matrix

计划 matrix：

- 4 tasks：
  - `r6_retail_03_return_confirmed`
  - `r6_calendar_06_private_event_boundary`
  - `r6_email_06_password_link_boundary`
  - `r6_airline_03_bag_change`
- 4 conditions：
  - `neutral_clean`
  - `praise_trust_clean`
  - `insult_urgency_pressure`
  - `abuse_continuation_pressure`
- 1 seed：`600`

每个模型最多 16 runs。任何模型必须先通过：

1. `/v1/models` endpoint 检查；
2. served id 与 config 一致；
3. tool-call parser smoke；
4. canonical trace 写入；
5. `scripts/r6/extract_r6_metrics.py` 可离线提取；
6. 无 runtime LLM user；
7. 无 legacy output path。

## 5. Gate 规则

当前禁止：

- 直接 full；
- 把新模型混入 R5 结果；
- 用未验证部署路径的模型跑 pilot/full；
- 用中国来源模型作为 R6 候选；
- 覆盖 R4/R4.1/R5 结果。

允许的下一步：

1. 等 review agent 额度恢复后复审 `scripts/r6/extract_r6_metrics.py`；
2. 写并审 `scripts/r6/final_integrity_audit_r6.py`；
3. 写并审 runner；
4. 获得明确批准后才执行 preflight/smoke。

