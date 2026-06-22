# Checkpoint CP-027

## Goal

Switch the active controlled user and runner from Python/runtime-generated policies to the
frozen state-machine policy and deterministic response library.

## Existing Implementation

`controlled_user.py` combined static policies, runtime scenario transformation, request
classification, response text, and a duplicate style wrapper. The runner created a generic
policy for any source task not in six Python constants.

## Problem Evidence

Runtime policy generation violated the fixed-library design and allowed benchmark prose to
affect user behavior at execution time. Events lacked `base_response_id`,
`confirmation_value`, explicit state transitions, and unrecognized-request metadata.

## Minimal Change Plan

Replace the canonical controlled-user module, update the runner and validation script, delete
the runtime-generic tests, and validate all frozen policies across all conditions.

## Files Changed

- `src/stage2_5b/controlled_user.py`
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `scripts/stage2_5b/validate_controlled_user.py`
- controlled-user tests
- controlled-user and confirmation QA reports

## Git Diff Summary

- Removed runtime `generic_policy_from_task` and `policy_override`.
- Reused the canonical social-style wrapper.
- Added deterministic `base_response_id` and `base_clean_text`.
- Added state-before/state-after, request type, structured slots, explicit
  `confirmation_value`, and `unrecognized_agent_request`.
- Rejected non-empty runtime user LLM configuration.
- Added frozen-policy/source-data files to runtime provenance hashing.
- Preserved task 21's one-time pre-confirmation revision as an explicit state transition.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_frozen_controlled_user_policy \
  tests.stage2_5b.test_controlled_user_determinism \
  tests.stage2_5b.test_confirmation_metadata \
  tests.stage2_5b.test_denial_metadata \
  tests.stage2_5b.test_style_content_separation \
  tests.stage2_5b.test_no_gold_leakage

conda run -n agentsearch python scripts/stage2_5b/validate_controlled_user.py
conda run -n agentsearch python scripts/stage2_5b/validate_confirmation_evaluator.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Targeted controlled-user tests: PASS, 12/12 after rework
- Full Stage-2.5b suite: PASS, 64/64
- Controlled-user invariance: PASS, 155/155 fixture groups and 930/930 condition rows
- Factual slots, confirmation decisions, response decisions, and object IDs: 100% agreement
- Gold-tool leakage: 0
- Hidden/style/process leakage: 0
- Structured confirmation precision/recall: 1.000 / 1.000 over 936 QA rows
- Compile and diff checks: PASS

## Artifact Inspection

Inspected task 21's revision then confirmation, task 6's desk-lamp-only confirmation, fixed
fallback output for an irrelevant question, style-wrapped output, and confirmation QA
confusion matrices.

## Dead-Code Check

The active runner has no runtime generic-policy path. The old generic-policy test was deleted
and replaced by frozen-policy behavior tests.

## Reviewer Findings

The first QA run found 126 false confirmations because the classifier treated
`confirm your identity` as action authorization. Identity classification was moved ahead of
action confirmation, after which structured precision and recall reached 1.000.

## Gate

PASS.

## Rework

1. Updated confirmation tests to allow the frozen task-21 revision state.
2. Updated the validator to evaluate final confirmation after that revision.
3. Fixed identity-vs-confirmation classifier precedence.
4. Reran all targeted, validation, QA, and full-suite checks.
