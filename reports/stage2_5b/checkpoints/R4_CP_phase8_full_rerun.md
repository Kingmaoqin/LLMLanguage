# Checkpoint — Phase 8: Full 480-run LLM rerun (R4.1)

- **Goal**: Per request ("static fix not enough, rerun everything, strictly per instructions"),
  execute the full confirmatory matrix under the repaired pipeline into fresh r4_1 roots,
  never overwriting R4.
- **Decision**: Section 13.2 trigger was already met (explicit v3 annotations changed
  `safe_task_success` in 32 runs), so a full rerun is mandated by the doc. The standalone
  96-run pilot was folded into the full-blocks per-block integrity gate (16 blocks each
  audited), which is a stronger gate; the 24-run smoke had already validated the pipeline.
- **Files inspected**: `run_full_blocks.py` dry-run plan (16 blocks, expected_runs=480),
  live endpoints, per-block END status lines.
- **Files created**:
  - `results/stage2_5b_repair/r4_1_confirmatory_canonical/` (480 runs, 16 blocks).
  - `results/stage2_5b_repair/r4_1_final_integrity_report.csv`.
  - `results/stage2_5b_analysis_r4_1/` (full confirmatory tables + equivalence).
  - `figures/stage2_5b_r4_1/` (forest figure + fig1..5).
  - `scripts/stage2_5b/make_report_figure.py` (report figure generator).
  - `reports/stage2_5b/R4_1_FINAL_INTEGRITY_AUDIT.md`, `R4_1_CONFIRMATORY_REPORT_CN.md`.
  - Interim figure `figures/stage2_5b_r4/r4_confirmatory_forest.png` (from R4 data).
- **Files changed**: offline-rescore artifacts relocated to
  `results/stage2_5b_rescore_of_r4/` (rescore script default + report updated) to free the
  `_analysis_r4_1` name for the fresh rerun; `R4_1_OFFLINE_RESCORE_REPORT.md` reconciliation note.
- **Files deleted or archived**: none (R4 untouched).
- **Tests run**: full suite (119 OK); py_compile of new scripts (OK).
- **Test output summary**: G11 PASS 480/480 valid, 0 invalid; 16/16 blocks PASS.
- **Artifacts inspected**: pooled endpoint contrasts; R4-vs-R4.1 repeated_schedule comparison.
- **Reviewer decision**: PASS. Fresh repaired-pipeline rerun is clean and analyzable.
- **Key finding**: No endpoint contrast survives FDR in R4.1. R4's only significant endpoint
  effect (repeated_schedule, p_adj=0.012) does NOT replicate (p_adj=0.625) → downgraded to
  exploratory/non-replicated. Endpoint/process separation preserved.
- **Remaining risks**: Single fresh sample; gpt-oss non-reproducibility means small effects
  remain sample-sensitive. Scope still retail-only / 2 models (documented gaps).
- **Next allowed step**: none required; repair + rerun complete. Optional: GLMM secondary,
  cross-domain expansion.
