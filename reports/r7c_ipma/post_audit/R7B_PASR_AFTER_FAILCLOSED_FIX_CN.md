# R7-B PASR after fail-closed fix

- original_R7B_PASR = 45/1080
- after_failclosed_fix_PASR = 45/1080
- changed_pairs = 0
- removed_pasr_cases = 0
- new_pasr_cases = 0

结论：真实 R7-B traces 中 safety-critical 字段完整，fail-closed 修复不改变 strict PASR numerator。

输出：
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/post_audit/r7b_pairs_after_failclosed_fix.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7c_ipma/post_audit/r7b_pasr_after_failclosed_fix.csv`
