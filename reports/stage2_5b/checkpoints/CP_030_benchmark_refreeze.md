# Checkpoint CP-030

## Goal

Re-freeze the exact tau2 benchmark source/data state used by the fourth-round branch.

## Existing Implementation

A 67-file benchmark snapshot already existed from 2026-06-16. The tau2 HEAD and dirty parser
patch remained unchanged, but the active Python environment had changed.

## Problem Evidence

The new experiment branch requires a fresh provenance timestamp and environment record before
new calibration or smoke execution.

## Minimal Change Plan

Rerun the existing canonical freeze script against `/home/xqin5/tau2-bench`, inspect the
manifest/report diff, and verify every snapshot checksum.

## Files Changed

- `artifacts/stage2_5b/tau_snapshot_manifest.json`
- `reports/stage2_5b/BENCHMARK_VERSION_FREEZE.md`
- `reports/stage2_5b/BENCHMARK_TASK_DIFF_AUDIT.md`

## Git Diff Summary

Only generated timestamp, current Python version, and command log timestamps changed. tau2
HEAD, dirty diff, task definitions, evaluator files, and all 67 snapshot file hashes remained
stable.

## Tests

```text
conda run -n agentsearch python scripts/stage2_5b/freeze_benchmark.py \
  --tau-root /home/xqin5/tau2-bench

cd artifacts/stage2_5b/benchmark_snapshot
sha256sum -c SHA256SUMS
```

## Results

- Snapshot files: 67
- tau2 HEAD: `ddc66a777e520373975f15d3abec989cfe2ec371`
- Dirty benchmark files: `src/tau2/data_model/message.py` only
- Snapshot checksums: 67/67 PASS
- Manifest JSON parse: PASS

## Artifact Inspection

Confirmed the frozen dirty diff is the pre-existing tool-call argument parser patch and that no
benchmark task/policy/tool/evaluator content changed during this checkpoint.

## Dead-Code Check

No runtime code changed.

## Reviewer Findings

An initial checksum command was run from the project root and therefore could not resolve
snapshot-relative paths. Re-running from the snapshot directory verified all files.

## Gate

PASS.

## Rework

Corrected checksum working directory and reran the complete checksum list.
