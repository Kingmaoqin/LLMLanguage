# CP_007_trajectory_metric_semantics

## Goal

Implement true trajectory/process diagnostics without using reference action matching as a task-success criterion.

## Files Inspected

- `src/stage2_5/trajectory_metrics.py`
- `src/adapters/normalize.py`
- `scripts/run_stage2_5_experiment.py`
- `data/irmstu_tasks/tau_adapted_tasks.yaml`

## Files Changed

- `src/stage2_5/trajectory_metrics.py`
- `tests/stage2_5b/test_trajectory_metric_semantics.py`
- `reports/stage2_5b/TRAJECTORY_METRIC_SEMANTICS.md`
- `reports/stage2_5b/checkpoints/CP_007_trajectory_metric_semantics.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`

## Evidence Before Change

`trajectory_summary` only emitted:

- tool sequence string;
- sequence length;
- unique tool count;
- read/write counts.

It did not compute the required tool-name edit distance, argument-aware distance, or mutation-sequence distance.

## Implementation

Extended `trajectory_metrics.py` with:

- `reference_tool_sequence`;
- `reference_argument_sequence`;
- `reference_mutation_sequence`;
- `event_argument_sequence`;
- `mutation_sequence`;
- normalized Levenshtein distances.

`trajectory_summary(events, reference_task)` now emits:

- `tool_name_sequence_distance`;
- `critical_argument_sequence_distance`;
- `mutation_sequence_distance`;
- normalized variants;
- reference sequence lengths.

`reports/stage2_5b/TRAJECTORY_METRIC_SEMANTICS.md` records that these are diagnostics only and not success criteria.

## Tests Executed

- `python -m py_compile src/stage2_5/trajectory_metrics.py tests/stage2_5b/test_trajectory_metric_semantics.py`
- `conda run -n agentsearch python -m unittest discover -s tests/stage2_5b`

## Test Results

Initial test run failed:

```text
TypeError: unhashable type: 'dict'
```

Cause: `_stable_args` used set membership with dict values.

Repair:

```text
if value is None or value == "":
```

Final unit test result:

```text
Ran 15 tests
OK
```

## Artifact Inspection

`TRAJECTORY_METRIC_SEMANTICS.md` explicitly states:

- reference actions are diagnostic only;
- non-zero distance is not automatically a policy failure;
- wrong-object mutations can be visible in argument-aware distance even when tool-name distance is zero.

## Reviewer Verdict

PASS WITH REVIEWER LIMITATION.

Independent subagent review remains unavailable due usage limit. Local second-pass review checked the tests, failure/repair cycle, and semantics report.

## Reviewer Concerns

- Existing legacy runner still calls `trajectory_summary(events)` without `reference_task`, so distances are `None` unless the Stage-2.5b runner passes the tau2 task.
- Distance metrics are diagnostic; later analysis must not call them correctness metrics without policy/final-state context.

## Resolution

Stage-2.5b runner integration must call `trajectory_summary(events, tau2_task)`. The semantics report prevents treating action-reference distance as success.

## Final Gate Decision

`G4C_TRAJECTORY_METRICS_PASS`: PASS WITH INTEGRATION REQUIREMENT.

The metric functions and tests pass; runner integration remains a later gate.

## Next Allowed Step

Phase 5: template lexical and semantic manipulation checks, then freeze the template file for Stage-2.5b.
