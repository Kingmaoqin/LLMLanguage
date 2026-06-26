# R6 Sensitivity-Focused Benchmark 资产与可复用性审计

日期：2026-06-24  
执行范围：按 `/home/xqin5/llmlanguage/第六轮实验指导` 的 P0 gate 执行。  
状态：仅做仓库、脚本、报告、本地 benchmark 资产与模型服务检查；未启动任何 R6 新实验。

## 0. Gate 结论

P0 审计结论如下：

1. R5 的 measurement-complete trace schema、token 修复、interactional metrics、noise floor 和配对统计分析可以作为 R6 的主测量骨架复用。
2. R5/R4 当前有效主实验仍然是 retail-only、2 模型、8 tasks、6 conditions；这不足以解释跨域、压力因子、Layer C privacy/refusal/unsafe/boundary 敏感性。
3. 本地已有 tau2/tau-bench 风格资产，尤其是 `retail` 和 `airline`；但 calendar/email/workspace/travel/hotel/file/privacy 不能直接从当前 active path 得到完整可跑环境，需要 R6 新增最小 deterministic env 或适配层。
4. R5 evaluator 已支持 final state、confirmation、evidence-before-mutation、prohibited mutation、boundary regex 和 user-abandonment marker；但 R6 指导要求的 privacy_violation、unsafe_compliance、correct_refusal、over_refusal、agent-side abandonment、field-level DB diff 尚未完整实现。
5. 当前 trace 含对话、工具事件、状态 hash、state_deltas、policy failures、branch decisions、final state、token usage；缺字段级 state diff 和 per-tool latency 的稳定字段。
6. 当前在线模型服务只有 Gemma 与 GPT-OSS；本地还有 Llama-3.3、Command、Nemotron 等权重目录，但 R6 不能直接纳入 full，必须先做模型 preflight。
7. 因此下一步允许进入 P1 task/template 构造与测试；仍不得启动 pilot/full 实验，直到 task/template/model preflight 均完成。

## 1. 仓库状态

执行的指导命令：

```bash
git status --short
git branch --show-current
git log --oneline -n 10
find . -maxdepth 4 -type f | sort > reports/r6_sensitivity/repo_file_inventory.txt
```

当前分支：

```text
r5-measurement-repair
```

最近提交：

```text
86fa32d Stage-2.5b R4 minimal repair + R4.1 full rerun
59ec4a9 Stage-2.5b round-4: confirmatory run, analysis, and reports
ed800bc Repair scripted-user classification on real prompts
d028058 Repair the canonical mutation-tool boundary
14ab414 Refreeze tau2 benchmark provenance
b94890a Archive replaced Stage-2 and Stage-2.5 implementations
885f63e Freeze scripted-user and contrast quality gates
b37e64b Switch runtime to frozen scripted-user policies
c5608f9 Freeze scripted-user policies and response library
f664f8f Enforce a self-contained Stage-2.5b active path
```

工作区已有 R5 未提交改动：

```text
 M README.md
 M src/adapters/normalize.py
?? artifacts/stage2_5b/run_measurement_complete_full_r5.sh
?? configs/stage2_5b/measurement_complete_rerun.yaml
?? reports/measurement_repair/
?? reports/r6_planning/
?? reports/stage2_5b/run_blocks_measurement_complete_full_r5/
?? scripts/stage2_5b/analyze_interactional_robustness_profile.py
?? scripts/stage2_5b/estimate_noise_floor.py
?? scripts/stage2_5b/extract_interactional_metrics.py
?? scripts/stage2_5b/reconstruct_traces_from_existing_artifacts.py
?? scripts/stage2_5b/run_measurement_complete_experiment.py
?? src/stage2_5b/metrics/
?? tests/stage2_5b/test_trace_metrics.py
?? tests/stage2_5b/test_trace_schema.py
```

R6 文件清单已写入：

- `reports/r6_sensitivity/repo_file_inventory.txt`

这说明 R6 必须避免覆盖 R4/R4.1/R5；新增内容应只进入 `results/r6_sensitivity/`、`reports/r6_sensitivity/`、`configs/r6/`、`data/r6/`、`tests/r6/`、`scripts/r6/`。

## 2. R5 代码、trace schema、metric extractor、analysis 是否可复用

可复用，建议作为 R6 基础层。

### 可直接复用的组件

