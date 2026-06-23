# Checkpoint — Phase 3: Benchmark provenance closure

- **Goal**: Replace the "benchmark is dirty" prose with a first-class, re-applicable patch
  artifact + manifest, and tie the runs to a frozen benchmark hash.
- **Files inspected**: tau2 repo git state + `git diff` of message.py;
  `tau_snapshot_manifest.json` (per-file hashes, dirty flags, evaluator flag);
  `FULL_RUN_CONTRACT.json` runtime_hashes; `freeze_benchmark.py` hash fields;
  benchmark_snapshot `SHA256SUMS`.
- **Files created**:
  - `artifacts/stage2_5b/benchmark_patches/tau2_message_patch.diff` (849 bytes).
  - `artifacts/stage2_5b/benchmark_patches/PATCH_MANIFEST.json` (base commit, patch hash,
    patched/base file hashes, snapshot-manifest hash, reason, effect scope, reapply cmd).
  - `tests/stage2_5b/test_benchmark_provenance.py` (8 tests).
  - `reports/stage2_5b/R4_BENCHMARK_PROVENANCE_REPORT.md`.
- **Files changed**: none (benchmark/tau2 sources untouched; only new provenance artifacts).
- **Files deleted or archived**: none.
- **Tests run**: `test_benchmark_provenance` (8, OK).
- **Test output summary**: Ran 8 tests — OK.
- **Artifacts inspected**: verified live patched `message.py` sha256 == snapshot entry
  `a67aeead…`; snapshot-manifest sha256 `f4626d9b…` == run-contract benchmark_manifest_hash.
- **Reviewer decision**: PASS (Gate 3). Patch + clean base commit are re-checkable; run
  manifest agrees with benchmark manifest; provenance reproducible.
- **Remaining risks**: Patch is an uncommitted working-tree change in the external tau2 repo;
  the .diff + reapply command in PATCH_MANIFEST.json mitigate loss. The patch is
  parsing-only (evaluator unchanged), so it does not, by itself, force a full rerun.
- **Next allowed step**: Phase 4 — evaluator three-layer semantics tests.
