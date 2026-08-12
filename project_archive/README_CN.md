# LLMLanguage 项目公开归档说明

本目录汇总 `/home/xqin5/llmlanguage` 父项目中未直接属于主 Git 工作树、但对研究复现和历史追溯有价值的材料。归档快照制作于 2026-08-11。

## 仓库与历史

- 主仓库：`Kingmaoqin/LLMLanguage`
- 当前最新研发线：`r9-mechanism-aligned-process-attack`
- MVEP 完整历史：`r7d-mvep-remediation-v1`
- R7-D 构念与因果重建历史：`r7d-construct-causal-rebuild` 及 `r7d-step*` 标签
- MISROUTE 基准拥有独立仓库和发布标签：`Kingmaoqin/misroute`

本次发布会同步本地主仓库的全部研究分支和标签，因此历史版本通过 Git 提交和标签保存，不再重复复制整个工作树。

## 归档内容

`2026-07-research-packages/` 包含论文证据包、早期交互鲁棒性试验、R8-C2 证据卷宗、Tier-A 强化分析和研究 wiki。`project-notes/` 包含父目录中的轮次总结、试验意见、提示词和 PDF 方案。

## 结果与日志策略

- 可复现的代码、冻结配置、指标表、分析 JSON、评审结果、报告和图表直接提交。
- 原始逐步轨迹和模型原始输出约 5.7 GB，继续遵循项目原有 `.gitignore` 规则留在本地，避免让公开仓库无法正常克隆。
- `manifests/LOCAL_RESULTS_INVENTORY.csv` 记录本地结果文件的路径、字节数和 SHA-256，可用于完整性核对。
- `logs_archive/` 保存所有 `.log` 文件的确定性 gzip 无损副本；`MANIFEST.csv` 同时记录原始文件和压缩文件的大小与 SHA-256。

重新生成清单和日志归档：

```bash
bash scripts/repository_archive/build_local_results_inventory.sh
bash scripts/repository_archive/build_public_log_archive.sh
```
