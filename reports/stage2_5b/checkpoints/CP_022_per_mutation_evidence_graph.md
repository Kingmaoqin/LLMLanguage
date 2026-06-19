# Checkpoint CP-022

## Goal

Replace first-mutation evidence checking with a canonical per-mutation evidence graph.

## Existing Implementation

`src/stage2_5/evidence_graph_evaluator.py` found the first critical mutation and credited a
required fact if an admissible source tool occurred before that one step. Later mutations were
not independently checked.

## Problem Evidence

A source read after an early mutation could make a later mutation valid, but the old summary
could not represent one invalid mutation followed by one valid mutation. It also did not emit
the required mutation/fact/source rows.

## Minimal Change Plan

Add `src/stage2_5b/evidence_graph.py`, update only the canonical policy evaluator's consumption
of evidence summaries, and add focused tests. Runner integration is deferred to the next
checkpoint.

## Files Changed

- `src/stage2_5b/evidence_graph.py`
- `src/stage2_5b/evaluator.py`
- `tests/stage2_5b/test_evidence_graph_per_mutation.py`

## Git Diff Summary

The new evaluator emits:

```text
mutation_id
mutation_tool
mutation_step
required_fact
source_tool
source_step
observed_before_mutation
```

It also emits one summary per mutation and computes aggregate coverage over all required
mutation/fact checks.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_evidence_graph_per_mutation \
  tests.stage2_5b.test_structured_confirmation_evaluator

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Targeted tests: PASS, 8/8
- Full Stage-2.5b suite: PASS, 52/52
- Compile and diff checks: PASS

## Artifact Inspection

A synthetic two-mutation trace was inspected. The first mutation correctly reported missing
identity evidence; the second mutation credited the intervening lookup and passed.

## Dead-Code Check

No active import was changed in this isolated step. The legacy evidence evaluator remains
active only until the runner integration checkpoint.

## Reviewer Findings

The policy evaluator originally consumed fact-level rows and would have emitted one failure per
missing fact. It was corrected during review to consume mutation summaries, yielding one policy
failure per invalid mutation with all missing facts attached.

## Gate

PASS.

## Rework

Changed policy-failure consumption from `mutation_evidence` to `mutation_summaries` and reran
the full suite.
