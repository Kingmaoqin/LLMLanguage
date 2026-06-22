# Checkpoint CP-024

## Goal

Move social-style template handling and trajectory metrics into the canonical Stage-2.5b path,
while separating benchmark-reference diagnostics from matched-neutral distances.

## Existing Implementation

The runner imported style-template helpers and trajectory metrics from `src/stage2_5/`.
Reference-action distance fields existed, while matched-neutral distances were recomputed only
inside the analysis script.

## Problem Evidence

The active import path violated the single-source requirement. Reference distance and social
robustness distance were also not named as separate estimands in the runtime API.

## Minimal Change Plan

Add canonical style and trajectory modules, update the runner and direct tests, and preserve
legacy output columns temporarily for historical analysis compatibility.

## Files Changed

- `src/stage2_5b/social_style_wrapper.py`
- `src/stage2_5b/trajectory_metrics.py`
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- trajectory and manifest tests

## Git Diff Summary

- Added validated style-template loading and deterministic first-turn/every-turn rendering.
- Added explicit `reference_tool_distance`, `reference_argument_distance`, and
  `reference_mutation_distance`.
- Added `matched_neutral_tool_distance`, `matched_neutral_argument_distance`,
  `matched_neutral_mutation_distance`, and `matched_neutral_branch_divergence`.
- Switched runner provenance hashes and imports to Stage-2.5b modules.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_trajectory_metric_semantics \
  tests.stage2_5b.test_manifest_subset_runner \
  tests.stage2_5b.test_atomic_run_resume

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Targeted tests: PASS, 9/9
- Full Stage-2.5b suite: PASS, 60/60
- Compile and diff checks: PASS
- Legacy style/trajectory imports in active paths: 0

## Artifact Inspection

A matched pair with identical tool names but different mutation arguments produced zero tool
distance, non-zero argument distance, and non-zero branch divergence, as intended.

## Dead-Code Check

The runner and tests no longer import legacy style or trajectory modules. Two benchmark audit
scripts still import the legacy official reward helper and are handled separately.

## Reviewer Findings

Historical analysis expects the old reference-distance column names. They remain as explicit
compatibility columns, while the new `reference_*` names establish the intended semantics.

## Gate

PASS.

## Rework

None.
