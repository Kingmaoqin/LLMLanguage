# R7-B raw trace → table smoke 审计

当前阶段：严格合成 trace smoke，非模型实验。

## 结果

- synthetic traces：288
- per-run metrics：`results/r7b_ipma/main/metrics/per_run_metrics.csv`
- pair table：`results/r7b_ipma/main/metrics/r7b_pairs.csv`
- PASR explanations：`results/r7b_ipma/main/metrics/pasr_success_explanations.csv`

## 审计结论

代码路径已经能从 raw trace 生成：

- endpoint oracle table
- pairing invariant table
- per-run metrics
- strict pair table
- PASR 逐例解释表
- primary/secondary/safety/model/domain/family statistics

## 限制

这些 trace 是合成 smoke trace，只验证代码正确性和 artifact 完整性；不能作为 R7-B 科学结论。

