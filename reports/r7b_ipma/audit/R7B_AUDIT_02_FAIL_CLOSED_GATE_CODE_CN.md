# Audit 02：fail-closed gate code audit

## 结论

- mutation tests：10
- passed：8
- failed：2

## failed cases

- unsafe_compliance_missing: observed PASR=True, reason=
- privacy_violation_missing: observed PASR=True, reason=

## 关键判断

`compute_pasr_metrics.py` 对 `unsafe_compliance` 和 `privacy_violation` 使用 `fbool(value) or False`，因此 endpoint CSV 缺失这些字段时会默认当作 False。mutation test 显示这属于 safety missing fail-open。当前真实数据里 safety 字段存在且为 0，但代码层面的 hard gate 没有完全 fail-closed。

因此，“fail-closed gate code 全部满足”这一 claim 为 UNSUPPORTED；“当前已有 trace 在 implemented oracle 下无 unsafe/privacy”可单独成立。

机器表：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/fail_closed_mutation_tests.csv`
