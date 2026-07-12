# R7-D Mainline Re-entry / G3 Reproducibility Remediation

Date: 2026-07-12  
Scope: read-only forensic audit plus deterministic infrastructure tests. No 18-task pilot, no attack branch, no model generation, no external write.

## Decision

**DO_NOT_PROCEED-R7D**.

The remediation added an evaluation-only ordered trajectory comparator and append-only replay primitives, and all 14 new deterministic tests pass. It does not retroactively make Step 2.1 reproducible: the 63 suffix records have no raw message/tool trajectories, no request/response provenance, no per-call token or latency record, and no replayable DB transition record. G3-A, G3-B, and G3-C therefore remain unclosed.

## Evidence hierarchy and chronology

- R7-C correctness audit: confirmatory IPMA failed; endpoint was a minimal synthetic field-diff rather than the official tau2 evaluator; semantic and human mechanism closure were not auditable.
- R7-D Step 1: R7-C under-tested the intended construct; this did not establish an IPMA effect.
- R7-D Step 2: four-task/two-domain methodology pilot; official endpoint scoring returned `None` for 120/120 and endpoint analysis fell back to a mutation proxy. It cannot support endpoint claims.
- R7-D Step 2.1 machine artifacts: 63/63 suffix summaries were scorable via official tau2 `EvaluationType.ENV`; 9 rewards were 1 and 54 were 0. No raw Step 2.1 trajectory file exists.
- Step 2.2 is preregistration/code only. It has no scientific result and was not run in this remediation.

## Step 2.1 gates: recorded and audited status

| Gate | Stored machine verdict | Forensic verdict | Reason |
|---|---:|---:|---|
| G1 official scorer | PASS | PASS_WITH_PROVENANCE_CAVEAT | `official_scorer.py` calls native `evaluate_simulation(..., ENV)` and fixtures pass in three domains; however 0/63 raw trajectories were retained, so individual scores cannot be independently replayed. The COMMUNICATE fixture proves reachability, not response correctness. |
| G2 family junction | PASS | NOT_CLOSED | For all five stored T2 proofs, `confirmation_asked=true` and `confirmation_not_yet_done=false`, while the gate ignores that field and describes the junction as before confirmation. T1 “remaining evidence” is only `gold_reads - successful_nonmutation_calls`, without target, uniqueness, or gold-membership validation. |
| G3 reproducibility | FAIL | FAIL | Only two active snapshots; 1/2 had tool-count range <=1; maximum range=2. The old gate records ordered-name equality but does not require it. |
| G4 positive control | FAIL | FAIL | 0 eligible cells. The reported T2 metric says “reads before act” but uses total reads; baseline reward only checks non-None and the endpoint comparison takes maxima across replicates. |
| Independent review | REVIEW_NOT_CLOSED | ONE_CODEX_FORENSIC_REVIEW_CLOSED | A new read-only Codex integrity review closed, but it is not cross-model and does not retroactively satisfy the frozen dual-review gate. |

## G3-A — code and environment reproducibility: FAIL

Positive evidence:

- Step 2.1 runner, scorer, analyzer, task registry, and machine summaries are tracked at main-repo HEAD `9b9541f...`.
- Local endpoint identity GETs resolved the configured served IDs and model roots without sending generation requests.
- Config, tokenizer, chat-template/system-prompt, and weight-index hashes are recorded in `results/r7d_ipma/reproducibility/environment_audit_v1.json`.

Blocking evidence:

- The main worktree is not clean and contains pre-existing untracked result/log paths plus this remediation's uncommitted files.
- tau2 source HEAD `ddc66a7...` is dirty: `message.py` and `llm_utils.py` contain runtime argument-normalization changes. Step 2.1 did not bind their hashes to its run.
- No complete dependency lock, CUDA runtime lock, all-shard model digest, tokenizer runtime rendering proof, GPU allocation manifest, or run-bound endpoint process manifest exists.
- Step 2.1 sets `temperature=0` but does not freeze a request seed, top-p, max tokens, timeout, or retry trace; it uses `num_retries=2` without per-attempt provenance.

