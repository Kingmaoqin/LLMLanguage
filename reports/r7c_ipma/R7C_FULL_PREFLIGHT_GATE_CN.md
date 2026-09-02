# R7-C full preflight gate

- gate_pass: True
- failures: []
- endpoint-supported test tasks: 48
- minimum required tasks: 48
- planned cells: 2592
- minimum required cells: 2592
- models: ['gemma4_31b', 'gpt_oss_120b', 'mistral_small_3p2']
- seeds: [300, 301, 302]
- conditions: ['neutral_control', 'urgency_pressure', 'confidence_without_delegation', 'frustration_pressure', 'matched_presence_pressure', 'smooth_process_pressure']
- missing template cells: 0

结论：可以进入 R7-C full/smoke 前置阶段。

## task expansion dependency

新增 endpoint-supported task 不能只追加 registry 行。当前 live runner 还要求以下资产同步存在并冻结：

- `data/r6/r6_tasks.yaml` 中的 runnable task spec；
- `data/r6/r6_task_policy_annotations.yaml` 中的 expected field diffs、confirmation/refusal/privacy/unsafe annotations；
- `data/r6/r6_task_user_policies.yaml` 中的 deterministic user policy；
- seed state family / initial-state hash；
- R7-C condition templates 与 per-condition template coverage；
- task family、PASR threshold、endpoint evaluator hash 与 freeze manifest。

`data/stage2_5b/candidate_tasks.csv` 是结构候选清单，不是 runnable frozen task registry。不得把 candidate row 直接标为 `endpoint_oracle_supported=True` 进入 full run。

机器表：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/r7c_full_preflight_gate.json`
