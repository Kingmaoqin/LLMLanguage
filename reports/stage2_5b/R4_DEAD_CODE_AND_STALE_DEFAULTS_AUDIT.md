# R4 Dead-Code and Stale-Defaults Audit

Static scans from Section 10.1, restricted to the active path
(`src/stage2_5b`, `scripts/stage2_5b`, `tests/stage2_5b`) plus top-level docs.

## Scan results

| Scan | Active-path hits | Verdict |
|---|---|---|
| `stage2_5.controlled_user_simulator` | only in `test_no_legacy_imports.py` (guard) | OK — guard asserts it is NOT imported |
| `run_stage2_5_experiment` / `run_stage2_experiment` | only in `test_no_legacy_imports.py` (guard) | OK — guard |
| `full_blocks_retail8_confirmatory_v2_atomic` | only in `canonical_paths.py` `LEGACY_RESULTS_ROOTS` + docstring | OK — explicit-only constant |
| `results/stage2_5b_analysis` (non-`_r4`) as a default | none after Phase 1 | FIXED in Phase 1 |
| `*_new.py` / `*_fixed.py` / `*_v2.py` / `*_v3.py` / `*_final.py` | none | OK — no duplicate implementations |
| `from legacy` / `import legacy` / `src.stage2_5.` (non-b) in active code | none | OK — no legacy imports |

The `tests/stage2_5b/test_no_legacy_imports.py` guard already fails the build if any active
module imports a legacy module, so this property is regression-protected.

## Stale items found and handled

1. **Stale script defaults** (round-3 roots in 5 scripts + run_glmm.R): repointed to R4
   canonical in Phase 1.
2. **Stale README layout line** `src/stage2_5/   evaluator and trajectory components`:
   that directory no longer exists in `src/` (it was archived to `legacy/stage2_5/`). The
   active evaluator lives in `src/stage2_5b/`. README layout corrected to list
   `src/stage2_5b/` and `src/adapters/`.
3. **Stale doc test count** (46): corrected in REPRODUCTION_GUIDE during Phase 1 / final.
4. **Stale untracked root `__pycache__/`**: contained `analyze_stage2.cpython-312.pyc` and
   `run_stage2_experiment.cpython-312.pyc` — compiled bytecode of legacy scripts that used
   to sit at repo root before archival. Git-ignored (not tracked). Deleted (regenerable).

## Not deleted (preserved per Section 4.3)

Raw experiment outputs, run manifests, result metrics, old reports, benchmark snapshots,
proposal history, patch files, reproduction logs, and the entire `legacy/` tree are retained
for audit. The legacy round-3 result roots remain on disk and are reachable only via explicit
`--root`/`--output-root` arguments.