| 类别 | 文件 | R6 复用判断 |
|---|---|---|
| 运行器骨架 | `scripts/stage2_5b/run_measurement_complete_experiment.py` | 可复制/适配为 R6 runner，保留 atomic bundle、trace、metrics 输出逻辑 |
| block 调度 | `scripts/stage2_5b/run_full_blocks.py` | 可适配为 R6 preflight/pilot/full block launcher |
| trace 重建 | `scripts/stage2_5b/reconstruct_traces_from_existing_artifacts.py` | 可复用 trace bundle 读取与 schema 校验，但 R6 需扩展字段 |
| interactional metrics | `scripts/stage2_5b/extract_interactional_metrics.py` | 可复用提取框架，R6 需新增 privacy/refusal/field-diff 指标 |
| profile 分析 | `scripts/stage2_5b/analyze_interactional_robustness_profile.py` | 可复用维度化分析和 FDR 框架 |
| noise floor | `scripts/stage2_5b/estimate_noise_floor.py` | 可复用 seed 噪声地板估计 |
| confirmatory analysis | `scripts/stage2_5b/analyze_confirmatory.py`、`scripts/stage2_5b/task_cluster_bootstrap.py` | 可复用配对/cluster 思路，需扩展到 factorial effects |
| trace schema | `src/stage2_5b/metrics/trace_metrics.py` | 可作为 R6 canonical trace v1 的基线 |
| token 修复 | `src/adapters/normalize.py` 与 `src/stage2_5b/metrics/trace_metrics.py` | 可复用；R6 应继续记录 token_source |
| deterministic user | `src/stage2_5b/controlled_user.py` | 可复用设计原则，但 R6 需多域 policy 与 3-turn matched behavior |
| evaluator | `src/stage2_5b/evaluator.py` | 可复用 final state / evidence / confirmation / mutation policy 逻辑 |

### R5 trace schema 现状

`src/stage2_5b/metrics/trace_metrics.py` 当前 canonical trace 顶层字段：

```text
schema_version
run_id
run_meta
conversation
tool_events
state_deltas
controlled_user_events
policy_failures
branch_decisions
final_environment_state
token_usage
```

R5 interactional profile 当前包含 6 个维度：

1. endpoint：safe_task_success、local_proxy_success、final_state_correct
2. tool：agent_tool_calls、unique_tools、read_calls、write_calls、tool_errors、n_state_mutations
3. trajectory：tool_name_sequence_norm_distance、critical_argument_sequence_norm_distance、mutation_sequence_norm_distance
4. policy：policy_failure_any、mutation_before_evidence、required_fact_coverage
5. efficiency：tokens_total、duration_s、self_repair_count
6. conversation：boundary_setting_count、user_abandonment_markers、assistant_text_turns

R6 应保留这个结构，但新增安全/拒绝/隐私/字段级差异维度，不能只靠 endpoint。

## 3. 当前任务域和可用 benchmark 资产

### 当前 active repo 主实验任务域

R5/R4 active confirmatory path 的主任务：

- `data/stage2_5b/calibrated_tasks_frozen.yaml`
- `data/stage2_5b/task_user_policies.yaml`
- `data/stage2_5b/task_policy_annotations.yaml`

有效任务为 8 个 `retail_*` task：

```text
retail_2
retail_6
retail_19
retail_21
retail_23
retail_28
retail_41
retail_64
```

结论：当前主实验是 retail-only。R5 诊断报告已指出：不显著结果最可能与 domain/task layer 太窄、pure valence 太温和、有效 task cluster 只有 8 个有关。

### 仓库内历史/辅助资产

仓库内存在 airline calibration 日志与 benchmark snapshot 资产，例如：

- `artifacts/stage2_5b/benchmark_snapshot/`
- `artifacts/stage2_5b/logs/calibration_cp012_gemma_shard_airline_*.log`
- `artifacts/stage2_5b/candidate_task_scan.json`
- `artifacts/stage2_5b/tau_snapshot_manifest.json`

但这些并未进入 R5 confirmatory active matrix。

进一步只读扫描确认：

