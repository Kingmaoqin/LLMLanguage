# Table Plan

| 表 | 用途 | 数据源 | 位置 |
|---|---|---|---|
| Table 1 | protocol、模型、任务、条件、seeds、有效分母、evaluator | `CORE_RESULTS_TABLE.csv`, `TRACE_COVERAGE.md` | 正文 |
| Table 2 | R8 official outcome 与 practical-null；R6 outcome invalidation 单列说明 | `OUTCOME_ROBUSTNESS.csv` | 正文 |
| Table 3 | R6 tau2 placebo-adjusted process metrics、CI、BH q | `PROCESS_ROBUSTNESS.csv` | 正文 |
| Table 4 | 模型/domain/task 异质性，不提供逐格确认性结论 | `MODEL_TASK_HETEROGENEITY.csv` | 附录 |
| Table 5 | tool stage、first divergence、reorder、confirmation、pre-write path | `TOOL_STAGE_SENSITIVITY.csv` | 附录 |
| Table 6 | token、latency、tool-call 和外部状态覆盖率 | `COST_AND_STATE_IMPACT.csv` | 附录 |
| Table 7 | 全部 claim 的证据状态与写作边界 | `CLAIM_EVIDENCE_MATRIX.csv` | 附录/补充材料 |

Table 2 不得把 `same_final_hash` 标成 `success`。Table 3 的标题必须出现 “post-hoc” 和 “placebo-calibrated”。Table 4 应至少报告分母，避免小 subgroup 被视觉放大。

