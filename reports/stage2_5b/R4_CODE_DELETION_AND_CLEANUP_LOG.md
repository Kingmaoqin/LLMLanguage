# R4 Code Deletion and Cleanup Log

Per Section 4.3, every deletion records: deleted_file, reason, replacement_file,
tests_passed_after_deletion, restore_method.

## Deletions

### 1. `__pycache__/` (repo root)

```text
deleted_file:   __pycache__/analyze_stage2.cpython-312.pyc
                __pycache__/run_stage2_experiment.cpython-312.pyc
reason:         Stale compiled bytecode of legacy scripts (analyze_stage2.py,
                run_stage2_experiment.py) that were archived to legacy/ in commit b94890a.
                The source no longer exists at repo root. The directory is git-ignored
                (.gitignore lines 16-17), so nothing tracked was removed.
replacement_file: none (regenerable bytecode; active code is under src/, scripts/)
tests_passed_after_deletion: yes — full tests/stage2_5b suite, 115 tests OK
restore_method: regenerated automatically by Python on next import/compile; or
                `python -m py_compile legacy/stage2/scripts/analyze_stage2.py`
```

## Edits (not deletions) that removed stale references

- 5 active scripts + `run_glmm.R`: stale round-3 default roots → R4 canonical (Phase 1).
- `README.md`: removed non-existent `src/stage2_5/` layout line; updated analysis/figure
  roots and the stale 480-run output paths to `_r4`.
- `reports/stage2_5b/REPRODUCTION_GUIDE.md`: round-3 root → R4 canonical; stale test count
  (46) → current; added benchmark-patch provenance pointer and scope note.

## Explicitly NOT deleted (preserved)

`legacy/` tree, all raw experiment outputs, run manifests, result metrics, old reports,
benchmark snapshots, proposal history, the exported patch file, and reproduction logs.
The legacy round-3 result roots remain on disk, reachable only via explicit arguments.

## No duplicate implementations created or found

No `_new.py` / `_fixed.py` / `_v2.py` / `_v3.py` / `_final.py` exist in the active path.
The `test_no_legacy_imports.py` guard keeps the active runtime free of legacy imports.
