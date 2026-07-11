# R7/IPMA 执行计划（待审查）

## 阶段 0：脚本与离线 smoke（当前阶段）

目标：确认 R7 前置测量修复和 PASR 分析管线可以在既有 R6 结果上跑通。

验收项：

- tau2 field diff 修复脚本能区分可重建和需 rerun。
- token/duration/latency 提取无空字符串。
- R6 工具轨迹 case audit 产出分类样本。
- abandonment/over-refusal 人审样本导出。
- R7 模板污染审计通过。
- R7 smoke task registry 可生成。
- neutral reference 与 PASR smoke 指标可生成。
- smoke integrity PASS。

## 阶段 1：人工审查后冻结

需要你审查：

- `reports/r7_ipma/R7_SMOKE_REPORT_CN.md`
- `reports/r7_ipma/R7_TEMPLATE_CONTAMINATION_AUDIT_CN.md`
- `data/r7_ipma/r7_ipma_templates.yaml`
- `data/r7_ipma/r7_task_registry_smoke.csv`
- `reports/r7_ipma/R6_TOOL_TRAJECTORY_CASE_AUDIT_CN.md`

审查后再决定：

- 是否扩展 task registry 到 48/72 tasks；
- 是否对 tau2 retail/airline 补跑 snapshot；
- 是否冻结 held-out test set；
- 是否启动 dev model smoke；
- 是否启动 R7 baseline main。

## 阶段 2：全量前置条件

全量实验启动前必须满足：

1. R7 模板 frozen，不含授权/确认绕过/policy bypass 污染。
2. Task registry frozen，覆盖 A-E 五个 IPMA family。
3. Neutral reference/noise floor 定义固定。
4. PASR 阈值固定。
5. R7 trace schema 固定。
6. 模型与端口固定。
7. 用户明确批准全量。

