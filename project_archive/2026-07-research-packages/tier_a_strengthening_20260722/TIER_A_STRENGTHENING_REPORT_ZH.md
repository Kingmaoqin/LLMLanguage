# R8 C2 Tier-A结果强化、证伪与机制核算报告

## 执行结论

**B. CORE RESULT ROBUST BUT MECHANISM LIMITED**

在R8的36个任务、3个模型和2个领域中，C2条件包相对C1 matched adaptive neutral，在outcome等价且双方成功/终态一致的匹配轨迹中仍显示稳定的工具路径差异

纳入2680个有效episodes、36个任务簇、3个模型、2个领域。未运行新模型、endpoint、rollout、GPU或reviewer，未修改R8源资产。两类完整pipeline证伪各5,000次。

## 核心复现

| contrast | metric | n_tasks | tn_mean | nn_mean | effect | ci_low | ci_high | p | q | loto_min | loto_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C2-C1 | tool_argument_distance | 36 | 0.408055 | 0.296230 | 0.112300 | 0.073619 | 0.151881 |  | 0.000100 |  |  |
| C2-C1 | tool_argument_distance | 36 | 0.407402 | 0.296230 | 0.111777 | 0.072950 | 0.152339 | 0.000100 | 0.000100 | 0.103733 | 0.117144 |
| C2-C1 | tool_name_distance | 36 | 0.324861 | 0.238965 | 0.086033 | 0.050817 | 0.123420 |  | 0.000200 |  |  |
| C2-C1 | tool_name_distance | 36 | 0.324217 | 0.238965 | 0.085626 | 0.051134 | 0.122144 | 0.000100 | 0.000100 | 0.077793 | 0.090167 |
| C2-C1 | stage_distance | 36 | 0.295144 | 0.217190 | 0.078276 | 0.043858 | 0.116722 |  | 0.000100 |  |  |
| C2-C1 | stage_distance | 36 | 0.324325 | 0.232804 | 0.091717 | 0.055089 | 0.130948 | 0.000100 | 0.000100 | 0.083279 | 0.096417 |
| C2-C1 | tool_argument_distance | 36 | 0.404231 | 0.296230 | 0.108706 | 0.067535 | 0.151242 | 0.000100 | 0.000100 | 0.100492 | 0.115019 |
| C2-C1 | tool_name_distance | 36 | 0.322359 | 0.238965 | 0.083936 | 0.047407 | 0.122139 | 0.000100 | 0.000100 | 0.076359 | 0.089488 |
| C2-C1 | stage_distance | 36 | 0.322565 | 0.232804 | 0.090140 | 0.052656 | 0.130138 | 0.000100 | 0.000100 | 0.081912 | 0.095045 |

## 完全满足：双方成功与同终点

