# Checkpoint — Phase 6: Smoke test

- **Goal**: Validate the repaired pipeline end-to-end on live endpoints (canonical paths,
  explicit annotations, evaluator semantics) — not to chase significance.
- **Files inspected**: `models.yaml` (endpoints), live `/v1/models` probes, smoke metrics /
  manifests / bundles, stored R4 seed-300 metrics for retail_41/retail_6.
- **Files changed**: none (code unchanged; smoke is a run).
- **Files created**: `results/stage2_5b_repair/smoke_r4_canonical/` (24 runs + bundles),
  `reports/stage2_5b/R4_SMOKE_TEST_REPORT.md`. (Throwaway `smoke_r4_sanity/` was created then
  deleted.)
- **Files deleted or archived**: `smoke_r4_sanity/` scratch dir (this-session only).
- **Tests run**: structural smoke gate (custom script).
- **Test output summary**: 24/24 metrics, manifests, bundles; 0 dup run_ids; 0 missing cells;
  0 invalid runs; all 6 conditions × 2 models × 2 tasks present. Ran without
  `--allow-generic-annotation` ⇒ explicit annotations proven in use.
- **Artifacts inspected**: per-run safe/local_proxy lines; R4-vs-smoke diff at seed 300.
- **Reviewer decision**: PASS (smoke gate). Pipeline healthy under repaired code.
- **Remaining risks / finding**: endpoint values at seed 300 do not match stored R4 because
  the annotation-independent `local_proxy_success` also moved ⇒ the gap is LLM server
  nondeterminism, not the repair. Stored R4 is not byte-reproducible by rerun regardless.
- **Next allowed step**: Phase 7/8 decision (pilot / full rerun / offline re-score) — a
  resource + scientific tradeoff that needs the user's call before any 96- or 480-run job.
