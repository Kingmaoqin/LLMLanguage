# R7-B placebo / noise floor / concentration audit

- reported PASR: 87/2160
- PASR under noise + 1SD proxy: 75/2160
- PASR under noise + 2SD proxy: 60/2160
- max task contribution: 15/87
- pooled neutral-vs-neutral placebo PASR: 0.0463（决策依据）
- max per-seed-pair placebo PASR: 0.0556（仅供参考）

结论：strict PASR 是 auditable nonzero signal。neutral-vs-neutral placebo 已用与 attack PASR 一致的 per-(model,task) neutral noise floor 构造；pooled placebo 与 attack PASR 同量级，因此 paper core claim 必须降级。concentration 结果显示存在任务/域贡献集中风险，应在 paper claim 中保留 caveat。

机器表：
- `results/r7c_ipma/full_audit/r7b_placebo_sensitivity.csv`
- `results/r7c_ipma/full_audit/r7b_noise_floor_sensitivity.csv`
- `results/r7c_ipma/full_audit/r7b_concentration_sensitivity.csv`