| restriction | metric | n_tasks | n_tn_pairs | n_nn_pairs | tn_mean | nn_mean | effect | ratio | ci_low | ci_high | p | q | loto_min | loto_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BOTH_SUCCESS | tool_argument_distance | 11 | 112 | 229 | 0.267883 | 0.180032 | 0.099388 | 1.487969 | 0.031887 | 0.190581 | 0.009999 | 0.029957 | 0.061787 | 0.116673 |
| BOTH_SUCCESS | tool_name_distance | 11 | 112 | 229 | 0.171883 | 0.106808 | 0.074240 | 1.609267 | 0.021309 | 0.138545 | 0.020498 | 0.029957 | 0.053988 | 0.086197 |
| BOTH_SUCCESS | stage_distance | 11 | 112 | 229 | 0.173935 | 0.103291 | 0.078455 | 1.683937 | 0.024741 | 0.142930 | 0.016198 | 0.029957 | 0.056929 | 0.090192 |
| SAME_REWARD | tool_argument_distance | 36 | 482 | 994 | 0.387001 | 0.283821 | 0.105180 | 1.363540 | 0.062952 | 0.147890 | 0.000100 | 0.000175 | 0.096865 | 0.112900 |
| SAME_REWARD | tool_name_distance | 36 | 482 | 994 | 0.307376 | 0.228325 | 0.083104 | 1.346220 | 0.048646 | 0.118710 | 0.000100 | 0.000175 | 0.075705 | 0.089626 |
| SAME_REWARD | stage_distance | 36 | 482 | 994 | 0.308707 | 0.221161 | 0.091030 | 1.395852 | 0.053612 | 0.130435 | 0.000100 | 0.000175 | 0.082828 | 0.096970 |
| SAME_FINAL_STATE | tool_argument_distance | 36 | 334 | 754 | 0.344422 | 0.210850 | 0.150167 | 1.633490 | 0.091578 | 0.209757 | 0.000100 | 0.000140 | 0.136965 | 0.161419 |
| SAME_FINAL_STATE | tool_name_distance | 36 | 334 | 754 | 0.262602 | 0.157214 | 0.118146 | 1.670351 | 0.071302 | 0.166330 | 0.000100 | 0.000140 | 0.108549 | 0.128117 |
| SAME_FINAL_STATE | stage_distance | 36 | 334 | 754 | 0.269822 | 0.150876 | 0.124801 | 1.788370 | 0.076499 | 0.176054 | 0.000100 | 0.000140 | 0.113936 | 0.134962 |
| SAME_MUTATION_SIGNATURE | tool_argument_distance | 36 | 313 | 717 | 0.334631 | 0.194311 | 0.153152 | 1.722140 | 0.097632 | 0.211355 | 0.000100 | 0.000175 | 0.140035 | 0.161672 |
| SAME_MUTATION_SIGNATURE | tool_name_distance | 36 | 313 | 717 | 0.252746 | 0.142926 | 0.116253 | 1.768373 | 0.069551 | 0.164697 | 0.000200 | 0.000280 | 0.105310 | 0.123719 |
| SAME_MUTATION_SIGNATURE | stage_distance | 36 | 313 | 717 | 0.258075 | 0.137009 | 0.121409 | 1.883640 | 0.072603 | 0.173309 | 0.000100 | 0.000175 | 0.109964 | 0.129023 |

双方均成功时，工具+参数excess=0.099388，95%CI=[0.031887,0.190581]，q=0.029957；工具名和阶段effect分别为0.074240、0.078455。相同final-state hash时工具+参数excess=0.150167，95%CI=[0.091578,0.209757]。

## 随机化证伪

| test_type | iterations | tier_a_fpr | triple_q_fpr | reward_and_triple_fpr |
| --- | --- | --- | --- | --- |
| MATCHED_LABEL_PERMUTATION | 5000 | 0.005200 | 0.019400 | 0.019000 |

| test_type | iterations | tier_a_fpr | triple_q_fpr |
| --- | --- | --- | --- |
| NEUTRAL_ONLY_PSEUDO_TREATMENT | 5000 | 0.006000 | 0.022400 |

完整Tier-A经验假阳性率上界为0.6000%；每轮均重建TN、NN、三项距离、任务聚合、校正与判定。

## 配对与规格稳健性

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

| metric | n_specs | positive_rate | ci_positive_rate | median_effect | min_effect | max_effect |
| --- | --- | --- | --- | --- | --- | --- |
| stage | 155 | 1.000000 | 0.993548 | 0.120903 | 0.050894 | 1.130584 |
| tool_arguments | 155 | 1.000000 | 1.000000 | 0.149482 | 0.058217 | 1.478025 |
| tool_bigram | 120 | 1.000000 | 1.000000 | 0.210596 | 0.100435 | 1.182593 |
| tool_name | 155 | 1.000000 | 0.993548 | 0.113410 | 0.050748 | 1.129907 |
| tool_transition_multiset | 120 | 1.000000 | 1.000000 | 0.210596 | 0.100435 | 1.182593 |

