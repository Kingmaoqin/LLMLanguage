# R4 Benchmark Provenance Report

## Decision: externalize the dirty patch (Section 8.2, Option A)

The tau2-bench working tree carries exactly one local modification used by the R4 runs:
`src/tau2/data_model/message.py` (+12 lines). The change is parsing-only, so a clean
refreeze (Option B) would have required either re-running with broken tool-call
deserialization or re-modifying the file anyway. We therefore externalize the patch and
record full provenance (Option A).

## Frozen identifiers

| Field | Value |
|---|---|
| tau2 base commit | `ddc66a777e520373975f15d3abec989cfe2ec371` |
| tau2 origin/main | `ddc66a777e520373975f15d3abec989cfe2ec371` (identical) |
| describe | `voice-user-sim-v1.0-90-gddc66a7` |
| patched file | `src/tau2/data_model/message.py` |
| patch file | `artifacts/stage2_5b/benchmark_patches/tau2_message_patch.diff` |
| patch sha256 | `17d1aa0ea05969a589275ffe0686c46b2581aa66c983dee85add7ffd9f263660` |
| patched-file sha256 | `a67aeead9798e9c23600dee69effde43e31fcf26b1643a307fcec4a73a6a2b99` |
| base-file sha256 | `378cc451ded5b4314c4fe177bf83e72abb2e0bba53b79c2a0e27c53f3cbd15b0` |
| snapshot manifest | `artifacts/stage2_5b/tau_snapshot_manifest.json` |
| snapshot manifest sha256 | `f4626d9b1a52829b002cc2562f4db4ea0afe649dc196daa4dd21442dfb1c7d95` |

## Run linkage

Every R4 run records `runtime_hashes.benchmark_manifest_hash` in its `run_contract.json`
and in `FULL_RUN_CONTRACT.json`. That value equals the snapshot-manifest sha256
(`f4626d9b…`), so the 480 runs are cryptographically tied to this exact benchmark state
including the patch. `tests/stage2_5b/test_benchmark_provenance.py` asserts this linkage.

## Effect scope

The patch adds a pydantic `field_validator("arguments", mode="before")` on `ToolCall` that
coerces a stringified JSON / Python-literal tool-call argument payload into a dict before
validation (some local served models emit arguments as a string). It is deserialization-only:
the snapshot manifest confirms `evaluator_changed_vs_comparison_ref = false`. It does not
change the evaluator, reward computation, DB checks, task definitions, or policies.

## Reapply / reproduce

```bash
cd /home/xqin5/tau2-bench
git checkout ddc66a777e520373975f15d3abec989cfe2ec371
git apply /home/xqin5/llmlanguage/ir_mstu_stage2/artifacts/stage2_5b/benchmark_patches/tau2_message_patch.diff
sha256sum src/tau2/data_model/message.py   # expect a67aeead…
```

The report no longer relies on the word "dirty": the patch and its hash are now first-class,
re-applicable artifacts.
