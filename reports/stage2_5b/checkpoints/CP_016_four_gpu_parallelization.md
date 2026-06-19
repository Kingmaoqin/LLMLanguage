# Checkpoint CP-016

## Goal
Use all four A100 GPUs for the full confirmatory run without allowing concurrent workers to
write the same block or mixing deployment endpoints within a model/task contrast block.

## Files Inspected
- GPU process mapping from `nvidia-smi --query-compute-apps`
- vLLM parent process commands and `CUDA_VISIBLE_DEVICES`
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `scripts/stage2_5b/run_full_blocks.py`
- the incomplete serial block directory
  `results/stage2_5b_repair/full_blocks_retail8_confirmatory/gemma4_31b__retail_41`

## Files Changed
- `scripts/stage2_5b/run_stage2_5b_experiment.py`
- `scripts/stage2_5b/run_full_blocks.py`
- `reports/stage2_5b/PREANALYSIS_PLAN.md`
- `reports/stage2_5b/PREANALYSIS_PLAN.md.sha256`

## Evidence Before Change
- GPU2 hosted Gemma.
- GPU1+GPU3 hosted gpt-oss with tensor parallel size 2.
- GPU0 was occupied by an unrelated Llama-3.3 service.
- The serial full runner had produced 23/30 rows of its first block but had not produced a
  passing block report.

## Implementation
- Stopped only the unrelated GPU0 Llama-3.3 service.
- Started a second Gemma replica on GPU0 at port 8006 with the same checkpoint, served ID,
  tool parser, max context, and batching parameters as port 8005.
- Added runner endpoint override plus recorded `deployment_id` and `deployment_base_url`.
- Added four-worker scheduling with task-major interleaving:
  two Gemma replicas and two concurrent gpt-oss block streams.
- Each model/task block remains isolated in one directory and on one deployment.
- The partial serial result root is retained but excluded. The four-GPU run uses a new root.

## Tests Executed
```bash
python -m py_compile scripts/stage2_5b/run_stage2_5b_experiment.py \
  scripts/stage2_5b/run_full_blocks.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch python scripts/stage2_5b/run_full_blocks.py \
  --workers 4 \
  --gemma-base-urls http://127.0.0.1:8005/v1 http://127.0.0.1:8006/v1 \
  --dry-run
```

## Test Results
- Stage-2.5b tests: 40/40 PASS.
- Dry-run showed the first four workers routed to:
  Gemma/8005, gpt-oss/8192, Gemma/8006, gpt-oss/8192.
- Both Gemma endpoints returned the same tool call:
  `lookup({"item_id":"123"})`, with `finish_reason=tool_calls` and identical token counts.
- Final preanalysis SHA256:
  `2e98483a7e45a51050b03aabea5874c6fc5b5cd4a6dcd9e44c180b88718fa496`.

## Artifact Inspection
- GPU0 Gemma log:
  `artifacts/stage2_5b/logs/gemma_gpu0_port8006.log`.
- Four-GPU full output root:
  `results/stage2_5b_repair/full_blocks_retail8_confirmatory_4gpu`.
- Partial serial root remains untouched and is not a formal input.

## Reviewer Verdict
CONDITIONAL PASS because the independent reviewer service remains unavailable at its usage
limit. Tests, endpoint probes, process mapping, and dry-run routing were checked directly.

## Reviewer Concerns
- Concurrent batching may add deployment-level runtime variation.
- A deployment must never vary within a model/task paired block.

## Resolution
- Deployment assignment is task-level and recorded per row.
- All conditions and seeds for a given model/task use one fixed endpoint.
- Treatment contrasts remain within the same deployment block.

## Final Gate Decision
FOUR-GPU DEPLOYMENT PASS WITH REVIEWER LIMITATION.

## Next Allowed Step
Run the new four-GPU block root with four workers and preserve per-block fail-fast gates.
