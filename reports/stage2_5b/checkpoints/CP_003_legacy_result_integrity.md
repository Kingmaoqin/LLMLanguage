# CP_003_legacy_result_integrity

## Goal

Audit legacy Stage-2 and Stage-2.5 raw results directly from CSV/JSONL logs, rebuild canonical metrics, identify invalid historical directories, audit wrapper schedules, and quantify LLM user-simulator drift.

## Files Inspected

- `results/stage2_mini/`
- `results/stage2_5_repair/*/`
- `scripts/run_stage2_5_experiment.py`
- `scripts/audit_stage2_integrity.py`
- `reports/stage2_5b/BENCHMARK_VERSION_FREEZE.md`

## Files Changed

- `scripts/stage2_5b/audit_all_results.py`
- `results/stage2_5b_audit/legacy_stage2_canonical_metrics.csv`
- `results/stage2_5b_audit/stage2_5_canonical_metrics.csv`
- `results/stage2_5b_audit/stage2_5_formal_clean_canonical_metrics.csv`
- `results/stage2_5b_audit/integrity_issues.csv`
- `results/stage2_5b_audit/cross_file_reconciliation.csv`
- `results/stage2_5b_audit/wrapper_schedule_audit.csv`
- `results/stage2_5b_audit/user_sim_drift.csv`
- `results/stage2_5b_audit/directory_summary.csv`
- `results/stage2_5b_audit/random_10_run_raw_reconciliation.csv`
- `reports/stage2_5b/INTEGRITY_FINDINGS.md`
- `reports/stage2_5b/LEGACY_USER_SIM_DRIFT_AUDIT.md`
- `reports/stage2_5b/checkpoints/CP_003_legacy_result_integrity.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`

## Evidence Before Change

Stage-2.5 result directories included multiple historical directories:

```text
diagnostic_gemma
diagnostic_gpt_oss
full_gemma
full_gemma_v2
full_gpt_oss
smoke
smoke_v2
```

Prior reports said the usable full data were `full_gemma_v2` and `full_gpt_oss`, but Phase 2 required direct raw-log audit rather than trusting Markdown reports.

## Implementation

Implemented `scripts/stage2_5b/audit_all_results.py`.

The script directly reads:

- `run_metrics.csv`
- `run_manifest.csv`
- `conversation_logs.jsonl`
- `normalized_tool_events.jsonl`
- `user_simulator_events.jsonl`
- `style_wrapper_events.jsonl`
- `state_deltas.jsonl`
- `final_environment_states.jsonl`
- `evidence_events.jsonl`
- `branch_decisions.jsonl`
- `policy_failures.jsonl`
- `termination_reasons.jsonl`
- `parser_health.jsonl`

It audits unique/duplicate/missing run IDs, orphan events, duplicate JSONL lines, cross-file row consistency, model/task/condition/seed/template mismatch, initial-state mismatch, config-hash presence, missing terminal records, empty conversations, and silent failed runs.

It also rebuilds canonical metrics from raw events and generates wrapper schedule and user-simulator drift audits.

## Tests Executed

- `python -m py_compile scripts/stage2_5b/audit_all_results.py`
- `python scripts/stage2_5b/audit_all_results.py --help`
- `python scripts/stage2_5b/audit_all_results.py`
- issue distribution inspection from `integrity_issues.csv`
- directory summary inspection from `directory_summary.csv`
- wrapper schedule audit inspection from `wrapper_schedule_audit.csv`
- user-sim drift inspection from `user_sim_drift.csv`
- deterministic 10-run raw reconciliation sample from `stage2_5_formal_clean_canonical_metrics.csv`

## Test Results

Audit run:

```text
legacy canonical rows: 204
stage2.5 canonical rows: 523
issues: 527
reconciliation rows: 0
```

Directory-level findings:

```text
stage2_mini: 204/204 canonical rows, 0 errors, 204 warnings for missing terminal file in legacy schema
diagnostic_gemma: 80/80, 0 errors
diagnostic_gpt_oss: 80/80, 0 errors
full_gemma: 40/120 metric rows, 282 errors
full_gemma_v2: 120/120, 0 errors
full_gpt_oss: 120/120, 0 errors
smoke: 2/2, 12 errors
smoke_v2: 1 expected / 3 metric rows, 22 errors
```

Formal clean Stage-2.5 pilot evidence is restricted to:

```text
results/stage2_5_repair/full_gemma_v2
results/stage2_5_repair/full_gpt_oss
```

Broken/incomplete directory:

```text
results/stage2_5_repair/full_gemma
```

Wrapper schedule audit:

```text
727/727 rows schedule_ok=True
```

LLM user-sim drift:

```text
groups audited: 101
clean signature drift: 93
extracted object-id drift: 24
```

10-run raw reconciliation sample:

```text
10/10 sample_check_pass=True
```

## Artifact Inspection

Generated outputs:

- `reports/stage2_5b/INTEGRITY_FINDINGS.md`
- `reports/stage2_5b/LEGACY_USER_SIM_DRIFT_AUDIT.md`
- `results/stage2_5b_audit/*.csv`

`cross_file_reconciliation.csv` contains only a header row, meaning no manifest-vs-event metadata mismatch was found for fields present in both sources.

## Reviewer Verdict

PASS WITH REVIEWER LIMITATION.

Independent subagent review remains unavailable due usage limit. A local second-pass audit was performed by deterministic 10-run raw reconciliation and CSV/report inspection.

## Reviewer Concerns

- No independent subagent reviewer could randomly inspect traces.
- Stage-2.5 directories do not contain config/template/benchmark hash fields, so resume/mixture safety cannot be proven from old manifests. This is recorded as `config_hash_missing` warnings and must be fixed in Stage-2.5b outputs.
- Stage-2 and Stage-2.5 data remain legacy/pilot evidence only.

## Resolution

The audit distinguishes clean historical pilot directories from broken historical directories and writes canonical metrics plus explicit warnings. Stage-2.5b will not reuse these result directories for confirmatory evidence.

## Final Gate Decision

`G2_INTEGRITY_PASS`: PASS WITH LIMITATIONS.

The gate is sufficient to continue because:

- new and old result directories were not mixed;
- formal Stage-2.5 clean pilot directories reconcile one-to-one;
- legacy risks are explicitly marked;
- canonical metrics are rebuilt by a single command;
- old Stage-2 is permanently marked exploratory/confound-discovery pilot.

## Next Allowed Step

Phase 3: audit and implement deterministic controlled user before any new calibration or confirmatory treatment run.
