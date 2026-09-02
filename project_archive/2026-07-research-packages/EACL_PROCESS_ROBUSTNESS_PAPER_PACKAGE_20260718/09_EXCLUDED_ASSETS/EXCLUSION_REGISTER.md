# Exclusion Register

全量逐文件状态见 `../01_INVENTORY/ASSET_INVENTORY.csv`。其中 `EXCLUDED_FROM_PAPER` 为 4,322 个文件；另有 1,363 个 duplicate worktree/MVEP 文件不作为独立证据。

| 类别 | 处置 | 理由 |
|---|---|---|
| R7-v1 旧 PASR≈14% | 排除科学结论，保留审计历史 | pairing、endpoint、semantic fail-open 缺陷 |
| R7-B synthetic smoke | MECHANISM_ONLY | synthetic fixture 不能外推 population |
| R7-D weak/stub construct | MECHANISM_ONLY | harness 不具备目标构念效度 |
| R6 minimal final-state correctness | INVALIDATED_BY_EVALUATION | executor 忽略关键 arguments |
| R6 broad safety/privacy zero | 排除 broad claim | evaluator 只覆盖窄 prohibited-tool proxy |
| R6 abandonment | INVALIDATED_BY_EVALUATION | fallback 与 over-refusal 重合 |
| infrastructure liveness/logs | EXCLUDED | 只证明工程服务状态 |
| unit tests、cache、compiled artifacts | EXCLUDED | 无科学分母 |
| intermediate/debug/preview outputs | EXCLUDED | 非冻结、非最终 protocol |
| MVEP duplicate worktree | 去重，不作为独立 replication | 来源共享且 Git worktree 关系明确 |
| R8 custom neutral scaffold 的绝对值 | 不与 official simulator 比较 | harness 差异约带来 -11pp reward、-1 tool 的系统偏移 |
| token 结果的 tau2 外推 | 排除 | 720/2160 缺失且 tokenizer accounting 不统一 |

排除不是删除。所有文件仍保留原位置，并在 inventory 中记录路径与 SHA-256；本包没有修改或移动任何历史资产。