- `data/stage2_5b/candidate_tasks.csv` 中有 24 个 retail 与 7 个 airline 结构候选。
- `data/stage2_5b/task_user_policies.yaml` 已含 retail policy，并含 `airline_7`、`airline_12`、`airline_44`。
- `data/stage2_5b/task_policy_annotations.yaml` 已含 legacy retail/airline annotations 与 R5 active retail annotations。
- `data/irmstu_tasks/tau_adapted_tasks.yaml` 有 legacy 3 retail + 3 airline mapped tau2 tasks。
- 当前 repo 的 frozen benchmark snapshot 可确认主要覆盖 retail + airline；更广域 tau2-bench 资产存在于外部本地目录，不等同于已冻结到当前 repo 的 active snapshot。

### 本地 tau2/tau-bench 资产

本地发现：

- `/home/xqin5/tau2-bench`
- `/home/xqin5/tau2-bench/data/tau2`
- `/home/xqin5/tau2-bench/data/tau2/domains/airline`
- `/home/xqin5/tau2-bench/data/tau2/domains/retail`
- `/home/xqin5/tau2-bench/data/tau2/domains/telecom`
- `/home/xqin5/tau2-bench/data/tau2/domains/banking_knowledge`
- `/home/xqin5/tau2-bench/data/tau2/domains/mock`

其中 `airline` 与 `retail` 都有 `tasks.json`、`db.json`、`policy.md` 等典型可适配材料。`telecom`、`banking_knowledge`、`mock` 是否适合作为 R6 action-taking task，需要再做 schema 适配审计。

### 其他本地任务资产

发现以下本地资产，但不能直接视为 R6 可跑 benchmark：

- `/home/xqin5/multiaiagent/artifacts/task_audit/all_tasks.csv`
- `/home/xqin5/multiaiagent/artifacts/task_audit/included_tasks.csv`
- `/home/xqin5/multiaiagent/src/ravel_core/policy_checks.py`
- `/home/xqin5/multiaiagent/results/.../airline...`
- `/home/xqin5/cbench/oh/benchmarks/workspace/...`
- `/home/xqin5/reactproject/tau2-agentbeats`
- `/home/xqin5/reactproject/tau2-agentbeats-leaderboard`

判断：

1. `multiaiagent` 里有 airline task audit/dependency graph 资产，适合辅助 R6 选 airline/travel task。
2. `cbench/oh/benchmarks/workspace` 更像 workspace conversation/event/base_state 资产，不是当前 R6 runner 可直接调用的 deterministic tool env。
3. 未在浅层扫描中发现可直接复用的 AgentDojo 或 ToolSandbox active runner 目录；如后续需要，可做更深层专项扫描，但不能把它们假定为可用。

仓库历史文档 `reports/BENCHMARK_INVENTORY.md` 也记录 AgentDojo 资产 absent；ToolSandbox 未发现直接匹配。因此 R6 不应在报告中宣称已使用 AgentDojo/ToolSandbox。

## 4. 对指导中任务域的逐项回答

| 指导域 | 当前可用性 | 结论 |
|---|---|---|
| retail | 高 | R5 已稳定运行；R6 可保留 8 个左右 retail task，但要加入 A/B/C 分层 |
| calendar | 低 | 当前 active repo 未发现完整 calendar env；需要新建 minimal deterministic env 或引入外部资产 |
| email/workspace | 中低 | 本地有 workspace traces/base_state，但未证明可直接跑；email 需要新建或适配 |
| travel/airline/hotel | 中 | airline 可从 tau2-bench 适配；hotel 未发现现成 env |
| file/message/privacy | 低 | 未发现完整可跑 env；建议 R6 新增最小 deterministic file/message/privacy env |
| other | 中 | telecom/banking_knowledge/mock 可作为备选，但需确认是否满足 action-taking 与 policy/refusal 需求 |

## 5. controlled_user 是否支持 multi-domain

当前 `src/stage2_5b/controlled_user.py` 的优点：

1. 明确禁止 runtime LLM user：`llm` 必须为 `None`、空字符串或 `controlled_user_no_llm`。
2. 使用 frozen policy 与 response library，保证 deterministic user。
3. policy resolution 支持 `source_task_id` 和 `domain` 维度。
4. 已有 clean_text_hash / clean_user_signature 等记录，支持跨 condition 内容一致性审计。

当前限制：

1. 现有 policy YAML 主要围绕 retail calibration/confirmatory task。
2. R6 要求所有条件 3-turn matched，而 R5 有 first_turn_only 与 every_user_turn 两类，不满足 R6 factorial design。
3. R6 需要用户在 privacy/refusal/boundary task 中稳定给出或拒绝给出某些信息；当前 controlled user 没有完整的多域 privacy/unsafe/boundary policy schema。
4. R6 pressure factor 需要在不改变任务事实的前提下表达 authorization/urgency/continuation pressure；当前 wrapper 不包含这个 factor label 与审计字段。

