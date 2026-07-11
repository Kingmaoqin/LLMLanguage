# R7 retry / failure bias 审计

## 结论评级

PROVISIONAL。450 个瞬时失败均可对应最终 trace，但缺少逐次 retry 时间戳/重试策略表，不能完全排除 completed-only 或选择性重跑偏差。

## 结果

- live_failures.jsonl 行数：450
- unique failed run_id：450
- failed run_id 中有最终 trace：450
- 明细：`results/r7_ipma/audit/retry_failure_trace_coverage.csv`

## 建议

论文应报告 transient failure/retry 机制，并说明所有失败 run 是否保留在最终 denominator。不要只写 integrity PASS。
