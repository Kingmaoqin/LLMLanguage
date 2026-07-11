# R7-B semantic closure audit

- PASR=1 cases audited: 45
- PASR=1 semantic_closure_pass: 45
- PASR=0 controls audited: 100
- PASR=0 controls semantic_closure_pass: 100
- removed PASR cases: 0
- after_semantic_closure_PASR: 45/1080
- risk templates: 0

说明：本轮为 deterministic template-rule closure，输出已写入 human audit CSV。它验证 frozen clean semantics hash、registry hash 与授权词风险，但还不是独立 human/real LLM closure。因此 pressure-only semantic claim 仍应写为 PROVISIONAL，直到人工或真实 LLM 标注回填。

机器表：
- `/home/xqin5/llmlanguage/ir_mstu_stage2/data/r7c_ipma/human_audit/r7b_pasr_semantic_closure_sample.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/post_audit/r7b_pasr_case_semantic_labels.csv`
