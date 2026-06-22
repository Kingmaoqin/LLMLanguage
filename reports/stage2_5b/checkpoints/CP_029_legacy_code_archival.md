# Checkpoint CP-029

## Goal

Remove legacy Stage-2 and Stage-2.5 runners/evaluators from active source and script locations
without deleting historical code or result artifacts.

## Existing Implementation

Legacy runners remained at the repository root and under `scripts/`; replaced evaluator modules
remained under `src/stage2_5/`; old configs remained under `configs/stage2_5/`.

## Problem Evidence

Although no active import remained, the old locations still presented multiple apparent
experiment entry points and duplicate evaluator implementations.

## Minimal Change Plan

Move legacy code/configs into `legacy/stage2/` and `legacy/stage2_5/`, add recovery
documentation, and extend the no-legacy gate. Do not move or modify historical results and
reports.

## Files Changed

- Archived Stage-2 source, runner, analyzer, and config.
- Archived Stage-2.5 source package, runners, analyzers, validation scripts, and configs.
- Added `legacy/README.md`.
- Updated `tests/stage2_5b/test_no_legacy_imports.py`.
- Removed one stale legacy path from runtime provenance hashing.

## Git Diff Summary

All changes are Git-tracked moves except the legacy README, test extension, and removal of the
stale provenance path. No historical result file was changed.

## Tests

```text
python -m py_compile src/stage2_5b/*.py scripts/stage2_5b/*.py tests/stage2_5b/*.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Initial test: FAIL because runtime provenance still referenced the moved legacy conversation
  evaluator.
- Rework test: PASS, 71/71.
- Compile, diff, and active-path legacy-reference scan: PASS.

## Artifact Inspection

Verified the archived Stage-2.5 package contains all former evaluator modules and that the
pre-consolidation tag can recover the exact original tree.

## Dead-Code Check

The following old active locations no longer exist:

```text
src/valence.py
src/stage2_5/
run_stage2_experiment.py
scripts/run_stage2_5_experiment.py
scripts/analyze_stage2_5.py
configs/stage2_5/
```

## Reviewer Findings

The first full test exposed a stale file in `RUNTIME_SOURCE_PATHS`. It was removed because
conversation management is already part of `src/stage2_5b/evaluator.py`.

## Gate

PASS.

## Rework

Removed the stale provenance entry and reran the complete Stage-2.5b suite.
