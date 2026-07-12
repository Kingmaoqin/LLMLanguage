# R7-D GO / NO-GO

Date: 2026-07-12

## Verdict

**DO_NOT_PROCEED-R7D**

The 18-task preregistration draft is not authorized because the required conjunction is false:

| Required gate | Status |
|---|---|
| G1 official scorer | PASS_WITH_PROVENANCE_CAVEAT |
| G2 mutation-anchored junction | NOT_CLOSED |
| G3-A environment/code lock | FAIL |
| G3-B deterministic input/replay | FAIL for historical Step 2.1; synthetic infrastructure test PASS |
| G3-C model stability | FAIL / not eligible to rerun |
| per-model liveness | FAIL / not closed |
| positive-control capability | FAIL (Step 2.1: 0 eligible) |
| Single-Agent/MAS parity | NOT_IMPLEMENTED |
| retail/airline/telecom coverage | FAIL (no valid telecom suffix) |
| ordered trajectory evaluator | PASS, evaluation-only, 14/14 tests |
| fresh reset and replay | synthetic PASS; real recorded trace NOT_AUDITABLE |
| full-trajectory token accounting | FAIL / absent |
| no history-driven selection | Step 2.1 selection states blind; end-to-end proof incomplete |

## Finite remaining fixes

1. Freeze a clean, versioned runtime: commit or explicitly vendor/hash the two tau2 normalization patches; generate a complete dependency/CUDA/GPU/start-command lock; hash every model shard plus tokenizer and rendered chat template; freeze seed, top-p, max tokens, timeout, and zero/fully logged retry behavior.
2. Add exclusive-create run roots and per-call append-only raw records containing rendered input hash, complete ordered messages/tool calls with typed arguments and IDs, tool responses, pre/post DB hashes, official score components, retry attempts, raw token texts/counts, and latency. Then demonstrate two independent deterministic replays on recorded fixtures.
3. Correct the gate logic prospectively: T2 must require a real unconsumed confirmation/mutation boundary; T1 evidence must be target-aware, unique, and task-required; G3 must require ordered sequence agreement; G4 must use the frozen pre-mutation metric and paired reward comparison. Add a deterministic no-write/communication evaluator so ENV-only DB equality cannot certify T1 competence.
4. Freeze a minimal, result-blind Single-Agent/MAS preflight manifest with retail, airline, and telecom fixtures. Only then run the authorized small preflight to close endpoint scoring, valid junctions, per-model liveness, model-sensitive positive control, parity, fresh reset, replay, and complete token accounting.
5. Run the required isolated integrity reviews on the frozen preflight artifacts and record disagreements as Unknown. Do not use reviewer labels as primary outcomes.

No ICC restart, new research pivot, 18-task pilot, attack rollout, or outcome/threshold change is permitted by this result.

