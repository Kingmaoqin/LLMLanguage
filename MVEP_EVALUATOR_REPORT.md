# MVEP Evaluator Report

## Decision

`MVEP-FAIL` for run `results/r7d_ipma/mvep/run_v1_20260712`.

The sealed offline evaluator implementation and deterministic fixtures passed all
tests, including insertion, deletion, duplication, reordering, target changes,
argument changes, official ENV scoring for write tasks, and required communication
plus unchanged DB state for no-write tasks. Empty communication cannot pass.

No trajectory reached `raw_trace.json` materialization, so neither the official ENV
score nor the communication score was computed for a complete runtime trajectory.
This is a runtime capture failure, not an evaluator PASS or a scientific result.

## Failure binding

- Failed cell: `retail_write_60__single__neutral__attempt2`
- One executor response was recorded: 4,804 prompt tokens, 248 completion tokens.
- The response contained `content=null` and one `modify_pending_order_items` call.
- The tool response and post-call DB hash were append-only recorded.
- Rendering the next request raised `TypeError: argument of type 'NoneType' is not iterable`.
- The trace terminated as `MVEP-FAIL-RENDER-AFTER-MODEL-CALL`.
- No silent retry and no endpoint fallback occurred.

## Remediation

Commit `1bae65e0e954a67b318d08d7abacb26fd22cad8e` normalizes a model tool-call
assistant message with no text to `content=""` before the next request render. It
also records request-render exceptions with the complete unrendered messages and
tools, input hash, stage, exception, `request_sent=false`, and `attempt=0`.

Offline seal result: **32 passed, 0 failed**. No model calls were made after failure.
