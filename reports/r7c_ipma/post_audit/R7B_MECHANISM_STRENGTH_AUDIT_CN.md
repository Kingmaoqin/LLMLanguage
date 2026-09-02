# R7-B mechanism strength audit

- PASR cases: 45
- strong: 0
- moderate: 44
- weak: 1
- invalid: 0
- strong+moderate PASR: 44/1080
- family counts: {'A_action_intensity_amplification': 10, 'E_evidence_path_steering': 28, 'C_confirmation_shift': 5, 'B_premature_mutation_pressure': 2}

Family E cases: 28。本轮只做 rule-based mechanism screen，未把任何 case 升为 strong；论文主结果若严格只使用 strong+moderate，应使用上面的 strong+moderate numerator，并保留 manual trace review caveat。

机器表：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/post_audit/r7b_pasr_case_mechanism_strength.csv`
