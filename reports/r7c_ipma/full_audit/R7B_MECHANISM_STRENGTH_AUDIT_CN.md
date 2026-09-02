# R7-B mechanism strength audit

- PASR cases: 87
- strong: 0
- moderate: 66
- weak: 21
- invalid: 0
- strong+moderate PASR: 66/2160
- family counts: {'A_action_intensity_amplification': 37, 'E_evidence_path_steering': 32, 'B_premature_mutation_pressure': 13, 'C_confirmation_shift': 5}

Family E cases: 32。本轮只做 rule-based mechanism screen，未把任何 case 升为 strong；论文主结果若严格只使用 strong+moderate，应使用上面的 strong+moderate numerator，并保留 manual trace review caveat。

机器表：`results/r7c_ipma/full_audit/r7b_pasr_case_mechanism_strength.csv`
