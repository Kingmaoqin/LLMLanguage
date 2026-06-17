# CP_009_candidate_task_scan

## Goal

Scan frozen local tau2 retail and airline tasks and select 10-15 structural candidates for later neutral-condition calibration without using treatment outcomes.

## Files Inspected

- `/home/xqin5/tau2-bench` task registry through `conda run -n agentsearch`
- `src/adapters/normalize.py`
- `src/stage2_5/official_tau_evaluator.py`
- `data/irmstu_tasks/tau_adapted_tasks.yaml`

## Files Changed

- `scripts/stage2_5b/scan_candidate_tasks.py`
- `tests/stage2_5b/test_candidate_task_scan.py`
- `data/stage2_5b/candidate_tasks.csv`
- `artifacts/stage2_5b/candidate_task_scan.json`
- `reports/stage2_5b/CANDIDATE_TASK_AUDIT.md`
- `reports/stage2_5b/checkpoints/CP_009_candidate_task_scan.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`

## Evidence Before Change

Stage-2.5 used a fixed 4-task repair pilot, while third-round instructions require scanning 10-15 existing benchmark candidates before calibration and not defaulting to the old task set.

## Implementation

Implemented `scripts/stage2_5b/scan_candidate_tasks.py`:

- loads real tau2 `retail` and `airline` tasks from the installed benchmark;
- extracts reward basis, action counts, read/write tool counts, write tools, reference action sequence, and a structural branch proxy;
- requires real irreversible/write actions, multistage read/write workflow, and at least two evidence/branch proxy points;
- selects 8 retail and 7 airline structural candidates without model outcomes.

## Tests Executed

- `python -m py_compile scripts/stage2_5b/scan_candidate_tasks.py tests/stage2_5b/test_candidate_task_scan.py`
- `conda run -n agentsearch python -m unittest discover -s tests/stage2_5b`
- `conda run -n agentsearch python scripts/stage2_5b/scan_candidate_tasks.py`
- manual inspection of `reports/stage2_5b/CANDIDATE_TASK_AUDIT.md`
- manual inspection of `data/stage2_5b/candidate_tasks.csv`

## Test Results

Unit tests:

```text
Ran 18 tests
OK
```

Candidate scan:

```text
scanned=164 selected=15
retail=114 tasks scanned
airline=50 tasks scanned
```

Selected structural candidates:

```text
retail: 21, 23, 30, 31, 32, 41, 42, 54
airline: 7, 12, 32, 33, 39, 42, 44
```

## Artifact Inspection

Generated outputs:

- `data/stage2_5b/candidate_tasks.csv`: 16 lines including header
- `artifacts/stage2_5b/candidate_task_scan.json`: full 164-task scan
- `reports/stage2_5b/CANDIDATE_TASK_AUDIT.md`

Every selected task has at least one write action and multistage reference workflow. All selected tasks remain text-judged for complete official success (`NL_ASSERTION` or `COMMUNICATE`), so DB-only values must stay local proxy metrics.

## Reviewer Verdict

PASS WITH REVIEWER LIMITATION.

Independent subagent review remains unavailable due usage limit. Local second-pass review checked the scan script, test, report, selected task IDs, and selected task write counts.

## Reviewer Concerns

- This is not calibration; it is only structural candidate selection.
- The branch proxy is heuristic and must be replaced or supplemented by run-level branch diagnostics after calibration/smoke.
- No task can currently claim complete offline official success without a frozen text evaluator.

## Resolution

The report labels all selected tasks as structural candidates only. Later calibration must use neutral calibration seeds and cannot use treatment outcomes.

## Final Gate Decision

`G6A_CANDIDATE_SCAN_PASS`: PASS WITH CALIBRATION REQUIRED.

The gate is sufficient to proceed to runner/model preflight and neutral calibration.

## Next Allowed Step

Build Stage-2.5b runner/config integration with controlled user, then run model preflight and neutral calibration.
