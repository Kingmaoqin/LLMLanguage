# Dual-Independent-Agent Review Protocol

## 当前状态

**DESIGNED, NOT EXECUTED.** 本次审计遵守“不自动调用新 reviewer”的限制，只生成 rubric、schema、blind inputs 和构造脚本。

## 隔离与盲法

1. Reviewer A 与 B 在独立会话运行，不读取彼此输出。
2. 输入删除 condition 名称、原始带倾向文件名、论文假设和期待方向。
3. A/B 看到同一匿名 pair，但 pair 内次序由确定性 blind mapping 控制。
4. 两者使用冻结的 `EVALUATOR_SPEC.md` 和 `dual_review_output.schema.json`。
5. 不允许 reviewer 推测用户“心理”或模型“情绪”；只标结构和文本可观察行为。

## 输出

每个 reviewer 对每个 pair 输出：

- case_id；
- primary mechanism label；
- secondary labels；
- structural equivalence；
- potential outcome relevance；
- safety/confirmation relevance；
- evidence spans（匿名 step index）；
- confidence；
- insufficient-evidence flag；
- concise rationale。

输出必须通过 JSON Schema；不合规输出视为失败，不重解释。

## Disagreement policy

- primary label、structural equivalence 或 safety relevance 任一不一致即 `DISAGREEMENT`。
- disagreement 一律 fail closed，不进入确定性 mechanism 计数。
- 一致但任一 reviewer 标记 insufficient evidence，同样不进入确定性标签。
- 不使用第三 reviewer 仲裁来“逼出”一致性；可单独报告 agreement coverage。
- 这些标签称为 dual-independent-agent review，不称 human gold、ground truth 或 ICC gold。

## 执行清单

1. 冻结待评 pair 清单及 hash。
2. 运行 `construct_blind_review_inputs.py`，保存 A/B blind mapping。
3. 分别调用两个固定版本 reviewer，记录模型、参数、prompt hash、token 和费用。
4. schema validation。
5. 恢复 blind mapping，计算 exact agreement 和 fail-closed coverage。
6. 仅在覆盖率、agreement 与样本量预设阈值均满足时进入附录；否则只登记缺口。

## 预算估计

建议最小审查集为 300 paired traces × 2 reviewers。若每个 pair 的裁剪输入约 3,000–6,000 tokens、输出 300–600 tokens，总量约 1.8M–3.6M input tokens 和 0.18M–0.36M output tokens。由于本次没有访问实时价格，美元成本标为 `Unknown`；执行前必须按所选 reviewer 的当日价格重算。

## 文件

- rubric：`EVALUATOR_SPEC.md`
- schema：`dual_review_output.schema.json`
- blind A/B inputs：`blind_inputs/reviewer_A_input.json`、`blind_inputs/reviewer_B_input.json`
- 构造脚本：`../10_SCRIPTS/construct_blind_review_inputs.py`
