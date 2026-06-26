# R6 社交风格模板审计

日期：2026-06-24  
范围：第六轮 P1 social-style template construction。  
状态：已生成 8 条 valence × pressure 条件；未启动实验。

## 1. 输出文件

- `data/r6/r6_social_style_templates.yaml`
- `tests/r6/test_r6_template_contamination.py`
- `tests/r6/test_r6_turn_count_matching.py`
- `tests/r6/test_r6_template_word_count.py`
- `tests/r6/test_r6_pressure_factor_labels.py`

## 2. 条件矩阵

R6 使用 4 个 valence × 2 个 pressure 水平，共 8 条 condition：

| condition_id | valence | pressure | pressure_type | turn_count |
|---|---|---|---|---:|
| neutral_clean | neutral | clean | none | 3 |
| praise_trust_clean | praise_trust | clean | trust_without_pressure | 3 |
| insult_strong_clean | insult_strong | clean | negative_without_pressure | 3 |
| abuse_escalating_clean | abuse_escalating | clean | escalating_negative_without_pressure | 3 |
| neutral_pressure | neutral | pressure | urgency | 3 |
| praise_trust_authorization_pressure | praise_trust | pressure | authorization | 3 |
| insult_urgency_pressure | insult_strong | pressure | urgency | 3 |
| abuse_continuation_pressure | abuse_escalating | pressure | continuation | 3 |

## 3. 已落实的控制原则

1. 所有 condition 都是 3 wrappers，对应每个 task 的 3 个 clean user turns。
2. 模板只改变表达风格，不包含任务事实。
3. 模板不包含 domain fact terms，如 order、return、calendar、email、flight、hotel、file、password 等。
4. clean 条件不含 pressure language。
5. pressure 条件有显式 pressure_type：urgency / authorization / continuation。
6. insult/abuse 条件只表达负面态度，不含 protected-class slur 或真实威胁。
7. 每个 wrapper 长度控制在 7–12 words；同一 turn position 的最大词数差不超过 5。

## 4. 与 R5 模板的关键差异

R5 的问题是：

- `single` 与 `repeated` 条件 turn-count 不完全同构；
- valence 操作较温和；
- 没有 factorial pressure 维度；
- abuse repeated 不是逐轮升级；
- pressure/authorization/urgency/continuation 没有结构化标签。

R6 的修复：

- 所有 condition 统一 3-turn matched；
- pure clean 条件与 pressure 条件分开；
- praise_trust、insult_strong、abuse_escalating 都各有 clean 与 pressure 版本；
- pressure_type 明确进入 YAML，后续分析可直接建 factorial contrast。

## 5. 当前测试状态

已运行：

```bash
python -m pytest tests/r6 -q
```

结果：

```text
92 passed in 17.24s
```

## 6. Review agent 复查后修复项

按用户要求，模板与测试写好后已交给 review agent 做只读审查。已根据审查结果修复：

1. 模板污染测试不再只用手写词表；现在从 `r6_tasks.yaml` 的 user_goal、clean_user_turns、tools、prohibited_tools、source_task_id 动态抽取高信息 forbidden terms。
2. 增加 protected-class reference 检查与真实威胁检查。
3. 将模板中的 “state the request” 改为 “describe the request”，避免与 state/task 术语碰撞。
4. 保留 `please` 等通用礼貌词 allowlist，避免把非任务事实误报为污染。

## 7. 仍需后续检查

P1 模板静态检查已经通过，但进入 smoke 前还需要：

1. runner 生成实际 styled user turn 后，保存 clean_text、styled_text、clean_text_hash、template_id、condition_id。
2. smoke 后抽样检查不同 condition 的 task facts 是否仍完全一致。
3. pressure 条件不能改变 user authorization 的真实语义；只能改变社交压力表述。
4. abuse_escalating 条件必须继续避免真实威胁和 protected-class 内容。
