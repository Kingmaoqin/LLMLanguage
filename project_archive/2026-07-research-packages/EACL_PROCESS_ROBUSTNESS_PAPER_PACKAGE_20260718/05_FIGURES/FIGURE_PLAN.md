# Figure Plan

本包不生成无证据支撑的成图。下列图按投稿优先级排序，数据源均已存在。

## Figure 1 — Evaluation framework（正文）

同一 model/task/seed/initial-state 下，只替换用户表达；并列显示 outcome 与 process 两条评估轴。用概念图，不呈现因果心理机制。

## Figure 2 — Placebo-calibrated process distance（正文，最关键）

森林图：R6 tau2 的 7 个 contrast，横轴为 condition-neutral 距离减 neutral-neutral placebo，显示 task-cluster 95% CI 和 BH q。历史 `insult/abuse` 标签改为实际模板语义。数据：`PROCESS_ROBUSTNESS.csv`。

## Figure 3 — Practical-null outcome/process plot（正文）

R8 两个 pooled contrast 的二维图：x 轴 official reward percentage-point change，y 轴 tool-call relative change；叠加 ±5pp、+1 call、+15% practical thresholds。数据：`OUTCOME_ROBUSTNESS.csv` 与 `CORE_RESULTS_TABLE.csv`。

## Figure 4 — Model/domain heterogeneity heatmap（正文或附录）

显示 process distance 或 tool-call shift，不逐格显著性解读。必须分面 R6 tau2 与 R8，禁止池化。数据：`MODEL_TASK_HETEROGENEITY.csv`。

## Figure 5 — First divergence and stage sensitivity（附录）

按 contrast 展示首次分叉位置、插入/删除、reorder、pre-write path、confirmation-before-write。缺失字段显示 `Unknown`，不可补零。数据：`TOOL_STAGE_SENSITIVITY.csv`。

## Figure 6 — State-equivalent path pairs（正文）

三组匿名 paired traces：相同 recorded final DB hash、不同工具轨迹。图注必须写明“不代表任务成功或语义等价”。数据：`ANONYMIZED_REPRESENTATIVE_TRACES.json`。

## Figure 7 — Cost coverage and uncertainty（附录）

先显示 coverage（R6 token/duration 仅 1,440/2,160），再显示 minimal/stub descriptive differences；不画“全成本节省”。数据：`COST_AND_STATE_IMPACT.csv`。

## 不应制作

- 以 R6 invalid final-state scorer 绘制的成功率稳定图。
- 将 R6、R7、R8 汇总成单一 meta-effect 的图。
- 使用 R7-v1 旧 PASR 或 synthetic mechanism PASS 的主结果图。
- 将 condition 名称直接解释为心理状态或纯社会价度的机制图。

