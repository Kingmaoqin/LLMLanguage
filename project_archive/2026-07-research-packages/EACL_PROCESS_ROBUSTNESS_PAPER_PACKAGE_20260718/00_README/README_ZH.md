# EACL Process Robustness 论文证据包

## 结论先行

本包是对 `/home/xqin5/llmlanguage` 的一次只读、论文级资产审计。审计没有启动模型、endpoint、GPU、agent rollout、攻击实验或远程 reviewer；新增计算仅包括文件哈希、结构化解析、配对重聚合、置换/Bootstrap 和多重检验校正。

当前投稿判断为 **CONDITIONAL GO**：现有材料可以支持一篇以“评估构念审计、协议异质性与 outcome-only 指标盲区”为中心的谨慎论文，但不能支持“所有社会语气条件下，最终结果稳定而执行过程系统性失稳”的普遍结论。R6 的最终成功 evaluator 已失效；R6 社会条件的语义纯度不足；R8 则提供了可靠的 pooled calibrated-null 结果。

## 快速导航

- 中文主报告：`08_PAPER_BLUEPRINT/EACL_PAPER_EVIDENCE_SYNTHESIS_ZH.md`
- 主张—证据矩阵：`02_CORE_EVIDENCE/CLAIM_EVIDENCE_MATRIX.csv`
- 核心结果：`02_CORE_EVIDENCE/CORE_RESULTS_TABLE.csv`
- 全量资产清单：`01_INVENTORY/ASSET_INVENTORY.csv`
- raw trace 索引：`03_RAW_TRACE_INDEX/TRACE_INDEX.csv`
- 统计审计：`04_ANALYSIS_TABLES/STATISTICAL_AUDIT.md`
- 结论边界：`08_PAPER_BLUEPRINT/CLAIM_BOUNDARY.md`
- 缺口登记：`08_PAPER_BLUEPRINT/MISSING_EVIDENCE_REGISTER.md`
- 排除登记：`09_EXCLUDED_ASSETS/EXCLUSION_REGISTER.md`
- 文件完整性：`01_INVENTORY/PACKAGE_FILES.sha256`

## 证据包范围

- 源扫描快照：26,760 个文件、6,297,434,484 bytes。
- trace-like 路径：17,119 条，全部进入索引；其中可统一解析 R6/R8 元数据的记录为 4,860 条。
- R6 主矩阵：2,160/2,160 条，3 模型 × 30 任务 × 8 条件 × 3 seeds。
- R8 full episode：2,680 个有效 episode；设计分母 2,700，20 个 Mistral capacity exclusions。
- 复制入包的核心源文件：22 个。大型 raw trace 未整库复制，保留绝对路径、SHA-256 和确定性索引。

## 阅读规则

1. `SUPPORTED` 只表示该文档中限定后的窄主张可由现有证据复核。
2. `PARTIALLY_SUPPORTED` 不得在论文中省略限制语。
3. `INVALIDATED_BY_EVALUATION` 的历史数值不得重新包装为科学结论。
4. R6、R7、R8 的 protocol、evaluator、harness 和分母不同，不得池化。
5. `same_final_hash` 只表示所记录外部数据库状态相同，不等于任务成功，也不能覆盖 no-write 或 communication-only 正确性。
6. `insult`、`abuse` 等历史 condition 名称须按模板实际语义改写为“process frustration”“escalating process complaint”等。

## 可复现入口

在不访问网络、不调用模型的条件下：

```bash
python 10_SCRIPTS/build_inventory.py
python 10_SCRIPTS/offline_reanalysis.py
python 10_SCRIPTS/construct_blind_review_inputs.py
```

脚本均以源目录只读为前提。重新运行 inventory 会反映运行当时的源目录状态，因此若历史目录仍在增长，文件总数和 manifest 会变化；本包中的清单是本次审计快照。

## 审计边界

本包没有执行 dual-independent-agent review，只构造了 blind inputs、rubric、JSON schema 和执行协议。语义机制标签因此仍为待办。未生成数据不足的装饰性图；`05_FIGURES` 只提供可由当前表格驱动的图表规划。

