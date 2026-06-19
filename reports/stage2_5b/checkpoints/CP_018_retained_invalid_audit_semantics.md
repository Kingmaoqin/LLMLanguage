# Checkpoint CP-018

## Goal

Correct the block-audit semantics for a retained infrastructure-invalid run without deleting,
rerunning, or reclassifying that run as model behavior.

## Files Inspected

- `scripts/stage2_5b/run_full_blocks.py`
- `tests/stage2_5b/test_run_full_blocks.py`
- `gemma4_31b__retail_41/run_metrics.csv`
- `gemma4_31b__retail_41/adapter_errors.jsonl`
- `gemma4_31b__retail_41/run_bundles/`
- `reports/stage2_5b/run_blocks_v2_atomic/BLOCK_gemma4_31b_retail_41.md`

## Files Changed

- `scripts/stage2_5b/run_full_blocks.py`
- `tests/stage2_5b/test_run_full_blocks.py`

## Evidence Before Change

The Gemma/retail_41 block contained all 30 manifest, metric, terminal, and atomic bundle
records. One run was correctly retained as `invalid_run=true` after the Gemma endpoint
rejected a 16,385-token request against its frozen 16,384-token context limit.

The audit nevertheless required that invalid run to have the valid-only parser,
final-environment-state, and controlled-user artifacts. It also required all six condition
openings among valid rows even though the invalid condition had no valid opening. The block
therefore reported FAIL despite complete and honest invalid-run accounting.

## Implementation

- Parser, final-state, controlled-user opening, and initial-state invariance checks now use
  valid run IDs only.
- Expected valid condition coverage is derived from the block's valid metric rows instead of
  hard-coding all six conditions.
- The invalid run remains in the 30-run block denominator, manifest, metric table, termination
  table, adapter-error log, and atomic bundle directory.
- Resume now rewrites a current block report even when a passing block is skipped, preventing
  stale FAIL Markdown from surviving after the underlying audit passes.
- Added a regression test for a retained invalid run with no valid-only artifacts.

## Tests Executed

```bash
python -m py_compile scripts/stage2_5b/run_full_blocks.py
conda run -n agentsearch python -m unittest tests.stage2_5b.test_run_full_blocks
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Test Results

- Block-runner tests: 5/5 PASS.
- All Stage-2.5b tests: 46/46 PASS.
- Gemma/retail_41 audit: PASS with 30 metrics, 29 valid runs, 1 retained invalid run.
- Valid-run rate: 96.67%, above the preflight threshold.

## Artifact Inspection

- The invalid run ID is
  `gemma4_31b__retail_41__insult_single__seed302__tpl2__temp0.0`.
- Its termination and adapter error record the context-window exception.
- The other 29 runs have complete parser, final-state, opening, and terminal coverage.
- No behavioral outcome was imputed for the invalid run.

## Reviewer Verdict

CONDITIONAL PASS.

## Reviewer Concerns

A separate reviewer agent was not available in this execution context. This checkpoint was
checked using a second evidence-only pass over the diff, regression test, block artifacts,
and the preregistered invalid-run rule.

## Resolution

The implementation now matches the frozen rule: every manifest row remains in integrity
accounting, while behavioral estimates and valid-only artifacts exclude infrastructure
failures. The fix changes audit interpretation only; it does not alter model prompts,
trajectories, evaluator values, or experiment data.

## Final Gate Decision

RETAINED-INVALID AUDIT SEMANTICS PASS WITH REVIEWER LIMITATION.

## Next Allowed Step

Complete the two remaining retail_28 blocks, refresh all 16 block reports, and run the global
G11 integrity audit.
