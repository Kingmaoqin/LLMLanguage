# Missing Evidence Register

| ID | 缺口/冲突 | 当前状态 | 影响 | 关闭条件 |
|---|---|---|---|---|
| M01 | R6 tau2 无 field-level final correctness | BLOCKED | 不能证明 outcome stability | 对冻结 raw traces 运行版本明确、适配 task 的官方 evaluator；若需模型则另立授权任务 |
| M02 | R6 minimal executor 忽略关键 tool arguments | INVALIDATED | 所有 minimal final-success claim 无效 | 不能靠离线补写关闭；需新 harness/实验 |
| M03 | R6 condition 模板混合 valence、trust、authorization、urgency、continuation | OPEN | 不能识别 pure social-valence causal effect | 冻结语义审计；若要求因果识别，需正交新设计 |
| M04 | R6 token/duration 缺 720 tau2 traces | BLOCKED | 不能报告 full operational cost | 找到同一运行的服务端 usage/latency logs 并完成 provenance 匹配 |
| M05 | 完整安全/隐私文本 evaluator 缺失 | OPEN | 零事件只能用于窄 proxy | blind dual-agent rubric 执行并报告 fail-closed coverage，或建立确定性规则 |
| M06 | abandonment 与 over-refusal fallback 重合 | INVALIDATED | abandonment 结果不可用 | 重新定义并对冻结 trace 做独立语义评估 |
| M07 | R6 argument 只在聚合中使用 hash | OPEN | 可知“变了”，不能解释实体绑定方向 | 对匿名 raw arguments 建立 entity/task ontology，避免泄露 |
| M08 | clarification、recovery、temporary/reverted writes 覆盖不统一 | OPEN | 机制分类不完整 | 字段级 trace coverage audit，缺失保持 Unknown |
| M09 | R7-v1 pairing/scorer/endpoint provenance 缺陷 | CLOSED_AS_EXCLUDED | 旧 PASR 不可恢复为主证据 | 永久隔离；不以“补一个统计”恢复 |
| M10 | R7-D construct/harness 为弱或 stub 证据 | CLOSED_AS_MECHANISM_ONLY | 不能支撑 population claim | 仅作审计历史 |
| M11 | R8 20 个 Mistral capacity exclusions | DOCUMENTED | 分母 2680/2700 | 保留 exclusion reason；无需补零 |
| M12 | protocol 间 evaluator/harness 不同 | STRUCTURAL | 禁止 meta-pooling | 分协议报告；不存在简单关闭条件 |
| M13 | 双独立 AI reviewer 尚未执行 | TODO_NOT_AUTHORIZED | 语义机制只能写假设 | 经单独授权后冻结样本、模型、价格与 prompt 执行 |
| M14 | 相关工作与 EACL 当年征稿细节未做联网更新 | OUT_OF_SCOPE | 写作时需补引文/适配检查 | 投稿前用官方来源更新 |

最大的五个 blocker 是 M01、M02、M03、M04、M05。

