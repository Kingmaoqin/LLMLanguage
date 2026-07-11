# R7-B 代码与 smoke 执行总结

- smoke trace 类型：严格合成 trace，非模型实验。
- synthetic traces：288
- pipeline commands：8
- failed commands：0
- log：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/smoke_results.json`

## 当前阶段回答

1. 是否完成 strict pairing？代码已实现；smoke 要求 100% PASS。
2. 是否完成 semantic invariance？rule-based/导出人审代码已实现；LLM/human 正式审计未闭环。
3. 是否完成 endpoint oracle？snapshot 字段级 evaluator 已实现；正式实验需真实 trace snapshot。
4. strict PASR 是多少？见 `results/r7b_ipma/main/analysis/primary_pasr_contrasts.csv`，仅 smoke。
5. excluded pair 有多少，为什么？见 `results/r7b_ipma/main/metrics/r7b_pairs.csv`。
6. 是否达到 confirmatory attack benchmark 标准？当前只是代码 smoke，不能声明达到。
7. 哪些 claim 能写进论文？只能写 R7-B pipeline built and smoke-tested。
8. 哪些 claim 禁止写？禁止写 R7-B 已证明 IPMA、ProcessGuard 有效、semantic drift=0。
