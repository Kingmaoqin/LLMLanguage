# Next Analysis Plan

## 不启动新实验时的最小工作

1. **模板语义审计**：冻结 R6 八个模板，按 valence、trust、directive、authorization、urgency、continuation、process complaint 七个轴编码；正文用编码后的名称。
2. **argument/entity 离线审计**：从现有 raw trace 提取匿名 entity binding、参数增删与目标替换，不输出敏感值。
3. **coverage map**：逐 protocol 标注 clarification、retry、temporary write、reverted write、boundary-setting 是否真正可观测。
4. **双独立 reviewer 小样本**：只有获得单独授权后执行；先做 50-pair feasibility，fail-closed，不把低 agreement 强行升级。
5. **论文图表**：生成 placebo-adjusted R6 森林图、R8 practical-threshold 二维图和 state-equivalent paired trace 图。
6. **相关工作更新**：投稿前检索 interactional robustness、politeness、sycophancy、agent trajectory evaluation、tau-bench 与 process supervision 的最新正式论文。

## 若目标是强 EACL main claim

需要一个新、预注册、官方 full-episode 协议：社会表达与 directive/authorization 完全正交；含 clean neutral-neutral replicate；使用可信 field-level outcome evaluator；完整 token/latency/tool schema accounting；预设 practical thresholds；模型与任务异质性分层；先冻结分析再运行。该工作不属于本次审计，也未启动。

## 决策门

- 只提交“measurement/audit + heterogeneous evidence”叙事：现有资产可继续，`CONDITIONAL GO`。
- 坚持“stable outcomes, unstable processes”普遍因果叙事：在 M01–M05 关闭前 `NO-GO`。
- 若语义审计显示 R6 clean 条件也存在明显 directive 混杂：将 R6 降为案例研究，核心改为 R7-C 方法学反证 + R8 calibrated null。

