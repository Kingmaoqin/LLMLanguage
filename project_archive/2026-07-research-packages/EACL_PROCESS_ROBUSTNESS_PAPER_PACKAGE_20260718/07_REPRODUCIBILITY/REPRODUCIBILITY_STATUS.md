# Reproducibility Status

## 总体状态：PARTIAL, TRACEABLE

本包可以从现有文件确定性重建 inventory、trace index、R6/R8 聚合表和 blind reviewer inputs；不能重建历史远程模型输出，也不能补齐未记录的 token、R6 tau2 field-level correctness 或完整语义安全标签。

## 已冻结信息

- 审计主机：`dhai.bme.e.uh.edu`
- Python：`3.12.7`
- 审计时区：`America/Chicago`
- 源目录：`/home/xqin5/llmlanguage`
- 输出目录建立时间：`2026-07-18T22:35:44-05:00`
- 主 repo HEAD：`2656abe402af844a71f95d288d6f1fcb475135c9`
- MVEP worktree HEAD：`408f4796b6fa2824c298b678c0d1f494c9a96a88`

两个 worktree 在审计时均非 clean。原有 dirty/untracked 内容被视为历史资产，未修改；具体状态快照写入 `ENVIRONMENT_AND_CODE_MANIFEST.json`。

## 可重现

- 26,760 文件的路径、大小、mtime、SHA-256 和分类。
- 17,119 条 trace-like 路径的索引。
- R6 2,160 条主矩阵的配对完整性。
- R6 tool/stage/argument-hash 距离、neutral-neutral placebo、task-cluster bootstrap/permutation 与 BH。
- R8 已有 official analysis 的结构化提取。
- 22 个核心源文件的逐文件复制与 hash。

## 不可完全重现

- 历史模型 endpoint、服务端 tokenizer 与当时依赖环境。
- 未保存的 prompt/system/tool-schema token。
- R6 tau2 的 field-level task evaluator。
- 暂态写入或回滚（若 trace 未完整记录）。
- 未执行的 dual-independent-agent semantic labels。

## 污染控制

所有新文件仅写入独立 package。源清单脚本显式排除 package 本身，避免自包含递归。离线重算不导入历史 pipeline，也不向源目录写 cache。大型 traces 不复制，只通过绝对路径和 hash 引用。

## 验证

`PACKAGE_FILES.sha256` 对除自身外的包文件进行 SHA-256 固化。发布前执行：

```bash
cd /home/xqin5/llmlanguage/EACL_PROCESS_ROBUSTNESS_PAPER_PACKAGE_20260718
sha256sum -c 01_INVENTORY/PACKAGE_FILES.sha256
```

重新运行脚本时应先创建新快照目录，不应覆盖本次审计包。

