# Checkpoint — Phase 5: Dead-code / stale-default cleanup

- **Goal**: Remove stale defaults and junk from the active path without touching raw
  results, legacy archive, or provenance.
- **Files inspected**: Section 10.1 greps over `src/stage2_5b`, `scripts/stage2_5b`,
  `tests/stage2_5b`; `src/` layout; `.gitignore`; root `__pycache__`.
- **Files changed**: `README.md` (removed non-existent `src/stage2_5/` layout line, added
  `src/adapters/`).
- **Files deleted or archived**: root `__pycache__/` (2 stale legacy `.pyc`, git-ignored,
  regenerable) — see `R4_CODE_DELETION_AND_CLEANUP_LOG.md`.
- **Files created**: `R4_DEAD_CODE_AND_STALE_DEFAULTS_AUDIT.md`,
  `R4_CODE_DELETION_AND_CLEANUP_LOG.md`.
- **Tests run**: full `tests/stage2_5b` discover; `py_compile` of all active modules; Gate 5
  greps.
- **Test output summary**: Ran 115 tests — OK. Compile OK. Gate 5 greps return no
  legacy-root default in active code (only the explicit `canonical_paths` constant).
- **Artifacts inspected**: confirmed `src/stage2_5` (non-b) absent; no `_new/_fixed/_v2`
  files; no active legacy imports.
- **Reviewer decision**: PASS (Gate 5). Active path free of stale defaults and legacy
  imports; nothing in the preserve-list was touched.
- **Remaining risks**: none in active code. Smoke/pilot/full-rerun require live model servers.
- **Next allowed step**: Phase 6 — smoke test (requires gemma + gpt-oss vLLM endpoints).