结论：controlled_user 设计可复用，但 R6 需要新增 `data/r6/r6_task_user_policies.yaml`、R6 policy loader 或兼容适配层，并强制所有 condition 的 user turns 数量相同。

## 6. evaluator 支持范围

当前 `src/stage2_5b/evaluator.py` 支持：

| 指标/行为 | 当前支持 | 备注 |
|---|---:|---|
| final_state_correct | 是 | 使用 local proxy / official reward basis 部分 |
| safe_task_success | 是 | 组合 local_proxy_success、invalid_run、policy failure、mutation_before_evidence |
| confirmation_before_action | 部分支持 | structured confirmation 与 mutation-before-evidence 已有 |
| policy_failure_any | 是 | policy_failures 输出 |
| prohibited mutation | 是 | task annotations 可定义 prohibited_mutations |
| boundary setting | 部分支持 | 基于 assistant text regex，非结构化分类器 |
| user abandonment marker | 部分支持 | conversation-management 级 marker，不等同 agent-side abandonment |
| field-level DB diff | 否 | 当前主要是 state_deltas 与 before/after hash |
| privacy_violation | 否 | 需要新增 policy annotation + evaluator |
| unsafe_compliance | 否 | 需要新增 unsafe/boundary task semantics |
| correct_refusal | 否 | 需要区分应该拒绝 vs 错误拒绝 |
| over_refusal | 否 | 需要判断 benign task 被拒绝 |
| agent-side abandonment | 否 | 需要检测 agent 未完成但停止/转人工/放弃 |
| continued_task_after_boundary | 否 | 需要 boundary 后继续执行/拒绝执行的结构化标记 |

结论：R6 evaluator 不能只复制 R5。必须在 R6 adapter/evaluator 中显式产生上述新指标，并加入测试。

## 7. trace 字段完整性

R5 measurement-complete trace 当前可提供：

| 字段 | 当前状态 |
|---|---|
| tool args | 有，来自 `normalized_tool_events` / bundle |
| tool result | 有，来自 normalized events |
| tool error | 有 |
| state before/after hash | 有 |
| state_deltas | 有 |
| final_environment_state | 有 |
| branch decisions | 有 |
| policy failures | 有 |
| confirmation metadata | 有，但需按 R6 指标进一步结构化 |
| conversation text | 有 |
| token usage | 有，R5 已修复 total token recompute 与 token_source |
| per-tool latency | 不稳定/不足 |
| structured field-level diff | 缺失 |
| privacy/unsafe/refusal flags | 缺失 |

更细粒度字段扫描显示，当前 `tool_events` 通常含：

```text
tool_name
arguments
tool_result
tool_error
valid_json
undefined_tool
step_index
turn_idx
mutation_type
irreversible_action
policy_relevant
branch_relevant
state_before_hash
state_after_hash
mutated
```

`controlled_user_events` 通常含：

```text
speech_act
decision
confirmation_value / confirmation
factual_slots / structured_slots
clean_text / styled_text / clean_text_hash
wrapper_event
state_before / state_after
```

R6 trace schema 建议升级为 `r6_trace_v1`，在保留 R5 字段的基础上新增：

```text
field_level_state_diff
tool_latency_ms
privacy_events
unsafe_events
refusal_events
confirmation_events
boundary_events
agent_abandonment_events
```

## 8. 模型资产与部署可行性

### 当前在线服务

`ss -ltnp` 当前显示：

| 端口 | 进程 | R5/R6 解释 |
|---:|---|---|
| 8005 | `vllm` | 已在线，R5 Gemma service |
| 8192 | `vllm` | 已在线，R5 GPT-OSS service |
| 7862 | `python` | 非 R5/R6 模型服务，需避免误纳入 |
| 8011 | unknown listener | 未确认 OpenAI-compatible 服务 |

### 本地模型目录

`/home/xqin5/hf_p08_models` 下存在：

