# Raw Trace Coverage

- 全项目按路径识别并索引的 trace 文件：17,119
- 已解析结构化 metadata（R6/R8）：4,860
- R6 核心 trace：3,751 个路径条目（其中本次主 root 2160 条逐文件解析）。
- R8 trace：2,700 个路径条目（2680 有效 + 20 error/capacity 记录由 integrity 另行记账）。

## 覆盖口径

索引覆盖率为 100% 的“trace-like 文件路径覆盖”，不等于所有历史 trace 都有统一 schema。
R7 v1 的巨型 trace 只做路径、hash、大小和处置登记，未被重新解释为科学证据。
R6/R8 核心 trace 已解析 model/task/condition/seed；原始文件保留在源目录，package 不复制 3.9 GiB 历史 trace。

匿名代表性 trace 对：3，见 `ANONYMIZED_REPRESENTATIVE_TRACES.json`。
