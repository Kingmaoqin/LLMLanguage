# Checkpoint CP-020

## Goal

Protect the published Stage-2.5b baseline and establish the factual architecture inventory
required before any fourth-round refactor.

## Existing Implementation

Read the active Stage-2.5b runner, deterministic user, configs, tests, legacy Stage-2/2.5
runner and evaluator modules, README, final integrity audit, result review, and curated result
tables.

## Problem Evidence

- The Stage-2.5b runner imported seven runtime modules from `src.stage2_5`.
- Active config referenced a Stage-2.5 policy annotation file.
- Evidence evaluation was first-mutation-only.
- Branch output used `premature_or_invalid_action`.
- Metrics retained ambiguous `official_local_success` compatibility aliases.
- Controlled-user responsibilities were combined in one 687-line module.

## Minimal Change Plan

This checkpoint changes documentation only. It records the protected commit, creates a safety
tag and working branch, classifies active/legacy files, and freezes the migration plan before
runtime code changes.

## Files Changed

- `reports/stage2_5b/CURRENT_ARCHITECTURE_AUDIT.md`
- `reports/stage2_5b/ACTIVE_AND_LEGACY_CODE_MAP.md`
- `reports/stage2_5b/checkpoints/CP_020_architecture_audit_and_safety_point.md`

## Git Diff Summary

Added factual architecture, historical-result, and migration inventories. No runtime code,
config, or result artifact was modified.

## Tests

```text
python -m py_compile src/stage2_5b/*.py scripts/stage2_5b/*.py tests/stage2_5b/*.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Compile: PASS
- Unit tests: PASS, 46/46
- Historical result accounting: 480 expected / 480 metrics / 479 valid / 1 retained invalid

## Artifact Inspection

Inspected `FINAL_INTEGRITY_AUDIT.md`, `INDEPENDENT_RESULTS_REVIEW.md`,
`confirmatory_run_metrics.csv`, `matched_pairs.csv`, and `final_integrity_report.csv`.

## Dead-Code Check

No code was added. The inventory identifies legacy modules and the currently active
Stage-2.5 modules that must be migrated before archival.

## Reviewer Findings

Self-review against the fourth-round prompt found the baseline runnable but non-compliant with
the single-active-path requirement. Historical results are internally complete but tied to the
protected source hashes.

## Gate

PASS.

## Rework

None.
