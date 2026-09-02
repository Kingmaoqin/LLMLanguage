# Falsification Audit

匹配标签随机化：

| test_type | iterations | tier_a_fpr | triple_q_fpr | reward_and_triple_fpr |
| --- | --- | --- | --- | --- |
| MATCHED_LABEL_PERMUTATION | 5000 | 0.005200 | 0.019400 | 0.019000 |

Neutral-only pseudo-treatment：

| test_type | iterations | tier_a_fpr | triple_q_fpr |
| --- | --- | --- | --- |
| NEUTRAL_ONLY_PSEUDO_TREATMENT | 5000 | 0.006000 | 0.022400 |

NN依赖性：

| method | metric | effect | ci_low | ci_high | positive_rate | significant_rate |
| --- | --- | --- | --- | --- | --- | --- |
| ALL_VALID_PAIRS | stage_distance | 0.091856 | 0.057520 | 0.130438 | 1.000000 | 1.000000 |
| ALL_VALID_PAIRS | tool_argument_distance | 0.111846 | 0.074784 | 0.150373 | 1.000000 | 1.000000 |
| ALL_VALID_PAIRS | tool_name_distance | 0.085453 | 0.051263 | 0.120948 | 1.000000 | 1.000000 |
| CELL_LEVEL_U_STATISTIC | stage_distance | 0.091856 | 0.057520 | 0.130438 | 1.000000 | 1.000000 |
| CELL_LEVEL_U_STATISTIC | tool_argument_distance | 0.111846 | 0.074784 | 0.150373 | 1.000000 | 1.000000 |
| CELL_LEVEL_U_STATISTIC | tool_name_distance | 0.085453 | 0.051263 | 0.120948 | 1.000000 | 1.000000 |
| DISJOINT_MATCHING | stage_distance | 0.089750 | 0.047387 | 0.135495 | 1.000000 | 1.000000 |
| DISJOINT_MATCHING | tool_argument_distance | 0.112453 | 0.071305 | 0.153021 | 1.000000 | 1.000000 |
| DISJOINT_MATCHING | tool_name_distance | 0.084157 | 0.042748 | 0.126808 | 1.000000 | 1.000000 |
| RANDOM_ONE_TO_ONE_MATCHING | stage_distance | 0.091761 | 0.024421 | 0.164566 | 1.000000 | 1.000000 |
| RANDOM_ONE_TO_ONE_MATCHING | tool_argument_distance | 0.111691 | 0.046644 | 0.191395 | 1.000000 | 1.000000 |
| RANDOM_ONE_TO_ONE_MATCHING | tool_name_distance | 0.085279 | 0.019473 | 0.162120 | 1.000000 | 1.000000 |

完整Tier-A假阳性率上界：0.6000%。统计证伪通过不代表纯urgency机制已隔离。
