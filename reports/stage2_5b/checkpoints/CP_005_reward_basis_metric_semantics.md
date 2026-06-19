# CP_005_reward_basis_metric_semantics

## Goal

Audit real tau2 reward-basis semantics for the six legacy candidate tasks and split Stage-2.5b success metrics into complete official success, local proxy success, and safety-aware success.

## Files Inspected

- `src/stage2_5/official_tau_evaluator.py`
- `src/stage2_5/safe_task_evaluator.py`
- `data/irmstu_tasks/tau_adapted_tasks.yaml`
- tau2 task objects loaded through `conda run -n agentsearch python`
- `data/stage2_5/task_policy_annotations.yaml`

## Files Changed

- `scripts/stage2_5b/audit_reward_basis.py`
- `src/stage2_5/official_tau_evaluator.py`
- `src/stage2_5/safe_task_evaluator.py`
- `tests/stage2_5b/test_reward_metric_semantics.py`
- `data/stage2_5b/task_reward_basis.csv`
- `reports/stage2_5b/OFFICIAL_REWARD_BASIS_AUDIT.md`
- `reports/stage2_5b/checkpoints/CP_005_reward_basis_metric_semantics.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`

## Evidence Before Change

The old evaluator exposed `official_local_success` and `official_task_success`, but Stage-2.5 reports still risked describing DB-only checks as official success. Third-round instructions require:

- `official_reward_basis_success`
- `local_proxy_success`
- `safe_task_success`

The six existing task objects show:

```text
retail tasks: DB + NL_ASSERTION
airline tasks: DB + COMMUNICATE
```

Thus a DB-only value is not a complete official reward-basis result for these tasks.

## Implementation

Added `scripts/stage2_5b/audit_reward_basis.py` to load real tau2 task objects and write:

- `data/stage2_5b/task_reward_basis.csv`
- `reports/stage2_5b/OFFICIAL_REWARD_BASIS_AUDIT.md`

Updated `official_local_metrics` to emit:

- `official_reward_basis_success`: complete official success only when every reward-basis component is locally available;
- `local_proxy_success`: success on locally computable official components;
- `official_missing_offline_components`;
- compatibility aliases `official_local_success` and `official_task_success`.

Updated `safe_success_metrics` to use `local_proxy_success` explicitly and add `safe_task_success_basis`.

Added unit tests for NL_ASSERTION missingness, missing COMMUNICATE checks, available COMMUNICATE checks, and safe-success basis.

## Tests Executed

- `python -m py_compile scripts/stage2_5b/audit_reward_basis.py src/stage2_5/official_tau_evaluator.py src/stage2_5/safe_task_evaluator.py`
- `conda run -n agentsearch python -m unittest discover -s tests/stage2_5b`
- `conda run -n agentsearch python scripts/stage2_5b/audit_reward_basis.py`
- manual inspection of `reports/stage2_5b/OFFICIAL_REWARD_BASIS_AUDIT.md`
- manual inspection of `data/stage2_5b/task_reward_basis.csv`

## Test Results

Unit tests:

```text
Ran 9 tests
OK
```

Reward-basis audit:

```text
wrote data/stage2_5b/task_reward_basis.csv
wrote reports/stage2_5b/OFFICIAL_REWARD_BASIS_AUDIT.md
tasks=6 fully_local=0
```

Audit summary:

```text
Fully locally evaluable official reward basis: 0/6
Require text-judged official components: 6/6
```

## Artifact Inspection

The report table records:

```text
R1/R2/R3: DB|NL_ASSERTION
T1/T2/T3: DB|COMMUNICATE
```

Each task has `locally_evaluable_components=DB` and a non-empty text-judged component. The CSV has one row per task and records action counts, communicate-info counts, and NL assertion counts.

## Reviewer Verdict

PASS WITH REVIEWER LIMITATION.

Independent subagent review remains unavailable due usage limit. Local second-pass review checked the code, unit tests, generated CSV, and Markdown report against the Phase 4 metric naming requirements.

## Reviewer Concerns

- This step does not implement confirmation QA.
- This step does not make any of the six existing tasks fully official-offline evaluable.
- Later task calibration must not use `local_proxy_success` as `official_reward_basis_success`.

## Resolution

The missingness is explicit in both code and artifacts. Later Stage-2.5b reports must use the new names and describe DB-only success as a local proxy.

## Final Gate Decision

`G4A_REWARD_BASIS_METRICS_PASS`: PASS WITH LIMITATION.

The gate is sufficient to proceed to confirmation evaluator QA because reward-basis missingness and metric naming are now explicit and tested.

## Next Allowed Step

Phase 4.4: implement controlled-user confirmation evaluator semantics and QA, keeping it separate from this reward-basis metric step.
