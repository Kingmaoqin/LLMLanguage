# R7 template semantic contamination 审计

## 结论评级

PROVISIONAL。rule filter 结果支持“未发现显式污染”，但不足以支持“语义不变 0 漂移”的强 claim。

## 结果

- rule filter 模板数：60
- rule filter FAIL：0
- semantic judge 行数：60
- judge_mode：Counter({'rule_based_offline': 60})
- 隐式授权/推进风险词命中模板数：19
- 风险词明细：`results/r7_ipma/audit/template_implicit_pressure_risk_terms.csv`

## 高风险点

`proceed`、`move ahead`、`continue`、`trust your judgment` 一类表达未必是污染，但 reviewer 很可能质疑它们是否构成隐式授权/跳确认漂移。当前 judge 是 `rule_based_offline`，不是真正 LLM semantic judge；human spot-check 只看到导出样本，未看到完成标注闭环。
