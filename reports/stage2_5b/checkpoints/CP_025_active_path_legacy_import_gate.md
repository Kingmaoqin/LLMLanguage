# Checkpoint CP-025

## Goal

Make Stage-2.5b runtime/configuration self-contained and add a permanent gate against legacy
imports, LLM-user fallback, and duplicate active implementations.

## Existing Implementation

Two active benchmark scripts imported `src.stage2_5.official_tau_evaluator`, and the active
experiment config referenced `data/stage2_5/task_policy_annotations.yaml`.

## Problem Evidence

The Stage-2.5b source path was clean after evaluator migration, but benchmark scan/freeze tools
and active configuration still depended on Stage-2.5 assets.

## Minimal Change Plan

Move policy annotations into `data/stage2_5b/`, update three benchmark scripts and active
config, and add a repository-level active-path test.

## Files Changed

- `data/stage2_5b/task_policy_annotations.yaml`
- `configs/stage2_5b/experiment.yaml`
- `scripts/stage2_5b/audit_reward_basis.py`
- `scripts/stage2_5b/scan_candidate_tasks.py`
- `scripts/stage2_5b/freeze_benchmark.py`
- `tests/stage2_5b/test_no_legacy_imports.py`

## Git Diff Summary

- Policy annotation version advanced to `stage2_5b_policy_annotations_v2`.
- All active benchmark tools now use `src.stage2_5b.evaluator`.
- Active config paths no longer reference `stage2_5/`.
- New tests reject legacy imports, runtime LLM-user selection, valence overlay use, old config
  paths, and duplicate version suffixes.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_no_legacy_imports \
  tests.stage2_5b.test_candidate_task_scan \
  tests.stage2_5b.test_reward_metric_semantics

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Targeted tests: PASS, 9/9
- Full Stage-2.5b suite: PASS, 64/64
- Compile and diff checks: PASS
- Active legacy imports: 0
- Runtime config/provenance hashing with the migrated policy file: PASS

## Artifact Inspection

Runtime hash generation produced non-missing policy, evaluator, and source-bundle hashes using
only Stage-2.5b canonical files.

## Dead-Code Check

Legacy evaluator modules are no longer imported anywhere under `src/stage2_5b/` or
`scripts/stage2_5b/`. Legacy runners and configs remain in their old locations pending the
separate archival step.

## Reviewer Findings

The active-path test intentionally constructs forbidden strings from fragments so the test
does not flag its own fixtures.

## Gate

PASS.

## Rework

None.
