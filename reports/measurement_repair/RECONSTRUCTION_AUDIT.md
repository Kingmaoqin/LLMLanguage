# Trace Reconstruction Audit (round-5 §5)

Source result root: `results/stage2_5b_repair/r4_1_confirmatory_canonical`
Traces written to: `results/stage2_5b_repair/r4_1_confirmatory_canonical/traces/<run_id>.trace.json`
Total runs reconstructed: **480**

## Completeness classification

| class | n | meaning |
|---|---|---|
| complete | 480 | all analysis dimensions present (state at hash level) |
| partial | 0 | usable but missing >=1 dimension (see notes) |
| insufficient | 0 | cannot support trajectory analysis |

## Token-source provenance

| token_source | n |
|---|---|
| prompt_plus_completion | 480 |

## Notes frequency

- state divergence is hash-level (no full DB object diff): 480

## Schema validation

- schema failures: 0

## Recoverable vs not recoverable

- Recoverable from existing bundles: endpoint outcomes, full tool-call sequence incl. arguments, state mutations (args + before/after hashes), policy/evidence/branch flags, conversation incl. tool_calls, controlled-user events, input/output tokens (=> total via prompt_plus_completion).
- NOT recoverable offline: full DB object-level state diffs (only state hashes were persisted) and per-message token usage (only aggregate input/output).

## Rerun decision (round-5 §9)

A measurement rerun is **not required** to build the interactional-robustness profile: every analysis dimension is reconstructable at the level the profile needs, and the token total is recovered as `prompt_plus_completion`. A rerun is only needed if full DB object-level state diffs or per-message token usage become a hard requirement; the measurement-complete runner exists for that and has been smoke-tested.
