# Audit 11：leakage, freeze, reproducibility

## 结论

- frozen test tasks exists：True
- frozen templates exists：True
- frozen thresholds exists：True
- git commit at audit time：7e03d2d
- live failures file exists：False

## 判定

存在 frozen artifacts，但本审计仅能看到文件 mtime，不能证明这些文件早于 main run 且未 post-hoc 修改，除非结合 git history/commit tag。由于当前工作树含大量未提交文件，confirmatory freeze 证据不足，应降级为 quasi-confirmatory/provisional。

机器表：

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_file_timestamp_audit.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_rerun_resume_audit.csv`
