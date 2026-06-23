# Stage-2.5b Reproduction Guide

## 1. Fixed scope

The confirmatory matrix is:

```text
2 models × 8 retail tasks × 6 conditions × 5 seeds = 480 runs
```

Formal (R4 canonical) result root:

```text
results/stage2_5b_repair/r4_confirmatory_canonical
```

This is the single canonical root. All active scripts default to it
(see `src/stage2_5b/canonical_paths.py`). The earlier round-3 roots
`full_blocks_retail8_confirmatory_v2_atomic`, `full_blocks_retail8_confirmatory`, and
`full_blocks_retail8_confirmatory_4gpu` are preserved for audit only and must never be
combined with the canonical root, nor reached except by an explicit `--root` argument.

> **Scope note.** This study is a single-session, user-to-agent social-valence
> perturbation study on a single tool-using LLM agent. Multi-agent peer influence /
> social contagion is explicitly **out of scope** and is not a requirement of the
> proposal — it must not be treated as a current gap.

## 2. Verify frozen inputs

Run from `/home/xqin5/llmlanguage/ir_mstu_stage2`:

```bash
sha256sum -c data/stage2_5b/calibrated_tasks_frozen.yaml.sha256
sha256sum -c reports/stage2_5b/PREANALYSIS_PLAN.md.sha256
python -m json.tool results/stage2_5b_repair/r4_confirmatory_canonical/FULL_RUN_CONTRACT.json
git rev-parse HEAD
git status --short
```

The executable experimental state is identified by the hashes in
`FULL_RUN_CONTRACT.json` and each block's `run_contract.json`. The benchmark provenance
(tau2 base commit + the single exported working-tree patch) is recorded in
`artifacts/stage2_5b/benchmark_patches/PATCH_MANIFEST.json` and the snapshot manifest
`artifacts/stage2_5b/tau_snapshot_manifest.json`; the Git commit alone is not a sufficient
runtime identifier.

## 3. Python environment and tests

```bash
conda run -n agentsearch python -m py_compile \
  scripts/stage2_5b/*.py src/stage2_5b/*.py tests/stage2_5b/*.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

Expected final Stage-2.5b unit-test result: 115 tests passing (R4 minimal-repair baseline).

## 4. Model services

The formal run used:

- Gemma-4-31B-it on GPU2, port 8005, served ID `g4`.
- A matching Gemma-4-31B-it replica on GPU0, port 8006, served ID `g4`.
- gpt-oss-120B on GPU1+GPU3 with tensor parallel size 2, port 8192, served ID `gpt-oss`.

Equivalent launch commands are:

```bash
CUDA_VISIBLE_DEVICES=2 conda run -n p08_skilloverload vllm serve \
  /home/xqin5/hf_p08_models/gemma-4-31B-it \
  --port 8005 --served-model-name g4 \
  --enable-auto-tool-choice --tool-call-parser gemma4 \
  --gpu-memory-utilization 0.92 --max-model-len 16384 \
  --max-num-batched-tokens 8192

CUDA_VISIBLE_DEVICES=0 conda run -n p08_skilloverload vllm serve \
  /home/xqin5/hf_p08_models/gemma-4-31B-it \
  --port 8006 --served-model-name g4 \
  --enable-auto-tool-choice --tool-call-parser gemma4 \
  --gpu-memory-utilization 0.92 --max-model-len 16384 \
  --max-num-batched-tokens 8192

CUDA_VISIBLE_DEVICES=1,3 conda run -n p08_skilloverload vllm serve \
  /home/xqin5/hf_p08_models/gpt-oss-120b \
  --served-model-name gpt-oss --port 8192 \
  --tensor-parallel-size 2 --max-model-len 65536 \
  --gpu-memory-utilization 0.90 --trust-remote-code \
  --enable-auto-tool-choice --tool-call-parser openai
```

Verify endpoint identity before running:

```bash
curl -s http://127.0.0.1:8005/v1/models
curl -s http://127.0.0.1:8006/v1/models
curl -s http://127.0.0.1:8192/v1/models
```

## 5. Smoke and pilot

```bash
conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py \
  --phase smoke --models gemma4_31b gpt_oss_120b \
  --output-dir results/stage2_5b_repair/smoke_retail8_confirmatory

conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py \
  --phase pilot --models gemma4_31b gpt_oss_120b \
  --output-dir results/stage2_5b_repair/pilot_retail8_confirmatory
```

Existing immutable manifests prevent accidental resume with changed task, template, model,
or runtime hashes. Use a new output directory for an independent reproduction.

## 6. Full atomic run

Dry-run the scheduler:

```bash
conda run -n agentsearch python scripts/stage2_5b/run_full_blocks.py \
  --workers 4 \
  --gemma-base-urls http://127.0.0.1:8005/v1 http://127.0.0.1:8006/v1 \
  --dry-run
```

Run or safely resume:

```bash
conda run -n agentsearch python scripts/stage2_5b/run_full_blocks.py \
  --workers 4 \
  --gemma-base-urls http://127.0.0.1:8005/v1 http://127.0.0.1:8006/v1
```

Each model/task block has 30 cells. Completed valid blocks are audited and skipped. Atomic
per-run bundles are materialized back into aggregate CSV/JSONL files, preventing duplicate
append records after interruption.

## 7. G11 integrity audit

```bash
python scripts/stage2_5b/final_integrity_audit.py
```

This must report `PASS` before confirmatory statistics are run. With no arguments it reads
the R4 canonical root and produces:

```text
results/stage2_5b_repair/r4_final_integrity_report.csv
reports/stage2_5b/R4_FINAL_INTEGRITY_AUDIT.md
```

## 8. Confirmatory analysis

```bash
python scripts/stage2_5b/analyze_confirmatory.py
python scripts/stage2_5b/equivalence_analysis.py
python scripts/stage2_5b/extract_failure_cases.py
```

The main script refuses to analyze fewer than 480 metric rows or a non-PASS G11 artifact.
It uses 10,000 task-cluster bootstrap replicates and the frozen pairing key
`model_alias × task_id × seed × template_block`.

Secondary GLMM entry point:

```bash
Rscript scripts/stage2_5b/run_glmm.R
```

If `Rscript`/`lme4` is unavailable, `glmm_status.csv` records `NOT_FIT`; this does not replace
or invalidate the preregistered primary task-cluster bootstrap.

## 9. Main outputs

```text
results/stage2_5b_analysis_r4/confirmatory_run_metrics.csv
results/stage2_5b_analysis_r4/matched_pairs.csv
results/stage2_5b_analysis_r4/paired_contrasts_task_cluster_bootstrap.csv
results/stage2_5b_analysis_r4/equivalence_results.csv
results/stage2_5b_analysis_r4/per_task_diagnostics.csv
results/stage2_5b_analysis_r4/summary_by_model_condition.csv
figures/stage2_5b_r4/
reports/stage2_5b/FAILURE_CASES.md
```

`official_reward_basis_success` remains missing because the selected retail tasks include an
offline-unavailable `NL_ASSERTION` component. Do not impute it from DB-based local or safe
success metrics.