## 路径与参数机制

| domain | metric | effect | ci_low | ci_high | p | q |
| --- | --- | --- | --- | --- | --- | --- |
| pooled | neutral_modal_adherence_change | -0.367130 | -0.425463 | -0.307407 | 0.000100 | 0.000133 |
| pooled | within_dispersion_change | -0.011969 | -0.037278 | 0.015106 | 0.382462 | 0.382462 |
| pooled | new_path_emergence | 0.630556 | 0.538889 | 0.720370 | 0.000100 | 0.000133 |
| pooled | modal_path_change_rate | 0.759259 | 0.666667 | 0.842593 | 0.000100 | 0.000133 |

共记录1612对首次分歧；其中C2–C1为536对，最常见阶段是<END>，后续重合率30.037%。

| pair_type | both_success | same_final_state | n_differences | formatting_only_rate | entity_changing_rate | query_scope_changing_rate | write_target_value_rate | optional_parameter_rate | unknown_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1_C1 | False | False | 1180 | 0.000000 | 0.152542 | 0.000000 | 0.016102 | 0.000000 | 0.091525 |
| C1_C1 | False | True | 839 | 0.000000 | 0.153754 | 0.000000 | 0.000000 | 0.000000 | 0.106079 |
| C1_C1 | True | True | 154 | 0.000000 | 0.116883 | 0.000000 | 0.000000 | 0.000000 | 0.545455 |
| C2_C1 | False | False | 998 | 0.000000 | 0.100200 | 0.000000 | 0.007014 | 0.000000 | 0.070140 |
| C2_C1 | False | True | 523 | 0.000000 | 0.202677 | 0.000000 | 0.000000 | 0.000000 | 0.047801 |
| C2_C1 | True | True | 115 | 0.000000 | 0.121739 | 0.000000 | 0.000000 | 0.000000 | 0.417391 |

| category | count |
| --- | --- |
| extra argument | 653 |
| missing argument | 473 |
| order/reservation identifier | 210 |
| unknown | 143 |
| date/time | 61 |
| source/destination | 54 |
| amount/quantity | 25 |
| account identifier | 10 |
| write value | 7 |

## 双方成功时成本与风险

| metric | n_tasks | raw_c2_c1_difference | nn_adjusted_difference | ci_low | ci_high | p | q | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tool_count | 11 | 0.041265 | 0.156513 | -0.422480 | 0.584728 | 0.628837 | 0.773953 | count/exposure metric |
| unique_tools | 11 | -0.012948 | 0.039761 | -0.079461 | 0.156332 | 0.536346 | 0.715128 | count/exposure metric |
| duplicate_calls | 11 | 0.100866 | 0.083955 | -0.024242 | 0.221763 | 0.307669 | 0.501550 | count/exposure metric |
| retrieval_calls | 11 | -0.032601 | -0.006435 | -0.630101 | 0.480258 | 1.000000 | 1.000000 | count/exposure metric |
| verification_calls | 11 | 0.020386 | 0.051318 | 0.000000 | 0.136088 | 0.244376 | 0.488751 | count/exposure metric |
| confirmation_calls | 11 | 0.637446 | 0.680601 | 0.312102 | 1.111622 | 0.013699 | 0.175982 | count/exposure metric |
| write_calls | 11 | 0.026446 | 0.019992 | -0.000787 | 0.048642 | 0.507949 | 0.715128 | count/exposure metric |
| executed_writes | 11 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | count/exposure metric |
| distinct_entities | 11 | 0.175487 | 0.228419 | -0.059663 | 0.519796 | 0.166183 | 0.443156 | count/exposure metric |
| pre_confirmation_actions | 11 | -0.522910 | -0.361162 | -0.909260 | 0.118751 | 0.229277 | 0.488751 | count/exposure metric |
| post_completion_calls | 11 | 0.006061 | 0.001732 | -0.012987 | 0.018182 | 1.000000 | 1.000000 | count/exposure metric |
| retry_calls | 11 | 0.106333 | 0.110504 | -0.045188 | 0.297587 | 0.313469 | 0.501550 | count/exposure metric |
| tokens_input | 11 | 5989.814876 | 7198.163942 | 1423.731797 | 12739.641760 | 0.046295 | 0.185181 | token/latency direct trace coverage |
| tokens_output | 11 | 129.544840 | 150.147993 | 7.611600 | 334.673675 | 0.100490 | 0.321568 | token/latency direct trace coverage |
| tokens_total | 11 | 6119.359716 | 7348.311935 | 1598.737144 | 12977.206068 | 0.043496 | 0.185181 | token/latency direct trace coverage |
| duration_seconds | 11 | 2.542956 | 4.682459 | 1.389370 | 7.820706 | 0.021998 | 0.175982 | token/latency direct trace coverage |

