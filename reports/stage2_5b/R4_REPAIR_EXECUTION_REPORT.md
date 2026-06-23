# R4 Minimal Repair — Execution Report

Branch `r4-minimal-repair-canonicalization`, safety tag
`pre-r4-minimal-repair-20260622-122324`, from commit `59ec4a9`.
Conda env `agentsearch`. tau2 base `ddc66a7`.

Goal: make R4 a clean, single, reproducible, well-explained canonical experiment — minimal
changes, strict tests, no overwriting of old results, no scope creep, no multi-agent.

## Phase results (each gated, each with a checkpoint in `checkpoints/`)

| Phase | What | Gate |
|---|---|---|
| 0 Freeze | safety tag + repair branch; `R4_REPAIR_INITIAL_STATUS.md`; active/legacy inventory; 79-test baseline | PASS |
| 1 Canonical paths | `src/stage2_5b/canonical_paths.py`; repointed `analyze_confirmatory`, `final_integrity_audit`, `extract_failure_cases`, `equivalence_analysis`, `run_full_blocks`, `run_glmm.R`; README + REPRODUCTION_GUIDE; `test_canonical_paths.py` (11) | PASS |
| 2 Annotations | explicit annotations for all 8 confirmatory tasks; confirmatory `_generic_annotation` hard-fails; `--allow-generic-annotation` gate for exploratory only; `test_confirmatory_annotations.py` (9) | PASS |
| 3 Benchmark provenance | exported `tau2_message_patch.diff` + `PATCH_MANIFEST.json`; run↔benchmark hash linkage; `test_benchmark_provenance.py` (8) | PASS |
| 4 Evaluator semantics | official/local/safe three layers pinned (incl. ALL_IGNORE_BASIS non-redefinition + safe-success guards); `test_reward_metric_semantics.py` extended | PASS |
| 5 Cleanup | dead-code audit + deletion log; fixed stale `src/stage2_5/` doc line; removed stale junk `__pycache__` | PASS |
| 6 Smoke | 24/24 runs on live endpoints; structural gate clean; explicit annotations proven | PASS |

Unit tests: **79 → 115**, all passing
(`conda run -n agentsearch python -m unittest discover -s tests/stage2_5b`).

## Final acceptance criteria (doc Section 16)

1. active defaults → R4 canonical — **done** (test-enforced).
2. confirmatory tasks 100% explicit annotation — **done** (8/8, test-enforced).
3. confirmatory `_generic_annotation` disabled — **done** (hard-fail, test-enforced).
4. tau2 dirty patch externalized — **done** (patch + manifest + tests).
5. official/local/safe metric semantics tested — **done**.
6. README / reproduction guide / reports synced to R4 — **done**.
7. no-legacy-import tests pass — **done** (pre-existing guard still green).
8. dead/stale active code removed/archived — **done** (logged).
9. smoke 24-run passes — **done**.
10. targeted pilot / full-rerun decision — **resolved: offline re-score** (see Phase 7/8).
11. reports correct multi-agent framing — **done** (README, guide, changelog Section 12).

## Phase 7/8 outcome (both paths executed)

**(a) Offline re-score** (deterministic) via `scripts/stage2_5b/rescore_with_annotations.py`
over all 480 frozen R4 bundles (now `results/stage2_5b_rescore_of_r4/`): 108/480 runs change
some diagnostic; **32/480 change `safe_task_success`, all `False → True`** — the generic
annotation over-constrained evidence ordering; v3 annotations remove those false failures.
Endpoints unchanged by construction.

**(b) Full 480-run LLM rerun (R4.1)** — subsequently requested ("static fix not enough"). Run
under the fully repaired pipeline (canonical paths, explicit v3 annotations, externalized
benchmark patch) into fresh `results/stage2_5b_repair/r4_1_confirmatory_canonical/`
(R4 untouched). 16/16 blocks PASS; G11 PASS **480/480 valid, 0 invalid**. Confirmatory analysis
+ equivalence + report figure regenerated into `results/stage2_5b_analysis_r4_1/` and
`figures/stage2_5b_r4_1/`. **No endpoint contrast survives FDR**; R4's one significant signal
(repeated_schedule, p_adj=0.012) does **not** replicate (p_adj=0.625). See
`R4_1_CONFIRMATORY_REPORT_CN.md`, `R4_1_FINAL_INTEGRITY_AUDIT.md`, checkpoint
`R4_CP_phase8_full_rerun.md`.

## Background — why a fresh rerun was not the chosen path

The smoke surfaced a decisive fact: at seed 300, stored-R4 (generic-annotation) endpoints do
not match fresh smoke (explicit-annotation) endpoints — but the divergence includes
`local_proxy_success`, which is **annotation-independent**. So the gap is **LLM server
nondeterminism** (gpt-oss, temp 0, tensor-parallel vLLM), not the repair. Consequences:

- The stored R4 480-run dataset is **not byte-reproducible by rerunning**, independent of this
  repair. A new full run yields a *new sample*, not a reproduction of R4.
- The explicit annotations change only the *trajectory-diagnostic* interpretation
  (evidence / branch / policy-failure / safe-success-from-policy). The clean, deterministic
  way to apply them to R4 is **offline re-scoring of the frozen R4 run bundles** — replaying
  stored trajectories through the v3-annotation evaluators — which requires a small new
  re-scoring script but no GPU and is fully reproducible.
- A fresh full LLM rerun (Section 13.3) is **optional**; if done it must write to fresh
  `r4_1_*` roots and must never overwrite R4.

Recommended: **offline re-score** the frozen R4 bundles under the v3 annotations and publish
as `r4_1` analysis, keeping the stored R4 endpoints untouched. A 96-run pilot / 480-run full
rerun are available but (a) need dedicated GPU time on a shared, contended machine and (b)
only add sampling noise rather than reproducing R4 — so they should be a deliberate,
authorized choice, not an automatic step. No 96/480 job was launched autonomously.
