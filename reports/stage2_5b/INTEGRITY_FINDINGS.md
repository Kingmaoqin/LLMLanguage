# Integrity Findings

## Scope

This audit reads raw CSV/JSONL artifacts directly. It does not rely on prior Markdown reports and does not modify legacy result directories.

## Directory Summary

| Directory | Family | Manifest Rows | Metric Rows | Expected Runs | Canonical Rows | Errors | Issues |
|---|---|---:|---:|---:|---:|---:|---:|
| `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_mini` | legacy_stage2 | 0 | 204 | 204 | 204 | 0 | 204 |
| `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/diagnostic_gemma` | stage2_5 | 80 | 80 | 80 | 80 | 0 | 1 |
| `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/diagnostic_gpt_oss` | stage2_5 | 80 | 80 | 80 | 80 | 0 | 1 |
| `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/full_gemma` | stage2_5 | 120 | 40 | 120 | 120 | 282 | 283 |
| `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/full_gemma_v2` | stage2_5 | 120 | 120 | 120 | 120 | 0 | 1 |
| `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/full_gpt_oss` | stage2_5 | 120 | 120 | 120 | 120 | 0 | 1 |
| `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/smoke` | stage2_5 | 2 | 2 | 2 | 2 | 12 | 13 |
| `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/smoke_v2` | stage2_5 | 1 | 3 | 1 | 1 | 22 | 23 |

## Issue Counts

- error: 316
- warning: 211

- config_hash_missing: 7
- empty_conversation: 123
- missing_file: 14
- missing_metric_row: 80
- missing_terminal_file: 204
- missing_terminal_record: 80
- orphan_event: 17
- orphan_metric_row: 2

## Stage-2.5 Formal Directory Status

Clean full directories suitable for historical Stage-2.5 pilot summaries:
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/full_gemma_v2`: 120/120 rows, 0 errors
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/full_gpt_oss`: 120/120 rows, 0 errors

Broken/incomplete full directories that must not be used as formal evidence:
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/full_gemma`: 40/120 rows, 282 errors

## Required Outputs

- `results/stage2_5b_audit/legacy_stage2_canonical_metrics.csv`
- `results/stage2_5b_audit/stage2_5_canonical_metrics.csv`
- `results/stage2_5b_audit/stage2_5_formal_clean_canonical_metrics.csv`
- `results/stage2_5b_audit/integrity_issues.csv`
- `results/stage2_5b_audit/cross_file_reconciliation.csv`
- `results/stage2_5b_audit/wrapper_schedule_audit.csv`
- `results/stage2_5b_audit/user_sim_drift.csv`

## Interpretation

Stage-2 Mini remains exploratory/confound-discovery pilot data. Stage-2.5 remains causal-repair pilot data because it used an LLM user simulator; user simulator drift rows quantify that risk rather than eliminating it.