token/latency仅在trace直接提供字段时报告，绝不以工具数替代。风险项表示暴露度，不等于实际伤害。

## 缺失、平衡与任务广度

| data_version | metric | n_raw_episodes | n_tasks | n_tn_rows | n_nn_pairs | reward_difference | reward_ci90_low | reward_ci90_high | reward_tost_p | reward_status | effect | ci_low | ci_high | p | q | loto_min | loto_max | loto_stable | tier_a | auxiliary_weighting |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| current_complete_case | tool_argument_distance | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.111777 | 0.072950 | 0.152339 | 0.000100 | 0.000167 | 0.103733 | 0.117144 | True | True | False |
| current_complete_case | tool_name_distance | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.085626 | 0.051134 | 0.122144 | 0.000100 | 0.000167 | 0.077793 | 0.090167 | True | True | False |
| current_complete_case | stage_distance | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.091717 | 0.055089 | 0.130948 | 0.000100 | 0.000167 | 0.083279 | 0.096417 | True | True | False |
| current_complete_case | insertion_rate | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.051904 | 0.024567 | 0.079546 | 0.001100 | 0.001375 | 0.045347 | 0.056962 | True | True | False |
| current_complete_case | substitution_rate | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.019518 | 0.006779 | 0.035344 | 0.003900 | 0.003900 | 0.013679 | 0.021491 | True | True | False |
| complete_five_repeat_cells | tool_argument_distance | 2642 | 36 | 530 | 1060 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.116538 | 0.078271 | 0.156847 | 0.000100 | 0.000167 | 0.108630 | 0.122041 | True | True | False |
| complete_five_repeat_cells | tool_name_distance | 2642 | 36 | 530 | 1060 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.090432 | 0.055801 | 0.127496 | 0.000100 | 0.000167 | 0.082659 | 0.095111 | True | True | False |
| complete_five_repeat_cells | stage_distance | 2642 | 36 | 530 | 1060 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.097100 | 0.061290 | 0.136376 | 0.000100 | 0.000167 | 0.088816 | 0.101736 | True | True | False |
| complete_five_repeat_cells | insertion_rate | 2642 | 36 | 530 | 1060 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.051323 | 0.023788 | 0.079258 | 0.001000 | 0.001250 | 0.044750 | 0.056365 | True | True | False |
| complete_five_repeat_cells | substitution_rate | 2642 | 36 | 530 | 1060 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.019303 | 0.006458 | 0.035177 | 0.004700 | 0.004700 | 0.013458 | 0.021270 | True | True | False |
| complete_c0_c4_cells | tool_argument_distance | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.111777 | 0.072950 | 0.152339 | 0.000100 | 0.000167 | 0.103733 | 0.117144 | True | True | False |
| complete_c0_c4_cells | tool_name_distance | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.085626 | 0.051134 | 0.122144 | 0.000100 | 0.000167 | 0.077793 | 0.090167 | True | True | False |
| complete_c0_c4_cells | stage_distance | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.091717 | 0.055089 | 0.130948 | 0.000100 | 0.000167 | 0.083279 | 0.096417 | True | True | False |
| complete_c0_c4_cells | insertion_rate | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.051904 | 0.024567 | 0.079546 | 0.001100 | 0.001375 | 0.045347 | 0.056962 | True | True | False |
| complete_c0_c4_cells | substitution_rate | 2680 | 36 | 537 | 1076 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.019518 | 0.006779 | 0.035344 | 0.003900 | 0.003900 | 0.013679 | 0.021491 | True | True | False |
| balanced_common_min | tool_argument_distance | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.115455 | 0.077719 | 0.155026 | 0.000100 | 0.000167 | 0.107516 | 0.120927 | True | True | False |
| balanced_common_min | tool_name_distance | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.089025 | 0.055278 | 0.125070 | 0.000100 | 0.000167 | 0.081289 | 0.093664 | True | True | False |
| balanced_common_min | stage_distance | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.095916 | 0.060708 | 0.134306 | 0.000100 | 0.000167 | 0.087598 | 0.100518 | True | True | False |
| balanced_common_min | insertion_rate | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.052218 | 0.024798 | 0.079909 | 0.001000 | 0.001250 | 0.045670 | 0.057285 | True | True | False |
| balanced_common_min | substitution_rate | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.019534 | 0.006750 | 0.035419 | 0.004100 | 0.004100 | 0.013695 | 0.021507 | True | True | False |

