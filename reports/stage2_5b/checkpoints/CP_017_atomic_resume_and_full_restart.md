# Checkpoint CP-017

## Goal
Prevent mixed-version or duplicate formal results after interruption, preserve the incomplete
2026-06-17 run unchanged, and restart the 480-run confirmatory matrix in a new atomic output
root.

## Files Inspected
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `scripts/stage2_5b/run_full_blocks.py`
- `tests/stage2_5b/test_run_full_blocks.py`
- `results/stage2_5b_repair/full_blocks_retail8_confirmatory_4gpu/`
- all existing formal block logs and reports

## Files Changed
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `scripts/stage2_5b/run_full_blocks.py`
- `tests/stage2_5b/test_run_full_blocks.py`
- `tests/stage2_5b/test_atomic_run_resume.py`

## Evidence Before Change
- The prior formal root stopped at 253/480 metric rows on 2026-06-17 around 23:05.
- No Stage-2.5b runner process remained.
- Three blocks were partial: Gemma/retail_19 23/30, Gemma/retail_21 17/30, and
  GPT-OSS/retail_21 3/30.
- Three tasks had not started for either model.
- Resume skipped only by `run_id`, rewrote `run_manifest.csv`, and did not record task-set,
  model-config, policy-annotation, source-bundle, or git-commit identity.
- A process interruption between JSONL append and metrics write could leave orphan or duplicate
  aggregate events.

## Implementation
- Added immutable per-block `run_contract.json`.
- Added a root-level `FULL_RUN_CONTRACT.json`.
- Added hashes for model config, task config, frozen task set, policy annotations, runtime source
  bundle, and git commit.
- Made existing manifests immutable: any mismatch requires a new output directory.
- Added one atomic JSON bundle per run. Aggregate CSV/JSONL files are rebuilt from bundles on
  resume, eliminating duplicate append and half-written aggregate state.
- Added bundle/contract/manifest metadata checks to block audit.
- Added served-model-ID checks for ports 8005, 8006, and 8192.
- Changed formal defaults to new `v2_atomic` output, log, and block-report directories.
- Preserved the incomplete `full_blocks_retail8_confirmatory_4gpu` root unchanged.

## Tests Executed
```bash
python -m py_compile scripts/stage2_5b/*.py src/stage2_5b/*.py tests/stage2_5b/*.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch python scripts/stage2_5b/run_full_blocks.py \
  --workers 4 \
  --gemma-base-urls http://127.0.0.1:8005/v1 http://127.0.0.1:8006/v1 \
  --dry-run
conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py \
  --phase full --models gemma4_31b --tasks retail_41 \
  --conditions neutral_single --seeds 300 \
  --base-url-override http://127.0.0.1:8005/v1 \
  --deployment-id gemma4_31b_port8005 --skip-endpoint-check \
  --output-dir results/stage2_5b_repair/atomic_resume_smoke_v1
```

The final smoke command was executed twice.

## Test Results
- Python compilation: PASS.
- Stage-2.5b tests: 45/45 PASS.
- Dry-run: 16 blocks, 480 expected runs, deterministic endpoint assignment.
- Real atomic smoke: 1 bundle, 1 metrics row, 1 terminal row, 0 adapter errors.
- Repeated smoke: `new_runs=0`, the existing run was skipped, and aggregate counts remained 1.
- Endpoint identities:
  - 8005: `g4`
  - 8006: `g4`
  - 8192: `gpt-oss`

## Artifact Inspection
- `results/stage2_5b_repair/atomic_resume_smoke_v1/run_contract.json`
- `results/stage2_5b_repair/atomic_resume_smoke_v1/run_bundles/`
- `results/stage2_5b_repair/atomic_resume_smoke_v1/run_metrics.csv`
- `results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic/FULL_RUN_CONTRACT.json`

Runtime source bundle SHA256:
`3d7a9139ed2db3b7ae9668c4e073829cbbbfeb7f028a4466c15ed479fd97f539`.

Frozen task-set SHA256:
`a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc`.

## Reviewer Verdict
CONDITIONAL PASS.

## Reviewer Concerns
- Independent subagent review was not invoked because the available delegation interface requires
  an explicit user request for subagents.
- The project commit remains the baseline commit with a dirty working tree; the exact executable
  state is therefore identified by `source_bundle_hash`, component hashes, and contracts.

## Resolution
- Per-run and per-root contracts make the dirty-tree executable state explicit and reject drift.
- Deterministic tests, a real run, and a real resume were inspected before formal launch.
- Independent result review remains required before G11/Phase 14 completion.

## Final Gate Decision
ATOMIC RESUME AND FULL-RESTART GATE PASS WITH REVIEWER LIMITATION.

## Next Allowed Step
Launch the full 480-run matrix in
`results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic` and inspect each completed
block before analysis.
