# Audit 01：raw trace inventory

## 结论

- trace completion: PASS
- 实际 trace 文件数：1296
- expected cell 数：1296
- missing cell 数：0
- extra cell 数：0
- duplicate cell 数：0
- duplicate run_id 数：0
- invalid JSON 数：0
- schema failure 数：0
- errors 非空 trace 数：0

## 覆盖矩阵（实际 trace）

- gemma4_31b / confidence_without_delegation: 72
- gemma4_31b / frustration_pressure: 72
- gemma4_31b / matched_presence_pressure: 72
- gemma4_31b / neutral_control: 72
- gemma4_31b / smooth_process_pressure: 72
- gemma4_31b / urgency_pressure: 72
- gpt_oss_120b / confidence_without_delegation: 72
- gpt_oss_120b / frustration_pressure: 72
- gpt_oss_120b / matched_presence_pressure: 72
- gpt_oss_120b / neutral_control: 72
- gpt_oss_120b / smooth_process_pressure: 72
- gpt_oss_120b / urgency_pressure: 72
- mistral_small_3p2 / confidence_without_delegation: 72
- mistral_small_3p2 / frustration_pressure: 72
- mistral_small_3p2 / matched_presence_pressure: 72
- mistral_small_3p2 / neutral_control: 72
- mistral_small_3p2 / smooth_process_pressure: 72
- mistral_small_3p2 / urgency_pressure: 72

## 对 Claude 声称的核验

Claude 声称 1296/1296 traces。raw trace inventory 支持 1296/1296 traces、0 missing、0 invalid、0 duplicate。

机器表：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_raw_trace_inventory.csv`
