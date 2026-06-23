# Checkpoint — Phase 1: R4 canonical path closure

- **Goal**: One source of truth for R4 artifact roots; every active script defaults to R4;
  legacy roots reachable only by explicit argument; docs synced; default-path tests added.
- **Files inspected**: analyze_confirmatory.py, final_integrity_audit.py,
  extract_failure_cases.py, equivalence_analysis.py, run_full_blocks.py, run_glmm.R,
  README.md, REPRODUCTION_GUIDE.md; grep of active code for legacy roots.
- **Files created**:
  - `src/stage2_5b/canonical_paths.py` (R4 roots + legacy-root constants).
  - `tests/stage2_5b/test_canonical_paths.py` (11 tests).
- **Files changed**:
  - 5 scripts: import canonical constants, extracted `build_parser()`, repointed every
    default to R4 roots (results→`r4_confirmatory_canonical`, analysis→`stage2_5b_analysis_r4`,
    figures→`stage2_5b_r4`, integrity→`r4_final_integrity_report.csv`,
    report→`R4_FINAL_INTEGRITY_AUDIT.md`).
  - `run_glmm.R`: default input/output to `results/stage2_5b_analysis_r4/`.
  - `README.md`, `REPRODUCTION_GUIDE.md`: canonical roots, scope note (multi-agent out of
    scope), benchmark-patch pointer, corrected test-count note.
- **Files deleted or archived**: none.
- **Tests run**: `python -m unittest tests.stage2_5b.test_canonical_paths`; `py_compile`
  of all 5 changed scripts + canonical_paths.py.
- **Test output summary**: Ran 11 tests — OK. Compile OK.
- **Artifacts inspected**: none written (no experiment run).
- **Reviewer decision**: PASS (Gate 1). All active defaults point to R4; no legacy root is a
  default anywhere; docs and code agree.
- **Remaining risks**: `run_full_blocks` default output-root is the canonical R4 root; a
  naive no-arg re-run is resume-safe (existing run_ids skipped) but a *full rerun* must use a
  fresh `r4_1_*` root per Section 13.3 — documented, enforced by operator discipline.
- **Next allowed step**: Phase 2 — disable confirmatory `_generic_annotation` fallback and
  author explicit annotations for all 8 confirmatory tasks.
