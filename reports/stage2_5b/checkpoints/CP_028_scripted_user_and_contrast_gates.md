# Checkpoint CP-028

## Goal

Add the exact fourth-round scripted-user and contrast gates and freeze the 16-task
neutral-calibration panel in active configuration.

## Existing Implementation

Equivalent tests existed under older names, but there were no dedicated unexpected-request,
runtime-user-LLM, or contrast-reference test modules. Calibration still selected all 31
candidate rows.

## Problem Evidence

An unbounded calibration set could include tasks without frozen policies. The repeated-abuse
reference was correct in analysis code but not frozen in experiment configuration.

## Minimal Change Plan

Rename and extend existing invariance tests, add three focused tests, add explicit contrasts,
and replace `all_candidates` with the frozen 16-task policy panel.

## Files Changed

- `configs/stage2_5b/experiment.yaml`
- `configs/stage2_5b/tasks.yaml`
- `tests/stage2_5b/test_scripted_user_determinism.py`
- `tests/stage2_5b/test_social_wrapper_invariance.py`
- `tests/stage2_5b/test_unexpected_request_fallback.py`
- `tests/stage2_5b/test_no_runtime_user_llm.py`
- `tests/stage2_5b/test_contrast_reference_mapping.py`

## Git Diff Summary

- Frozen four confirmatory style contrasts and one non-confirmatory schedule contrast.
- Enforced `abuse_repeated` versus `neutral_repeated`.
- Froze 16 neutral-only calibration tasks matching the policy data.
- Added deterministic response-ID, no-extra-turn, fixed-fallback, no-user-LLM, and contrast
  reference checks.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_scripted_user_determinism \
  tests.stage2_5b.test_social_wrapper_invariance \
  tests.stage2_5b.test_unexpected_request_fallback \
  tests.stage2_5b.test_no_runtime_user_llm \
  tests.stage2_5b.test_contrast_reference_mapping \
  tests.stage2_5b.test_response_library_schema

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Targeted gates: PASS, 13/13
- Full Stage-2.5b suite: PASS, 70/70
- Calibration config/policy panel equality: PASS, 16/16
- Compile and diff checks: PASS

## Artifact Inspection

Compared substantive response IDs across social conditions, counted repeated-condition user
turns, and inspected the configured reference for every contrast.

## Dead-Code Check

Old test filenames were moved rather than duplicated. No `*_new`, `*_fixed`, or `*_v2` active
test implementation was introduced.

## Reviewer Findings

The schedule contrast remains present but is explicitly marked non-confirmatory. This prevents
its accidental interpretation as a pure abuse effect.

## Gate

PASS.

## Rework

None.
