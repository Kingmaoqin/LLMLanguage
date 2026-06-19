# Checkpoint CP-014

## Goal
Complete the CP-013 retail-expansion calibration gate, freeze a retail-only confirmatory
task set with explicit metric-scope limitations, and pass a balanced two-model smoke before
the pilot.

## Files Inspected
- `reports/stage2_5b/checkpoints/CP_013_calibration_diagnosis_and_retail_expansion.md`
- `results/stage2_5b_repair/calibration_retail8_gemma/run_manifest.csv`
- `results/stage2_5b_repair/calibration_retail8_gemma/run_metrics.csv`
- `results/stage2_5b_repair/calibration_retail8_gpt_oss/run_manifest.csv`
- `results/stage2_5b_repair/calibration_retail8_gpt_oss/run_metrics.csv`
- `data/stage2_5b/candidate_tasks.csv`
- `data/stage2_5b/candidate_tasks_v1.csv`
- `scripts/stage2_5b/calibrate_and_freeze_tasks.py`
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `configs/stage2_5b/tasks.yaml`

## Files Changed
- `scripts/stage2_5b/calibrate_and_freeze_tasks.py`
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `scripts/stage2_5b/select_calibrated_tasks.py`
- `tests/stage2_5b/test_calibrate_and_freeze_tasks.py`
- `tests/stage2_5b/test_manifest_subset_runner.py`
- `tests/stage2_5b/test_candidate_task_scan.py`
- `tests/stage2_5b/test_select_calibrated_tasks.py`
- `configs/stage2_5b/tasks.yaml`
- `data/stage2_5b/calibrated_tasks_frozen.yaml`
- `data/stage2_5b/calibrated_tasks_frozen.yaml.sha256`
- `results/stage2_5b_audit/task_calibration_summary.csv`

## Evidence Before Change
- The current candidate scan was expanded by CP-013 to 24 retail plus 7 airline tasks, but
  the candidate-scan unit test still enforced the superseded 10-15 total.
- `calibrate_and_freeze_tasks.py` required all 31 structural candidates to have ten runs in
  both models even when the explicit CP-013 calibration set contained eight retail tasks.
- The script always demoted `DB|NL_ASSERTION` retail tasks, despite the recorded CP-013
  decision to make local DB endpoints primary and report the unavailable official
  `NL_ASSERTION` component as missing.
- An attempted CP-012 missing-run repair split seeds by task. Because the runner assigned
  `template_block` from each supplied seed list index, some shard run IDs did not match the
  original full-manifest cells. Those shard directories are retained as failure evidence
  but excluded from all formal calibration and confirmatory artifacts.

## Implementation
- Added explicit manifest-subset execution to the runner so future repairs preserve the
  original `task_id`, `seed`, `template_block`, and `template_id` assignments.
- Made calibration completion depend on the tasks actually present in the two calibration
  inputs, not every row in the expanded structural candidate pool.
- Added the explicit `--retail-local-db-confirmatory` switch. It is limited to retail-only
  calibrated sets and records that `official_reward_basis_success` is missing because the
  reward basis includes `NL_ASSERTION`.
- Updated the candidate-scan test to validate the configured `TARGET_PER_DOMAIN` total
  instead of the superseded hard-coded upper bound of 15.
- Froze the eight-task retail confirmatory set and changed smoke/pilot task lists to subsets
  of that frozen set.

## Tests Executed
```bash
python -m py_compile scripts/stage2_5b/run_stage2_5b_experiment.py
python -m py_compile scripts/stage2_5b/calibrate_and_freeze_tasks.py
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_calibrate_and_freeze_tasks \
  tests.stage2_5b.test_manifest_subset_runner \
  tests.stage2_5b.test_candidate_task_scan
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch python scripts/stage2_5b/calibrate_and_freeze_tasks.py \
  --gemma results/stage2_5b_repair/calibration_retail8_gemma \
  --gpt-oss results/stage2_5b_repair/calibration_retail8_gpt_oss \
  --retail-local-db-confirmatory --freeze
conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py \
  --phase smoke --models gemma4_31b gpt_oss_120b \
  --output-dir results/stage2_5b_repair/smoke_retail8_confirmatory
```

## Test Results
- Stage-2.5b unit tests: 38/38 PASS.
- Retail calibration: 80/80 Gemma and 80/80 gpt-oss rows, zero invalid runs.
- Calibration classification: 8 confirmatory tasks.
- Frozen task SHA256:
  `a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc`.
- Smoke: 24/24 rows, 24 unique run IDs, zero missing/orphan/duplicate rows, zero
  invalid runs, zero adapter errors.
- Smoke balance: 12 runs/model, 12 runs/task, and 4 runs for each of six conditions.

## Artifact Inspection
- `results/stage2_5b_audit/task_calibration_summary.csv` contains ten calibration rows per
  task and model with invalid rate 0.
- `data/stage2_5b/calibrated_tasks_frozen.yaml` records:
  `primary_endpoint_scope=retail_local_db_with_official_nl_assertion_missing`.
- Frozen tasks:
  `retail_41`, `retail_6`, `retail_19`, `retail_2`, `retail_21`, `retail_64`,
  `retail_23`, `retail_28`.
- Smoke terminal artifacts contain 24 final environment states, 24 evidence records,
  24 branch records, 24 termination records, and 24 parser-health records.

## Reviewer Verdict
CONDITIONAL PASS: independent subagent review was requested twice. The previous reviewer
session returned no verdict, and the replacement reviewer errored because the subagent usage
limit was reached. A deterministic second-pass inspection and full unit/integrity checks were
performed, but this is not represented as an independent reviewer PASS.

## Reviewer Concerns
- The confirmatory claim is retail-only.
- `official_reward_basis_success` cannot be treated as locally observed for these tasks;
  local DB final-state and safe-task metrics are primary, with the missing official
  `NL_ASSERTION` component reported explicitly.
- The failed CP-012 shard repair must remain excluded from formal inputs.

## Resolution
- The scope limitation is encoded in the frozen YAML and calibration summary.
- Smoke and pilot task configuration now contains only frozen retail tasks.
- Formal calibration references only the complete `calibration_retail8_*` directories.
- The runner now supports exact manifest-cell repair to prevent template assignment drift.

## Final Gate Decision
G6 RETAIL-ONLY CALIBRATION/FREEZE PASS WITH REVIEWER LIMITATION.
G8 RETAIL-ONLY SMOKE PASS.

## Next Allowed Step
Run the 96-row retail-only pilot, audit integrity and endpoint/process stability, then freeze
the pre-analysis plan before the 480-row confirmatory run.
