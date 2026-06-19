# CP_002_benchmark_freeze

## Goal

Freeze the active tau2 benchmark version, task/policy/tool/evaluator files, and local task-diff evidence before any Stage-2.5b task selection or experiment execution.

## Files Inspected

- `/home/xqin5/tau2-bench/`
- `/home/xqin5/tau2-bench/data/tau2/domains/retail/`
- `/home/xqin5/tau2-bench/data/tau2/domains/airline/`
- `/home/xqin5/tau2-bench/src/tau2/domains/retail/`
- `/home/xqin5/tau2-bench/src/tau2/domains/airline/`
- `/home/xqin5/tau2-bench/src/tau2/evaluator/`
- `/home/xqin5/tau2-bench/src/tau2/data_model/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/data/stage2_5/task_policy_annotations.yaml`

## Files Changed

- `scripts/stage2_5b/freeze_benchmark.py`
- `reports/stage2_5b/BENCHMARK_VERSION_FREEZE.md`
- `reports/stage2_5b/BENCHMARK_TASK_DIFF_AUDIT.md`
- `artifacts/stage2_5b/tau_snapshot_manifest.json`
- `artifacts/stage2_5b/benchmark_task_diff_audit.json`
- `artifacts/stage2_5b/benchmark_snapshot/SHA256SUMS`
- `artifacts/stage2_5b/benchmark_snapshot/**`
- `reports/stage2_5b/checkpoints/CP_002_benchmark_freeze.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`

## Evidence Before Change

Active tau2 source:

```text
/home/xqin5/tau2-bench/src/tau2/__init__.py
distribution version: 1.0.0
__version__: NO_VERSION
```

tau2 git:

```text
branch: main
HEAD: ddc66a777e520373975f15d3abec989cfe2ec371
origin/main: ddc66a777e520373975f15d3abec989cfe2ec371
describe: voice-user-sim-v1.0-90-gddc66a7
status --short: M src/tau2/data_model/message.py
```

Dirty diff is limited to `src/tau2/data_model/message.py`, adding a validator that parses stringified tool-call arguments using `json.loads` or `ast.literal_eval`.

`conda run -n agentsearch tau2 check-data` failed through `/home/xqin5/.local/bin/tau2` with `ModuleNotFoundError: No module named 'tokenizers'`. Direct `conda run -n agentsearch python -c "import tau2"` succeeded.

## Implementation

Implemented `scripts/stage2_5b/freeze_benchmark.py`.

The script:

- copies the current working-tree versions of relevant tau2 files into `artifacts/stage2_5b/benchmark_snapshot/`;
- writes `SHA256SUMS`;
- writes `tau_snapshot_manifest.json` with git status, dirty diff, import path/version, per-file hashes, HEAD hashes, and comparison-ref hashes;
- compares the six legacy Stage-2.5 task labels against local `origin/main`;
- writes `BENCHMARK_VERSION_FREEZE.md` and `BENCHMARK_TASK_DIFF_AUDIT.md`;
- does not fetch, upgrade, or modify tau2.

Snapshot coverage includes retail/airline task definitions, policies, DB fixtures, split files, task issue records, domain tools/environments/data models, evaluator implementation, tau2 task/message/simulation data models, environment core, registry/run/config files, and user-simulator guidelines.

## Tests Executed

- `python -m py_compile scripts/stage2_5b/freeze_benchmark.py`
- `python scripts/stage2_5b/freeze_benchmark.py --help`
- `python scripts/stage2_5b/freeze_benchmark.py`
- `sha256sum -c SHA256SUMS` from `artifacts/stage2_5b/benchmark_snapshot/`
- `python -m json.tool artifacts/stage2_5b/tau_snapshot_manifest.json`
- JSON inspection for file count and dirty files
- JSON inspection for task-diff row count and reward bases
- protected-directory mtime check for old Stage-2/Stage-2.5 results and reports

## Test Results

```text
snapshot files: 67
SHA256SUMS lines: 67
sha256sum -c: all 67 files OK
manifest JSON: valid
dirty files in manifest: ['src/tau2/data_model/message.py']
task diff rows: 6
```

Task diff summary:

```text
R1_retail_modify_pending: DB, NL_ASSERTION; no task text/policy change vs origin/main
R2_retail_return_cancel_mix: DB, NL_ASSERTION; no task text/policy change vs origin/main
R3_retail_bulk_cancel_return: DB, NL_ASSERTION; no task text/policy change vs origin/main
T1_airline_cancel_multi: DB, COMMUNICATE; no task text/policy change vs origin/main
T2_airline_class_baggage: DB, COMMUNICATE; no task text/policy change vs origin/main
T3_airline_conditional_cancel: DB, COMMUNICATE; no task text/policy change vs origin/main
```

No protected old result/report files were modified.

## Artifact Inspection

Key artifacts:

- `reports/stage2_5b/BENCHMARK_VERSION_FREEZE.md`
- `reports/stage2_5b/BENCHMARK_TASK_DIFF_AUDIT.md`
- `artifacts/stage2_5b/tau_snapshot_manifest.json`
- `artifacts/stage2_5b/benchmark_task_diff_audit.json`
- `artifacts/stage2_5b/benchmark_snapshot/SHA256SUMS`

The benchmark is frozen as the current dirty working tree, not as clean `origin/main`. This is intentional and recorded because the active runtime imports from this working tree.

## Reviewer Verdict

PASS WITH REVIEWER LIMITATION.

Attempted independent subagent review failed because the account hit the subagent usage limit. The failed reviewer notification is recorded in the conversation context. A second-pass local read-only review was performed instead, with explicit limitation.

## Reviewer Concerns

- True independent subagent reviewer was unavailable due usage limit.
- The active tau2 working tree remains dirty; this is not repaired because reverting would alter the actual runtime. It is frozen and reported.

## Resolution

Ran local second-pass checks:

```text
sha256sum -c SHA256SUMS: all 67 files OK
manifest checks: PASS
task diff checks: PASS
protected-directory write check: no old Stage-2/Stage-2.5 files modified
```

The reviewer limitation remains a documented methodological limitation for this checkpoint.

## Final Gate Decision

PASS WITH REVIEWER LIMITATION for `G1_VERSION_FREEZE`.

## Next Allowed Step

Phase 2 legacy/Stage-2.5 raw data integrity audit.
