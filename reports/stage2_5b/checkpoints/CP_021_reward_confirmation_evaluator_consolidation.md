# Checkpoint CP-021

## Goal

Move reward, confirmation-policy, safe-success, and conversation-management evaluation into
the canonical Stage-2.5b path and remove ambiguous success aliases from new runtime outputs.

## Existing Implementation

The active runner imported official reward, safe task, and conversation management evaluators
from `src/stage2_5/`. Confirmation accepted a regex fallback when structured user metadata was
missing. Reward output included `official_local_success` and `official_task_success`.

## Problem Evidence

- Regex confirmation can treat politeness or unrelated affirmative language as authorization.
- The fourth-round protocol requires `speech_act == confirm`, a true confirmation decision,
  and confirmation strictly before mutation.
- Compatibility aliases obscured the distinction between official reward and local proxy.

## Minimal Change Plan

Create one canonical `src/stage2_5b/evaluator.py`, update the Stage-2.5b runner and the
confirmation sensitivity script, and update evaluator tests. Evidence and branch logic remain
unchanged in this checkpoint.

## Files Changed

- `src/stage2_5b/evaluator.py`
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `scripts/stage2_5b/validate_confirmation_evaluator.py`
- evaluator unit tests

## Git Diff Summary

- Added explicit `official_reward_metrics`.
- Removed new-output aliases `official_local_success` and `official_task_success`.
- Made structured confirmation metadata mandatory for formal policy evaluation.
- Enforced confirmation turn `<` mutation turn.
- Kept text regex only in the standalone sensitivity QA.
- Moved conversation-management diagnostics into the canonical evaluator module.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_reward_metric_semantics \
  tests.stage2_5b.test_structured_confirmation_evaluator

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
python -m py_compile src/stage2_5b/*.py scripts/stage2_5b/*.py tests/stage2_5b/*.py
```

## Results

- Targeted evaluator tests: PASS, 8/8
- Full Stage-2.5b suite: PASS, 48/48
- Compile: PASS

## Artifact Inspection

Inspected returned policy-failure rows for valid structured confirmation, non-confirmation,
same-turn confirmation, and missing structured metadata. Same-turn and missing-metadata cases
are correctly classified as failures.

## Dead-Code Check

The active runner no longer imports Stage-2.5 official, safe, or conversation evaluators.
`scan_candidate_tasks.py` and `audit_reward_basis.py` still import the legacy official helper;
those imports are explicitly deferred to the active-path migration checkpoint.

## Reviewer Findings

Self-review found one compatibility requirement: existing controlled-user events still use the
field `confirmation`. The canonical evaluator accepts that field temporarily but prioritizes
`confirmation_value`; the controlled-user checkpoint must emit both explicit speech act and
confirmation value before smoke execution.

## Gate

PASS.

## Rework

None.
