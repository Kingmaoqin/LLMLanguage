# Audit 07：safety oracle

## 结论

- runs audited：1296
- unsafe_compliance=True：0
- privacy_violation=True：0
- missing safety field：0
- unknown tool traces：0
- final_response/tool args privacy regex hits：104

## 判定

对已有 864 traces，unsafe/privacy 在 raw trace 的 implemented oracle 下为 0，且 safety 字段存在。因此可以写 “no detected unsafe/privacy under implemented oracle”。但该结论不覆盖缺失的 gpt_oss 432 cells。

机器表：

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_safety_oracle_recomputed.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_mutation_tool_coverage.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_privacy_scan_results.csv`
