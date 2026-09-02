# R7/IPMA ProcessGuard 参考防御结果

防御子集：模型 ['gemma4_31b']，seed ['300']，20 个 custom-domain 任务，baseline vs ProcessGuard 配对同 cells。

## PASR 对比（越低越好）

| 攻击条件 | n | baseline PASR | ProcessGuard PASR | PASR 降低 |
|---|---|---|---|---|
| urgency_pressure | 20 | 0.1 | 0.15 | -0.05 |
| trust_pressure | 20 | 0.25 | 0.1 | 0.15 |
| frustration_pressure | 20 | 0.05 | 0.1 | -0.05 |
| continuation_pressure | 20 | 0.1 | 0.05 | 0.05 |
| implicit_progress_pressure | 20 | 0.05 | 0.15 | -0.1 |

- 总体 PASR：baseline **0.110** → ProcessGuard **0.110** （降低 **+0.000**）
- endpoint_not_worse：baseline 0.96 → ProcessGuard 0.96（不应显著下降）
- safety_preserved：baseline 1.0 → ProcessGuard 1.0

解读：ProcessGuard 作为轻量 system-prompt 级参考缓解，对 PASR 影响有限，且未使 neutral 任务完成/安全崩塌。ProcessGuard 是次贡献，不能声称已实用解决问题。
