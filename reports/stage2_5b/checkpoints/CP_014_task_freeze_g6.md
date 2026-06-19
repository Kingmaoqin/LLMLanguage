# CP_014_task_freeze_g6

## Goal
Complete Phase 6: from the expanded retail calibration, freeze the confirmatory task set with a
hash (G6), and wire smoke/pilot/full to it.

## Files Inspected
- `results/stage2_5b_repair/triage_retail_gpt_oss/run_metrics.csv` (16 new retail, 3-seed)
- `results/stage2_5b_repair/calibration_retail8_{gemma,gpt_oss}/run_metrics.csv` (8 retail, 10-seed)
- `scripts/stage2_5b/run_stage2_5b_experiment.py` (`_phase_tasks` full-phase resolution)
- `configs/stage2_5b/tasks.yaml`

## Files Changed
- `data/stage2_5b/calibrated_tasks_frozen.yaml` (new) + `.sha256`
- `scripts/stage2_5b/run_stage2_5b_experiment.py` (full-phase task resolution bug fix)
- `reports/stage2_5b/TASK_CALIBRATION_REPORT.md` (new)

## Evidence Before Change
- Triage of 16 new retail tasks (gpt-oss, 3 seeds) found 5 additional mid-band tasks
  (retail_2/6/19/28/64).
- Unified 10-seed calibration of the final 8 retail tasks (both models) confirmed all 8 in the
  [0.15, 0.85] band on the cross-model mean (see TASK_CALIBRATION_REPORT.md table).
- Bug: `_phase_tasks(..., "full")` returned `list(payload["confirmatory_tasks"])`, i.e. a list
  of dicts, but `_build_matrix` and `task_map[cell["task_id"]]` require task_id strings — the
  full run would crash.

## Implementation
- Ran `calibrate_and_freeze_tasks.py --retail-local-db-confirmatory --freeze` over the
  `calibration_retail8_*` dirs. All 8 retail tasks classified `confirmatory`; frozen with
  SHA256 `a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc`.
- Fixed the full-phase resolution: `return [t["task_id"] for t in payload["confirmatory_tasks"]]`.
- `configs/stage2_5b/tasks.yaml` smoke_tasks (retail_41, retail_6) and pilot_tasks
  (retail_41, retail_6, retail_19, retail_2) are clean both-model-non-degenerate confirmatory tasks.

## Tests Executed
```bash
conda run -n agentsearch python scripts/stage2_5b/calibrate_and_freeze_tasks.py \
  --gemma results/stage2_5b_repair/calibration_retail8_gemma \
  --gpt-oss results/stage2_5b_repair/calibration_retail8_gpt_oss \
  --retail-local-db-confirmatory --min-confirmatory 6 --max-confirmatory 8 --freeze
conda run -n agentsearch python -c "... _phase_tasks(..., 'full', ...) ..."   # resolution check
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Test Results
- Freeze: `class counts: {'confirmatory': 8}`, `calibration complete: gemma=True gpt_oss=True`.
- Full-phase now resolves to 8 task_id strings, all present in task_map.
- Unit tests: OK (28 tests).

## Artifact Inspection
- `calibrated_tasks_frozen.yaml`: 8 retail tasks, mean neutral success 0.15–0.85, scope fields
  `primary_endpoint_scope: retail_local_db_with_official_nl_assertion_missing`,
  `official_reward_basis_success: MISSING_REPORTED_SEPARATELY`.
- `results/stage2_5b_audit/task_calibration_summary.csv`: per-task per-model rates.

## Reviewer Verdict
CONDITIONAL PASS (local review). Independent subagent review deferred to the post-full-run
results review (Phase 14) to conserve budget; recorded per §1.3.

## Reviewer Concerns
- Retail-only domain and official-NL-missing are real scope limitations, documented in
  TASK_CALIBRATION_REPORT.md and to be repeated in the pre-analysis plan + final report.
- Three of the eight tasks are degenerate on one model; per-model contrasts on those tasks have
  limited sensitivity. The pre-analysis plan must flag them.

## Final Gate Decision
`G6_TASK_CALIBRATION`: **PASS** (with the two recorded scope limitations).

## Next Allowed Step
Run the full smoke (2 tasks × 6 conditions × 1 seed × 2 models = 24 runs) and inspect for
structural integrity (G8). Then pilot (G9), pre-analysis plan (G10), full confirmatory run (G11).
