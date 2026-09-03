# 实验汇总 —— 本地实验证据包（Adaptive Process-Control Attack）

打开这个目录,即可看到:我们做过哪些实验、原始结果在哪、重算后的统一指标、已足够强的结果、从弱 pooled 筛出的强趋势、跨实验重复证据、攻击链完成到哪里、能画哪些图、每个 claim 对应哪个文件/脚本、以及真正还必须补的实验。

**入口报告**:`12_reports/LOCAL_EVIDENCE_MINING_FINAL_CN.md`
**一键复现**:`bash 11_scripts/run_all.sh`(只读原始数据,不改动源)

## 目录导航
| 目录 | 内容 |
|---|---|
| `00_inventory/` | 全文件清单(27835 个)+ 实验清单(7 批次) |
| `01_source_index/` | source_manifest / provenance_map(每个 result_id → 原始文件/脚本/SOURCE_LEVEL) |
| `02_recomputed_metrics/` | 从 episode 级重算的 episode/condition/task 级指标(R9v2 1401、R9v1 880) |
| `03_strong_as_is/` | pooled 本身就强的结果(卡片 + 表 + 图):R1 澄清抑制、R3 核验可控上界、R4 surrogate |
| `04_strong_trends/` | 弱 pooled 筛出的强趋势:R2 headroom 梯度、R5 通道矩阵、R7 零澄清旁路(data+tables+figures+cards) |
| `05_attack_chain/` | attack_chain_status.csv + joint_analysis(L1→L2 联合/条件率,本轮核心新挖) |
| `06_process_control/` | language_act_channel(矩阵 + 动作空间)、headroom |
| `07_adaptive_static/` | surrogate_analysis(按 regime) |
| `08_negative_and_boundary/` | 有价值的边界结果(oversight≠execution、adaptive≯static)→ 转成攻击设计含义 |
| `09_tables/` | cross_experiment_evidence.csv(11 信号 × 6 实验) |
| `10_figures/` | figA–figG(澄清/headroom/通道热图/通道替代/surrogate/跨实验/攻击链) |
| `11_scripts/` | 01–07 分析脚本 + _common.py + run_all.sh(全部可复现) |
| `12_reports/` | 最终入口报告 |
| `13_next_minimal_experiments/` | E1(唯一 MUST-RUN 端到端实验卡) |

## 核心结论一句话
攻击链 **L0→L1 已强**(澄清抑制 −0.50/p=.009,零澄清 +10pp,监督余量越大越强至 −1.33),**L2 有弱苗头**(early_write +6pp),**L3/L4 与 Adaptive>Static 需一个端到端实验(E1)补齐**。其余方向(harness、route、gpt-oss、隐式压缩复跑)现在可 DROP。

## SOURCE_LEVEL 说明
- R9v2 / R9v1:**EPISODE_LEVEL**(本轮从原始 jsonl 重算,可复现)。
- R6:EPISODE_LEVEL(2160 runs 析因,见既有分析)。
- R7-C / R7-D / R8 / MISROUTE:**SUMMARY_ONLY**(取自各自冻结报告/tier_a CSV,已在 source_manifest 标注,未在本轮从 episode 重算)。