| 目录 | R6 初判 |
|---|---|
| `gemma-4-31B-it` | 已在线，可作为 continuity baseline |
| `gpt-oss-120b` | 已在线，可作为 continuity baseline |
| `Llama-3.3-70B-Instruct-FP8` | 有权重，最现实的新候选；必须验证 vLLM 启动和 tool-call parser |
| `command-a-plus-w4a4` | 有权重，但 R5 记录 vLLM/transformers/W4A4 on A100 未验证 |
| `Nemotron-3-Super-120B-A12B-FP8` | 有权重，但 R5 记录 ModelOpt FP8 需要 compute capability >= 8.9，A100 为 8.0，不建议优先 |

R5 `configs/stage2_5b/models.yaml` 明确只把 `gemma4_31b` 与 `gpt_oss_120b` 纳入可运行模型；Command 与 Nemotron 被记录为 deployment failure / not-run。R6 要求 “四个非中国本地开源模型”，因此模型扩展必须做 preflight，不能直接 full。

建议 R6 preflight 候选顺序：

1. `gemma4_31b`：continuity baseline。
2. `gpt_oss_120b`：continuity baseline。
3. `llama3_3_70b_fp8`：本地权重存在，优先验证。
4. `command_a_plus_w4a4`：只在 vLLM/transformers/tool parser 验证后纳入。
5. `nemotron_super_120b_fp8`：硬件兼容风险高，除非更换 GPU 或确认可用 runtime。
6. 如必须凑满 4 个非中国模型，可考虑从本地已有模型之外重新下载/部署，但这需要网络和存储许可，当前 P0 未授权。

## 9. 缺口与最小新增模块

R6 最小新增模块如下：

| 优先级 | 模块 | 输出路径 | 必要性 |
|---|---|---|---|
| P1 | R6 task schema 与 30 task YAML | `data/r6/r6_tasks.yaml` | 必须；解决 domain/layer narrow |
| P1 | R6 user policies | `data/r6/r6_task_user_policies.yaml` | 必须；保持 deterministic user |
| P1 | R6 policy annotations | `data/r6/r6_task_policy_annotations.yaml` | 必须；支持 confirmation/privacy/unsafe/refusal/field diff |
| P1 | R6 seed state | `data/r6/r6_environment_seed_states/` | 必须；支持 multi-domain deterministic env |
| P1 | R6 social templates | `data/r6/r6_social_style_templates.yaml` | 必须；实现 valence × pressure factorial 且 3-turn matched |
| P1 | template/task tests | `tests/r6/` | 必须；防止任务事实污染和 turn-count mismatch |
| P2 | model preflight config | `configs/r6/` | 必须；避免不可部署模型进入 full |
| P2 | R6 runner | `scripts/r6/run_r6_experiment.py` | 必须；只写 R6 输出路径 |
| P2 | R6 trace/metric extractor | `scripts/r6/extract_r6_metrics.py` | 必须；新增安全/拒绝/字段 diff 指标 |
| P2 | final integrity audit | `scripts/r6/final_integrity_audit_r6.py` | 必须；full 前后 gate |
| P3/P4 | analysis scripts | `scripts/r6/analyze_r6_interactional_profile.py`、`estimate_r6_noise_floor.py`、`statistical_analysis_r6.py` | pilot/full 后需要 |

## 10. 下一步执行建议

严格按第六轮指导，下一步不启动实验，只进入 P1：

1. 构造 `data/r6/r6_tasks.yaml`，先覆盖 30 个任务的 schema、domain、layer、policy requirements，不连接 runner。
2. 构造 `data/r6/r6_social_style_templates.yaml`，8 条 condition 全部 3-turn matched。
3. 写 task/template 审计报告：
   - `reports/r6_sensitivity/R6_TASK_DESIGN_REPORT.md`
   - `reports/r6_sensitivity/R6_TEMPLATE_AUDIT.md`
4. 写并运行 R6 schema/template tests。
5. 每新增一个 `scripts/r6/*.py`，按用户要求启动 review agent 检查代码正确性并及时修复。

## 11. 当前 gate 状态

| Gate | 状态 |
|---|---|
| P0 repo inventory | 完成 |
| P0 R5 reusable code audit | 完成 |
| P0 local benchmark asset scan | 完成 |
| P0 model availability/deployment scan | 初步完成；正式 preflight 待 P2 |
| P0 no-experiment rule | 遵守 |
| P1 task/template construction | 待执行 |
| P2 model preflight | 未开始 |
| P3 pilot | 未开始 |
| P4 full | 未开始 |
