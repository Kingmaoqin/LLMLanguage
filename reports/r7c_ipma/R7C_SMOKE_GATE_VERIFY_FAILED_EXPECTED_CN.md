# R7-C smoke gate verification

- gate_pass: False
- smoke_root: `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/smoke/live_20260709_231615`
- failures: ['missing_r7c_live_summary', "endpoint_not_ok=['gemma4_31b']", 'trace_count=0 != 144', 'pair_count=0 != 120', 'missing_pasr_success_explanations', 'missing_primary_pasr_contrasts']
- trace_count: 0/144
- pair_count: 0/120
- pasr_success: 0
- endpoint_preflight: `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/smoke/live_20260709_231615/r7c_endpoint_preflight.json`
- summary: `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/smoke/live_20260709_231615/r7c_live_summary.json`

结论：不得进入 full；smoke 未通过或证据不完整。
