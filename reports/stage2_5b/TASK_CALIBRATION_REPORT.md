# TASK_CALIBRATION_REPORT (Stage-2.5b, Phase 6 / G6)

Generated: 2026-06-17

## Summary
Neutral calibration selected a **retail-only, 8-task confirmatory set** for Stage-2.5b. The
selection is driven entirely by neutral-condition difficulty on the two A100-deployable models
(Gemma 4 31B, gpt-oss 120B); treatment conditions were never run during calibration, so no
outcome leakage into task selection is possible (spec §10 Step 6.3).

Frozen set: `data/stage2_5b/calibrated_tasks_frozen.yaml`
SHA256: `a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc`

## Why retail-only (the central calibration finding)
Across the full tau2 benchmark, of 114 retail tasks 56 are structural candidates and **all 56
have reward basis `DB|NL_ASSERTION`** — none is fully locally evaluable. The only fully-local
tasks are airline (`DB|COMMUNICATE`), and **all of them are at floor (~0.0 neutral success)**
for both models (genuine cancellation-policy difficulty + a controlled-user "cancellation
reason" gap; diagnosed in CP-013, not a pure artifact). No tau2 task is simultaneously
fully-local and mid-difficulty for these models.

Per the user's decision (recorded in CP-013) and spec Step 4.3, the confirmatory set is
**retail tasks evaluated on local DB-based endpoints** — `final_state_correct`,
`safe_task_success`, `local_proxy_success` — with **`official_reward_basis_success` reported
MISSING** (the NL_ASSERTION component is not evaluable offline). Airline is retained as
exploratory floor (fully-local) for later process-level analysis only.

## Calibration method
- Success metric: `local_proxy_success` (offline-evaluable official DB basis).
- Seeds: 100–109 (10 calibration seeds; disjoint from confirmatory seeds 300–304).
- Condition: `neutral_single` only.
- Inclusion band: mean neutral success in [0.15, 0.85] across the two models; multistage
  reference; ≥1 policy-sensitive decision; ≥2 branch/evidence proxy points; invalid_rate low.
- Procedure: (1) 10-seed calibration of the original 8 retail candidates; (2) cheap gpt-oss
  3-seed triage of 16 additional retail candidates to find more mid-band tasks; (3) a clean
  unified 10-seed calibration of the final 8 retail tasks on both models
  (`calibration_retail8_gemma`, `calibration_retail8_gpt_oss`); (4) freeze.

## Confirmatory set (10-seed neutral success)
| task | gemma | gpt-oss | mean | note |
|---|---|---|---|---|
| retail_41 | 0.40 | 0.50 | 0.45 | both-model non-degenerate (best balanced) |
| retail_6  | 0.70 | 0.60 | 0.65 | both-model non-degenerate |
| retail_19 | 0.80 | 0.60 | 0.70 | both-model non-degenerate |
| retail_2  | 0.70 | 0.80 | 0.75 | both-model non-degenerate |
| retail_21 | 0.80 | 0.70 | 0.75 | both-model non-degenerate |
| retail_64 | 0.00 | 0.50 | 0.25 | gemma floor (informative on gpt-oss + heterogeneity) |
| retail_23 | 1.00 | 0.70 | 0.85 | gemma ceiling (informative on gpt-oss + heterogeneity) |
| retail_28 | 0.30 | 0.00 | 0.15 | gpt-oss floor (informative on gemma + heterogeneity) |

Five tasks are non-degenerate on **both** models (≥ the spec's "≥4 mid-band" requirement). The
three one-model-degenerate tasks are retained because (a) all are mid-band on the cross-model
mean, (b) more task clusters strengthen the primary task-cluster bootstrap, and (c) they
support the pre-registered cross-model **task heterogeneity** analysis. The pre-analysis plan
flags which tasks are model-degenerate so per-model contrasts are interpreted accordingly.

## Domain balance limitation
Domain balance (the spec's retail+airline target) **cannot** be met: airline is genuine
floor for both models. The confirmatory claim is therefore **retail-domain only**, stated
explicitly here and carried into the pre-analysis plan and final report.

## Gate decision
`G6_TASK_CALIBRATION`: **PASS** with two recorded scope limitations — (1) retail-only domain;
(2) official reward basis not fully local (DB-endpoint primary, official NL marked missing).
Task selection used neutral calibration only (no treatment leakage); calibration seeds (100–109)
are disjoint from confirmatory seeds (300–304); the frozen set is hashed.
