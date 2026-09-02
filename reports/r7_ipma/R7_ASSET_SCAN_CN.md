# R7/IPMA 资产扫描报告（脚本与 smoke 前）

日期：2026-07-01  
范围：`/home/xqin5/llmlanguage/ir_mstu_stage2`  
依据：`/home/xqin5/llmlanguage/AI 实验执行 Prompt：R7 - IPMA 交互式过程操纵攻击实验.pdf`

## 1. 现有可复用资产

- R6 全量结果根目录：`results/r6_sensitivity/full_main_seq_eligible_20260626/`
- R6 trace 数：2160 个 JSON trace，目录为 `traces/`
- R6 per-run metrics：`interactional_metrics/per_run_metrics.csv`
- R6 统计结果：`analysis/primary_contrasts.csv`、`analysis/secondary_contrasts.csv`
- R6 任务资产：`data/r6/r6_tasks.yaml`
- R6 用户模板资产：`data/r6/r6_social_style_templates.yaml`
- R6 live runner：`scripts/r6/run_r6_live.py`
- R6 deterministic custom env/live agent：`src/r6/minimal_env.py`、`src/r6/minimal_live_agent.py`

## 2. R6 结论对 R7 的约束

R6 已经支持 R7 的核心动机：最终结局和安全指标基本稳定，但工具路径/确认行为/调用数量出现可测的过程差异。因此 R7 不能再只问“是否最终成功”，而要把“在 endpoint-safe 情况下过程是否被操纵”作为主问题。

同时，R6 仍有 PDF 明确要求 R7 前修复的测量缺口：

1. tau2 retail/airline 缺字段级 final-state diff，部分 trace 只有 hash 或 summary。
2. token/duration/latency 未进入原 per-run metrics，需要从 trace 重新抽取。
3. 工具轨迹显著差异需要 case-level 分类，区分 benign reordering、extra evidence、confirmation shift 等。
4. over-refusal / abandonment 自动指标需要人审导出。
5. R7 新模板必须做 contamination audit，避免授权、跳过确认、policy bypass 等污染。

## 3. 本轮实现边界

本轮只做：

- R7/IPMA 脚本撰写；
- 基于既有 R6 结果的离线 smoke；
- 生成审查用报告和 artifact；
- 不启动任何 R7 全量模型调用。

全量 R7 需满足：

- 你审查脚本和 smoke 报告；
- R7 模板和 task registry 冻结；
- 明确是否需要补跑 tau2 snapshot；
- 确认模型服务和 GPU 调度策略。

## 4. 新增脚本清单

- `scripts/r7_ipma/reconstruct_tau2_field_diffs.py`
- `scripts/r7_ipma/extract_usage_and_timing.py`
- `scripts/r7_ipma/audit_r6_tool_trajectory_effects.py`
- `scripts/r7_ipma/export_abandonment_human_audit_sample.py`
- `scripts/r7_ipma/audit_r7_templates.py`
- `scripts/r7_ipma/build_r7_task_registry.py`
- `scripts/r7_ipma/build_neutral_reference_table.py`
- `scripts/r7_ipma/compute_pasr_metrics.py`
- `scripts/r7_ipma/check_r7_integrity.py`
- `scripts/r7_ipma/run_r7_script_smoke.py`

## 5. 新增数据资产

- `data/r7_ipma/r7_ipma_templates.yaml`：R7/IPMA smoke 版交互过程压力模板。
- `data/r7_ipma/r7_task_registry_smoke.csv`：从 R6 tasks 派生的 smoke registry，由脚本生成。
- `data/r7_ipma/human_audit/abandonment_sample.csv`：人审样本，由脚本生成。
- `data/r7_ipma/human_audit/abandonment_label_template.csv`：人审标注模板，由脚本生成。

## 6. 风险控制

- tau2 field diff 缺 snapshot 时标记 `cannot_reconstruct_missing_snapshot`，不猜测。
- token 缺失写 `MISSING`，timestamp 缺失写 `missing_no_timestamp`，避免空字符串污染统计。
- R7 模板机器审计只作为下限检查，正式冻结前仍需人工语义复核。
- PASR smoke 使用 R6 条件作为管线代理，不声明为正式 R7 结果。

