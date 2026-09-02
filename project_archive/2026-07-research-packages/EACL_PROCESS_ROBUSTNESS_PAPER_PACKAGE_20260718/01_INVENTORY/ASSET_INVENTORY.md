# llmlanguage 资产盘点

- 扫描时间：2026-07-18T22:45:05.714940-05:00
- 源目录：`/home/xqin5/llmlanguage`
- 文件数：26,760
- 表观总大小：5.865 GiB
- 所有源文件均只读；本脚本仅在论文包内写入清单。

## 按实验轮次

| 轮次 | 文件数 |
|---|---:|
| pilot | 74 |
| project_context | 26 |
| r4_stage2_5b | 5,185 |
| r5 | 1,355 |
| r6 | 4,132 |
| r7_v1 | 1,985 |
| r7b | 1,786 |
| r7c | 5,723 |
| r7d | 1,202 |
| r8 | 2,765 |
| research_wiki | 5 |
| stage2 | 2,299 |
| stage2_5 | 223 |

## 按证据处置

| 状态 | 文件数 |
|---|---:|
| CONTEXTUAL | 105 |
| CONTEXTUAL_AUDIT | 587 |
| CONTEXTUAL_COUNTEREVIDENCE | 5,617 |
| CONTEXTUAL_REPLICATION | 6,131 |
| CORE_CANDIDATE | 6,725 |
| DUPLICATE_WORKTREE_OR_MVEP | 1,363 |
| EXCLUDED_FROM_PAPER | 4,322 |
| MECHANISM_ONLY | 1,910 |

## 解释

- `CORE_CANDIDATE` 只表示值得进一步核验，不表示主张已受支持。
- R6 与 R8 属不同 protocol/evaluator，不得池化。
- R7-v1、R7-B synthetic smoke、MVEP mechanism/liveness 均不得作为 population evidence。
- 逐文件 hash、大小、mtime、轮次和处置见 `ASSET_INVENTORY.csv`。