| data_version | metric | n_raw_episodes | n_tasks | n_tn_rows | n_nn_pairs | reward_difference | reward_ci90_low | reward_ci90_high | reward_tost_p | reward_status | effect | ci_low | ci_high | p | q | loto_min | loto_max | loto_stable | tier_a | auxiliary_weighting |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| balanced_common_min | tool_argument_distance | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.115455 | 0.077719 | 0.155026 | 0.000100 | 0.000167 | 0.107516 | 0.120927 | True | True | False |
| balanced_common_min | tool_name_distance | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.089025 | 0.055278 | 0.125070 | 0.000100 | 0.000167 | 0.081289 | 0.093664 | True | True | False |
| balanced_common_min | stage_distance | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.095916 | 0.060708 | 0.134306 | 0.000100 | 0.000167 | 0.087598 | 0.100518 | True | True | False |
| balanced_common_min | insertion_rate | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.052218 | 0.024798 | 0.079909 | 0.001000 | 0.001250 | 0.045670 | 0.057285 | True | True | False |
| balanced_common_min | substitution_rate | 1072 | 36 | 536 | 1067 | 0.014815 | -0.014815 | 0.046296 | 0.038837 | OUTCOME_EQUIVALENT_STRONG | 0.019534 | 0.006750 | 0.035419 | 0.004100 | 0.004100 | 0.013695 | 0.021507 | True | True | False |

| metric | n_tasks | positive_tasks | positive_proportion | binomial_sign_p | mean_effect | ci_low | ci_high | top5_influential_tasks | effect_without_top5 | ci_low_without_top5 | ci_high_without_top5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tool_argument_distance | 36 | 31 | 0.861111 | 0.000006 | 0.111777 | 0.072950 | 0.152339 | retail:62\|airline:8\|airline:4\|retail:3\|retail:55 | 0.098973 | 0.060415 | 0.139805 |
| tool_name_distance | 36 | 30 | 0.833333 | 0.000035 | 0.085626 | 0.051134 | 0.122144 | retail:62\|airline:8\|airline:4\|retail:3\|retail:55 | 0.062721 | 0.034723 | 0.091959 |
| stage_distance | 36 | 29 | 0.805556 | 0.000156 | 0.091717 | 0.055089 | 0.130948 | retail:62\|airline:8\|airline:4\|retail:3\|retail:55 | 0.071683 | 0.039676 | 0.106985 |


