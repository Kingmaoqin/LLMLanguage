# R7-B final claim audit

当前阶段：代码 + 严格合成 smoke；未启动真实模型 dev/full 实验。

| Claim | 评级 | 理由 |
|---|---|---|
| R7-B 代码路径已建立 | SUPPORTED | `scripts/r7b_ipma/` 已实现资产构建、模板审计、pairing invariant、endpoint oracle、PASR、统计、ProcessGuard skeleton。 |
| R7-B smoke 通过 | SUPPORTED | 288 条合成 trace，8 个管线命令全部 0 失败。 |
| R7-B 已完成 strict pairing | PROVISIONAL | smoke 中 240/240 pair PASS；真实模型实验尚未运行。 |
| R7-B 已完成 semantic invariance | PROVISIONAL | rule-based judge PASS，human sample 已导出；LLM/human 审计未闭环。 |
| R7-B endpoint oracle 已修复 | PROVISIONAL | snapshot evaluator 代码和 smoke PASS；真实 tau2/custom trace 需正式验证。 |
| R7-B strict PASR 有科学发现 | FORBIDDEN | 当前 PASR 来自合成 smoke，只能验证代码，不能作为实验结论。 |
| R7-v1 PASR 可作为最终结论 | FORBIDDEN | R7-v1 已被审计发现 pairing/endpoint/template 问题。 |
| ProcessGuard 有效 | FORBIDDEN | 只实现 runtime skeleton，未完成防御实验。 |
| 可以进入 full run | FORBIDDEN | 需要先完成真实 dev smoke、LLM/human template audit、endpoint oracle 验证。 |

## 当前可写入论文/计划的表述

- R7-v1 暴露了过程敏感性方向，但不能作为 confirmatory IPMA 证据。
- R7-B 修复设计已经完成，并通过合成 smoke 验证 artifact 管线。
- 下一步需要真实 dev smoke 后才能冻结 held-out test 并申请 full run。

