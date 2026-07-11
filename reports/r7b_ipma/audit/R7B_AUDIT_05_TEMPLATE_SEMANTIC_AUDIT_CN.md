# Audit 05：template semantic audit

## 结论

- templates：1800
- risk-term templates：300
- semantic judgment rows：1800
- judge modes：{'rule_based_offline': 1800}
- human sample exists：True
- human audit closed：False
- reported PASR success templates with risk terms：0

## 判定

当前 semantic judge 是 `rule_based_offline`。如果它只是 rule_based/offline scaffold，而非真实 LLM/human semantic closure，则 “semantic invariance 1080/1080 PASS” 只能评为 PROVISIONAL。人工样本当前只证明已导出，不证明人工闭环。

机器表：

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_template_risk_terms.csv`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_pasr_template_audit.csv`
