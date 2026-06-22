# Checkpoint CP-023

## Goal

Integrate the canonical evidence graph into the runner and replace merged branch labels with
the six required branch outcomes.

## Existing Implementation

The runner still imported legacy evidence and branch evaluators. Branch evaluation emitted
`premature_or_invalid_action`, and generic annotations listed the same mutation as both valid
and invalid.

## Problem Evidence

The merged branch label prevented separate measurement of timing errors and invalid choices.
The generic annotation overlap also made branch classification internally contradictory.

## Minimal Change Plan

Add one canonical branch evaluator, update runner imports/provenance/output materialization, and
add branch-label tests. No controlled-user or trajectory code is changed.

## Files Changed

- `src/stage2_5b/branch_evaluator.py`
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `tests/stage2_5b/test_branch_evaluator_labels.py`

## Git Diff Summary

- Added `correct_revision`, `missed_revision`, `premature_action`, `invalid_action`,
  `not_reached`, and `reached_unscored`.
- Removed valid/invalid overlap before classification.
- Switched runner evidence and branch imports to `src.stage2_5b`.
- Wrote fact-level and mutation-summary evidence rows to `evidence_events.jsonl`.
- Kept large evidence detail lists out of `run_metrics.csv`.
- Removed contradictory generic `invalid_actions`.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_branch_evaluator_labels \
  tests.stage2_5b.test_evidence_graph_per_mutation \
  tests.stage2_5b.test_atomic_run_resume \
  tests.stage2_5b.test_manifest_subset_runner

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Targeted tests: PASS, 16/16
- Full Stage-2.5b suite: PASS, 59/59
- Compile and diff checks: PASS
- Legacy branch/evidence imports in active paths: 0

## Artifact Inspection

Synthetic branch fixtures produced each of the six expected labels. Evidence fixtures produced
separate `required_fact` and `mutation_summary` records suitable for JSONL audit.

## Dead-Code Check

Stage-2.5b no longer imports the legacy branch or evidence modules. The old files remain only
for legacy runner recovery until final archival.

## Reviewer Findings

The original generic annotation used the same tool in valid and invalid action sets. The new
evaluator defensively removes overlap, and the runner now generates an empty invalid set unless
an actual invalid alternative is known.

## Gate

PASS.

## Rework

None.
