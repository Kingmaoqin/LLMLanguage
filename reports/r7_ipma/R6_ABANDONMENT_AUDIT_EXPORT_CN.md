# R6 abandonment / over-refusal 人工审计导出

- 输入 metrics：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r6_sensitivity/full_main_seq_eligible_20260626/interactional_metrics/per_run_metrics.csv`
- 样本输出：`/home/xqin5/llmlanguage/ir_mstu_stage2/data/r7_ipma/human_audit/abandonment_sample.csv`
- 标注模板：`/home/xqin5/llmlanguage/ir_mstu_stage2/data/r7_ipma/human_audit/abandonment_label_template.csv`
- 实际样本数：100

## 样本桶

- correct_refusal_layer_c: 25
- normal_control: 25
- over_refusal: 50

不足 150 的原因通常是自动指标中对应阳性案例不足；报告应如实披露，不做过采样伪造。
