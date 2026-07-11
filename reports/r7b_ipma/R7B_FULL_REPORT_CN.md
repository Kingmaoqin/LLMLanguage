# R7-B / IPMA 修复实验代码与 smoke 报告

## 1. 当前状态

已完成 R7-B confirmatory benchmark 的代码路径和严格合成 smoke。没有启动真实模型 dev/full 实验。

## 2. 已实现模块

- `scripts/r7b_ipma/build_r7b_assets.py`
- `scripts/r7b_ipma/filter_template_contamination.py`
- `scripts/r7b_ipma/judge_template_semantic_invariance.py`
- `scripts/r7b_ipma/export_human_template_audit.py`
- `scripts/r7b_ipma/check_pairing_invariants.py`
- `scripts/r7b_ipma/evaluate_endpoint_from_snapshot.py`
- `scripts/r7b_ipma/compute_pasr_metrics.py`
- `scripts/r7b_ipma/run_statistical_analysis.py`
- `scripts/r7b_ipma/processguard/runtime.py`
- `scripts/r7b_ipma/run_r7b_smoke.py`

## 3. 已生成资产

- `data/r7b_ipma/r7b_task_registry.csv`
- `data/r7b_ipma/r7b_condition_templates.jsonl`
- `data/r7b_ipma/frozen/r7b_dev_tasks.jsonl`
- `data/r7b_ipma/frozen/r7b_test_tasks.jsonl`
- `data/r7b_ipma/frozen/r7b_frozen_templates.jsonl`
- `data/r7b_ipma/frozen/r7b_task_family_registry.csv`
- `data/r7b_ipma/frozen/r7b_pasr_thresholds.json`

## 4. Smoke 结果

- synthetic traces：288
- template rule filter：1800/1800 PASS
- offline semantic judge：1800/1800 PASS
- human template audit sample：100 rows exported
- pairing invariant：240/240 PASS
- endpoint oracle：288/288 supported
- strict pair table：240 rows
- strict PASR smoke successes：60
- pipeline commands：8/8 PASS

## 5. 关键解释

R7-B 的核心修复是把 confirmatory PASR 的 denominator 收紧：只有同时满足 pairing invariant、semantic invariance、endpoint oracle supported、safety preserved、endpoint_not_worse、policy_not_worse、family threshold、neutral noise floor 的 pair 才能进入 confirmatory PASR。

## 6. 仍未完成

- 真实模型 dev smoke：未运行。
- LLM semantic judge：未运行。
- human template audit：仅导出样本，未回填标注。
- full run：未运行。
- ProcessGuard defense experiment：未运行。

## 7. 是否达到 confirmatory attack benchmark 标准？

尚未达到。当前完成的是代码和 smoke。要达到标准，必须先跑真实 dev smoke，并满足：

- 0 missing trace
- 0 pairing invariant fail
- 0 endpoint unsupported in confirmatory tasks
- template audit 闭环
- per-run metrics 可从 raw trace 复算
- PASR 逐例解释表可审计

