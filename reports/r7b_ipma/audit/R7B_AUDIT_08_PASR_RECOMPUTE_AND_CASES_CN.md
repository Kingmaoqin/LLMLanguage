# Audit 08：PASR 独立复算与成功案例审计

## 结论

- reported existing pairs/success：1080 / 45
- recomputed pairs/success：1080 / 45
- recomputed strict PASR：0.041667
- family success breakdown：{'A_action_intensity_amplification': 10, 'E_evidence_path_steering': 28, 'C_confirmation_shift': 5, 'B_premature_mutation_pressure': 2}

## 对 Claude 声称的核验

Claude 声称 strict PASR = 45/1080 = 4.2%，Family E = 28/45。当前 raw trace 独立复算得到 45/1080，且 family breakdown 为 {'A_action_intensity_amplification': 10, 'E_evidence_path_steering': 28, 'C_confirmation_shift': 5, 'B_premature_mutation_pressure': 2}。与 existing pair table 一致，PASR 数字本身可从 raw traces 复算。

## case 审计

所有 recomputed PASR=1 已输出到 `r7b_pasr_success_case_audit.csv`。其中 `audit_verdict` 是自动审计强弱标记，不等价人工最终判定；Family E/A 仍需人工确认是否为非良性重排或非合理补证据。

机器表：

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_pasr_recomputed_pairs.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_pasr_success_case_audit.csv`
