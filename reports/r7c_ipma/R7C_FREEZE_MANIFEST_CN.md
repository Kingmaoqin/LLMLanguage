# R7-C freeze manifest

- total tasks: 48
- existing R6/R7B runnable tasks: 30
- new candidate-derived runnable tasks: 18
- templates: 2880
- domain counts: {'retail': 24, 'calendar': 6, 'email': 4, 'workspace': 2, 'airline': 4, 'hotel': 3, 'travel_privacy': 1, 'file': 2, 'message': 1, 'privacy': 1}
- family counts: {'E_evidence_path_steering': 4, 'A_action_intensity_amplification': 4, 'C_confirmation_shift': 9, 'B_premature_mutation_pressure': 23, 'D_abandonment_overrefusal_boundary': 8}
- hash manifest: `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/main/integrity/freeze_hash_manifest.json`

说明：新增任务来自 `data/stage2_5b/candidate_tasks.csv` 的 structural candidates，已转换为 R7-C minimal runnable task spec、policy annotations、deterministic user policy、registry rows and frozen templates。该冻结集用于 R7-C smoke/full 前置验证。
