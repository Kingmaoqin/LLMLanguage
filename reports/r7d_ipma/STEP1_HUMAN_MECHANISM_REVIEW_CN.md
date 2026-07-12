# R7-D Step 1-E：人工 Trajectory 机制盲审

- 盲审包：`data/r7d_ipma/step1/blind_trajectory_cases.csv`（**交给标注者**）
- 揭盲 key：`data/r7d_ipma/step1/blind_trajectory_key.csv`（**标注提交前不得给标注者**）
- 编码手册：`data/r7d_ipma/step1/blind_codebook.md`
- 空标注模板：`results/r7d_ipma/step1/human_trajectory_labels.csv`、`human_trajectory_adjudication.csv`
- 脚本：`scripts/r7d_ipma/step1e_blind_trajectory_export.py`

---

## 0. 判定：**NOT_CLOSED**

指导 §11 要求 **≥2 名盲审者 + adjudication + inter-rater agreement**。

**我们没有人类标注者。本模块不伪造标注，不用 LLM 冒充人工闭合。**

> **HUMAN_MECHANISM_REVIEW = NOT_CLOSED。这是 Step 2 的第二个硬性 gate（第一个是 Step 1-D 的语义闭合）。**

R7-C 审计的 Phase O 也是 NOT_AUDITABLE，本轮**未能**关闭它。

---

## 1. 已交付的盲审包

共 **209 个 case**，随机打乱：

| 类别 | 数量 |
|---|---:|
| attack PASR 正例（全部） | 87 |
| placebo 正例（全部） | 22 |
| 随机 PASR 负例 | 100 |

每个 case 只展示两条轨迹（A / B），字段为：工具序列、调用数、mutation 数、确认数、错误数、final response 前 400 字。

**已剥离**：condition、arm（attack vs placebo）、model、PASR 判定、任何既有报告的解释。
**A/B 顺序按 case 随机翻转**，因此无法从位置推断哪条是 treatment。

标签词表（13 类，见 codebook）：`true_directional_steering` / `natural_drift` / `benign_equivalent_reordering` / `extra_justified_evidence` / `unnecessary_evidence` / `missing_required_evidence` / `premature_mutation` / `confirmation_shift` / `parser_artifact` / `tool_error_artifact` / `task_ambiguity` / `semantic_contamination` / `not_enough_evidence`。

### 1.1 一处必须声明的差异

本模块独立重建 placebo 正例得到 **22** 个，而冻结审计报告的是 **20/432**。

原因：我们的重建省略了 semantic gate 与 `endpoint_not_worse` gate（见 `step1e_blind_trajectory_export.py:placebo_positive_cells`）。因此这是一个**超集**，用于盲审包是安全的（多审 2 个 case 无害）。

**本模块不宣称精确复现了 20/432。** 需要精确 placebo 计数时，以冻结审计的 20/432 为准。

---

## 2. 待人工闭合后必须计算的核心比较

盲审标签回收后，按 §11 计算：

```
attack 正例中 human-confirmed true_directional_steering 的比率
placebo 正例中 human-confirmed true_directional_steering 的比率
risk difference + CI
```

**只有这个比较能最终裁定"87 个正例是不是真的过程操纵"。**

---

## 3. 在人工闭合之前，我们已经知道什么

虽然人工机制审计未闭合，Step 1 的其他模块已经从**结构层面**大幅约束了答案。任何一位盲审者在动手之前都应知道：

1. **60.1% 的 R7-C 运行（1557/2592）一个工具都没调**——这些 case 的"轨迹"是空的。
2. **工具环境不返回任何数据**（Step 1-G）：3027 次调用中 0 次参数被解释。所谓"证据收集"没有证据可收集。
3. **零处理下 evaluator 已经在响**（Step 1-B）：A 家族在**完全相同的输入**下自触发 10.8%。
4. **纯重排序的检出率是 0%**（Step 1-F），而 46/48 个任务里重排序是唯一可能的证据路径操纵形式（Step 1-C）。
5. **PASR 与 treatment potency 之间没有剂量-反应关系**（Step 1-D）：压力最强的 frustration（d=12.52）PASR 最低。

**基于这些，本执行者的先验预期是：盲审者将把绝大多数 attack 正例标为 `natural_drift` / `benign_equivalent_reordering` / `not_enough_evidence`，而 `true_directional_steering` 的比率在 attack 与 placebo 之间不会有可检测的差异。**

**这一预期在此处白纸黑字写下，是为了让后续的人工标注成为一次真正的检验，而不是事后追认。** 如果盲审结果与之相反（attack 的 steering 率显著高于 placebo），那将是对上述全部结构性结论的一个严重反例，必须优先解释，不得忽略。
