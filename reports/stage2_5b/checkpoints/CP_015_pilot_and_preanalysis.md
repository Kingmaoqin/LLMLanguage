# Checkpoint CP-015

## Goal
Pass the 96-run retail-only pilot, freeze the confirmatory analysis plan before full data,
and add a fail-fast full-block runner.

## Files Inspected
- `results/stage2_5b_repair/pilot_retail8_confirmatory/run_manifest.csv`
- `results/stage2_5b_repair/pilot_retail8_confirmatory/run_metrics.csv`
- all pilot terminal and process JSONL logs
- `第三轮实验意见` Phase 9-12 requirements
- `scripts/stage2_5b/run_stage2_5b_experiment.py`

## Files Changed
- `reports/stage2_5b/PREANALYSIS_PLAN.md`
- `reports/stage2_5b/PREANALYSIS_PLAN.md.sha256`
- `scripts/stage2_5b/run_full_blocks.py`
- `tests/stage2_5b/test_run_full_blocks.py`

## Evidence Before Change
- No preanalysis plan existed.
- A single 480-run command would not satisfy the required per-model/per-task block checks.
- The pilot was complete but had not yet been audited as a balanced matrix.

## Implementation
- Froze endpoint/process outcome families, five contrasts, matched blocks, task-cluster
  bootstrap, mixed-model fallback, equivalence margins, multiplicity, invalid-run handling,
  and the retail-only official-reward limitation.
- Added a 16-block serial runner. Each 30-run block validates manifest/metric equality,
  balance, hashes, valid parse rate, parser/final-state terminal coverage, undefined tools,
  orphan events, initial-state hashes, and controlled-user opening clean-text invariance.
- The runner stops immediately after a failed block and writes one report per block.

## Tests Executed
```bash
conda run -n agentsearch python -m unittest tests.stage2_5b.test_run_full_blocks
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch python scripts/stage2_5b/run_full_blocks.py --dry-run
```

## Test Results
- Pilot: 96/96 rows; zero missing/orphan/duplicate IDs; zero invalid runs; zero adapter errors.
- Pilot balance: 48/model, 24/task, 16/condition, 48/seed.
- Pilot has 13 MAX_STEPS valid behavioral outcomes; none were removed.
- Full-block tests: 2/2 PASS.
- Full Stage-2.5b tests before plan freeze: 40/40 PASS.
- Dry-run printed 16 blocks, each one model x one task x 30 cells.
- Frozen preanalysis SHA256:
  `1319f15ebd1a2ea00934cab171cc2e3f3ae9f6ec9e57ccb6f957d3bd67b88043`.

## Artifact Inspection
- Pilot terminal records: 96 final states, 96 parser-health rows, 96 evidence rows,
  96 branch rows, and 96 termination rows.
- Pilot process logs contain 2,992 conversation records and 810 normalized tool events.
- All five provenance hashes are single-valued across pilot metrics.

## Reviewer Verdict
CONDITIONAL PASS. Independent subagent review is unavailable because the reviewer tool hit
its usage limit. This limitation remains explicit and is not represented as an independent
PASS.

## Reviewer Concerns
- Official `NL_ASSERTION` remains unavailable offline.
- MAX_STEPS is frequent enough to require reporting, but it is a valid behavioral outcome.
- Full blocks must not mix hashes or silently resume after code/config changes.

## Resolution
- Official reward is prespecified as missing, not imputed.
- MAX_STEPS remains in denominators and process analysis.
- Block runner hard-codes and checks the frozen provenance hashes and stops on mismatch.

## Final Gate Decision
G9 PILOT PASS.
G10 PREANALYSIS FROZEN WITH REVIEWER LIMITATION.

## Next Allowed Step
Run the 16 full blocks and stop at the first failed block.
