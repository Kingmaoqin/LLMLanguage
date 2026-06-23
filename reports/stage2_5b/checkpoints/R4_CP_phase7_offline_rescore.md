# Checkpoint — Phase 7/8: Offline re-score (user-selected)

- **Goal**: Apply the v3 explicit annotations to R4 deterministically, without a fresh LLM
  rerun and without overwriting R4.
- **Decision**: User selected "Offline re-score R4 bundles" over 96-run pilot / 480-run full
  rerun. Justified by the smoke finding that annotation-independent `local_proxy_success`
  also moves run-to-run ⇒ gpt-oss nondeterminism, so a rerun cannot reproduce R4.
- **Files inspected**: `run_one` evaluation flow; `evidence_graph`, `branch_evaluator`,
  `evaluator` (confirmed all re-derive from raw events + annotation); a stored R4 bundle's
  structure.
- **Files created**:
  - `scripts/stage2_5b/rescore_with_annotations.py` (deterministic re-scorer).
  - `tests/stage2_5b/test_rescore_with_annotations.py` (4 tests).
  - `results/stage2_5b_analysis_r4_1/` (rescored_run_metrics.csv, rescore_diff_summary.csv,
    rescore_status.json).
  - `reports/stage2_5b/R4_1_OFFLINE_RESCORE_REPORT.md`.
- **Files changed**: `R4_REPAIR_EXECUTION_REPORT.md` (Phase 7/8 outcome).
- **Files deleted or archived**: none. Stored R4 bundles untouched.
- **Tests run**: `test_rescore_with_annotations` (4, OK); re-scorer over 480 runs.
- **Test output summary**: 4 tests OK. Re-score: 480 runs; 108 diagnostic changes;
  32 safe_task_success changes, all False→True.
- **Artifacts inspected**: changed-column frequencies; safe-change concentration
  (retail_28, retail_21); endpoints verified reused verbatim.
- **Reviewer decision**: PASS. Annotation effect isolated deterministically; endpoint
  conclusions preserved; R4 not overwritten.
- **Remaining risks**: Full bootstrap contrast re-derivation on rescored metrics not run
  (out of scope for the minimal repair); `rescored_run_metrics.csv` is the ready input if
  desired. A full LLM rerun remains optional (fresh r4_1 roots only).
- **Next allowed step**: Final — confirm full suite green; summarize.
