# Checkpoint CP-031

## Goal

Correct mutation/evidence classification after inspecting the first real fourth-round trace.

## Existing Implementation

`IRREVERSIBLE_TOOLS` omitted retail address/payment mutations and airline passenger updates.
Generic annotations therefore treated those state-changing calls as evidence reads.

## Problem Evidence

The first real run,
`gemma4_31b__retail_41__neutral_single__seed300__tpl0__temp0.0`, succeeded, but its evidence
rows incorrectly required `modify_user_address` and `modify_pending_order_address` as evidence
before `modify_pending_order_items`. Normalized events labeled both address changes as reads
even though their state hashes changed.

## Minimal Change Plan

Expand the canonical mutation-tool set and add a focused classification test. Do not reinterpret
or overwrite the first integration artifact; rerun in a new directory after committing.

## Files Changed

- `src/adapters/normalize.py`
- `tests/stage2_5b/test_mutation_tool_classification.py`

## Git Diff Summary

Added:

```text
modify_pending_order_address
modify_pending_order_payment
modify_user_address
update_reservation_passengers
```

Existing cancellation, return, exchange, booking, certificate, transfer, baggage, and flight
mutations remain classified as writes.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_mutation_tool_classification \
  tests.stage2_5b.test_trajectory_metric_semantics \
  tests.stage2_5b.test_candidate_task_scan
```

## Results

- Targeted tests: PASS, 8/8
- Compile and diff checks: PASS

## Artifact Inspection

Inspected normalized events and state-hash changes from the real integration run. The defect
was evaluator metadata, not model behavior or environment state.

## Dead-Code Check

No duplicate mutation list was introduced; existing consumers continue to use the one canonical
set from `src/adapters/normalize.py`.

## Reviewer Findings

The constant's historical name says “irreversible,” but its experimental role is the complete
state-changing/consequential mutation boundary. The comment now states this explicitly.

## Gate

PASS.

## Rework

The original one-cell artifact is retained as a failed pre-smoke diagnostic and will not be
mixed into formal smoke results.
