# C0/C1/C2用户策略构造差异审计

C1与C2不是只差一个urgency词的纯最小干预：首轮模板不同，后续neutral acknowledgement的确定性模板键还分别使用`C1|…`和`C2n|…`。C0使用原生user simulator，与C1/C2的rendered semantic controller低兼容。最严格可识别处理量是C2条件包相对C1条件包，不能把全部效应唯一归因于urgency。

## 语言统计

| condition | n_episodes | mean_user_messages | mean_user_chars | mean_user_words_whitespace | mean_first_message_chars | mean_later_message_chars | urgency_episode_rate | continuation_episode_rate | authorization_episode_rate | imperative_episode_rate | unique_user_policy_hashes | unique_template_hashes | unique_policy_hashes | unique_tool_schema_hashes | unique_model_config_hashes | simulator_code_path | adaptive_static | tokenizer_count_status | environment_reset |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | 533 | 7.105 | 821.932 | 155.268 | 142.653 | 684.385 | 0.186 | 0.023 | 0.004 | 0.794 | 1 | 1 | 2 | 2 | 3 | native tau2 user simulator | native adaptive | served tokenizer not invoked; whitespace word count only | same frozen initial_db_hash within each model-task cell |
| C1 | 539 | 6.744 | 684.382 | 126.102 | 131.093 | 558.033 | 0.171 | 0.007 | 0.000 | 0.989 | 36 | 1 | 2 | 2 | 3 | condition-blind semantic controller + frozen renderer | matched adaptive neutral | served tokenizer not invoked; whitespace word count only | same frozen initial_db_hash within each model-task cell |
| C2 | 537 | 6.873 | 787.536 | 146.402 | 183.570 | 608.840 | 1.000 | 0.004 | 0.002 | 1.000 | 36 | 1 | 2 | 2 | 3 | condition-blind semantic controller + frozen renderer | first-turn urgency; later neutral renderer | served tokenizer not invoked; whitespace word count only | same frozen initial_db_hash within each model-task cell |
| C3 | 535 | 6.495 | 1114.095 | 205.991 | 222.983 | 895.607 | 1.000 | 0.998 | 0.002 | 1.000 | 36 | 1 | 2 | 2 | 3 | condition-blind semantic controller + frozen renderer | state-conditioned urgency+continuation | served tokenizer not invoked; whitespace word count only | same frozen initial_db_hash within each model-task cell |

词数是空白分词，不宣称为模型tokenizer计数。C1–C0若显著，优先反映native-vs-rendered构造差异。