## G3-B — input and replay reproducibility: FAIL

The stored Step 2.1 evidence has 63 summary rows but zero files in `results/r7d_ipma/step2_1/traces/`. `run_closure.py` creates a trace directory but never writes to it. `closure_suffixes.jsonl` retains tool names only and loses typed arguments, call IDs, tool responses, message ordering, rendered input, pre/post DB hashes, token text/counts, latency, and retry history.

Consequently the original 63 records cannot establish:

- stable rendered-input hashes;
- observation/tool-event-bound junctions;
- final DB replay equality;
- target/argument or mutation-class equality;
- deterministic official-score replay;
- tokenizer recount equality.

The new replay primitive passes a two-pass synthetic no-model test, fails closed when token text is missing, and never modifies its input. This is infrastructure readiness only, not historical-result recovery.

## G3-C — model-run stability: FAIL / not rerun

| Dimension | Step 2.1 evidence |
|---|---|
| exact trace match | Not measurable; raw traces absent |
| ordered tool-name match | 1/2 active snapshots exact; the other is not exact |
| mutating-action match | Not auditable with target/argument detail |
| endpoint success match | Summary rewards exist; no replay proof |
| scorer agreement | No independent two-pass replay |
| tool-count difference | worst active range 2 |
| token difference | not recorded |
| latency difference | not recorded |

No generation preflight was run because G3-A/B were not frozen. Model text does not need to be token-identical for causal interpretation, but fixed recorded traces must replay identically through deterministic extraction, scorer, DB hashing, and token recount. Model behavior variance must be reported separately using the dimensions above.

## Evaluation-only ordered trajectory component

`scripts/r7d_ipma/reproducibility/ordered_trajectory_evaluator.py` detects insertion, deletion, duplicate, reorder, action/target/argument changes, mutation-class changes, first decisive deviation, ordered edit distance, and endpoint-equal/DB-equal corrupt success. It has no import path from the Step 2.1 agent runtime and cannot alter prompts, branch selection, tool execution, or gates.

Two outcome layers are enforced:

1. Endpoint: official task score, final DB hash, and separately recorded unsafe/privacy violations.
2. Process: ordered edit distance, mutating-action divergence, first decisive deviation, tool count, retry/clarification, full-trajectory tokens, and latency.

A process difference is descriptive and never automatically PASR or attack success. The frozen causal contrasts and control requirements must also be satisfied.

## Deterministic test record

Command: `python -m pytest -q tests/r7d_ipma`  
Result: **14 passed**.

Covered faults: insertion, deletion, duplicate, reorder, wrong target, wrong argument, mutation/non-mutation change, malformed call, corrupt success, order/multiplicity preservation, two-pass replay, token-accounting fail-closed, append-only state order, overwrite refusal, and existing-root refusal.

## Minimal preflight status

Only endpoint identity GET was performed; all three configured endpoints were active and returned the expected served IDs. No completion request, agent trajectory, positive-control run, or effect estimate was made.

The authorized informal preflight was not eligible to start because G3-A/B were not frozen. In addition, current assets do not establish Single-Agent/MAS parity, telecom junction coverage, per-model liveness, or positive-control capability. Step 2.2's T1 baseline is also invalid as written: its six no-write tasks have communication/NL reward bases, but `run_exposure.py` scores only `ENV`; unchanged DB can therefore receive a vacuous success without correct reading or communication.

## Causal-design boundary

The future design remains: attack vs matched benign, attack vs neutral, benign vs neutral, and the architecture interaction `Delta_IPMA(MAS) - Delta_IPMA(Single)`, with fixed task/environment/policy/permission, mutation-anchored junctions, per-model liveness, positive controls, three-domain coverage, and k>=5 per final cell. Nothing in this remediation changes branch text, tasks, thresholds, outcomes, or estimands.

The existing data cannot support adaptive-IPMA effectiveness, cross-domain validity, MAS advantage, population safety, or any ICC natural-intent claim.

