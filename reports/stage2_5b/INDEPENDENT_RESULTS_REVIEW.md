# INDEPENDENT_RESULTS_REVIEW (Stage-2.5b, Phase 14)

Reviewer: separate Claude session (independent of the Codex session driving the experiment).
Role assignment: user-directed ("Codex drives, I review"). This reviewer launches **no GPU
jobs** and only reads artifacts.

Status: **PART 1 (foundation) complete; PART 2 (results) pending the full confirmatory run +
analysis.**

---

## PART 1 — Foundation integrity (G0–G9): PASS

All checks below were run directly against artifacts/logs, not summary reports.

### 1.1 Full-phase task resolution bug (reviewer-caught, fixed)
`_phase_tasks(..., "full")` returned a list of dicts; `_build_matrix` / `task_map[...]` require
task_id strings — the full run would have crashed. Fixed to
`[t["task_id"] for t in payload["confirmatory_tasks"]]`. Verified: full phase resolves to the 8
frozen task_id strings, all present in the candidate task_map. **PASS.**

### 1.2 No treatment leakage into task selection
The two calibration directories used for the freeze (`calibration_retail8_gemma`,
`calibration_retail8_gpt_oss`) contain **only `neutral_single`**. Task difficulty — and hence
selection — was estimated without any treatment condition. **PASS** (no outcome leakage).

### 1.3 Seed disjointness
Calibration seeds = {100…109}; confirmatory seeds = {300…304}; **disjoint = True**. **PASS.**

### 1.4 Frozen task set
`data/stage2_5b/calibrated_tasks_frozen.yaml` SHA256 matches the stored
`.sha256` (`a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc`). The concurrent
(driving) session uses the **same hash** — both sessions are aligned on one task set. 8 retail
tasks, mean neutral success 0.15–0.85. **PASS.**

### 1.5 Controlled-user invariance + leakage
Re-ran `validate_controlled_user.py`: **261 fixture groups**, 261/261 agreement on clean
response / factual slots / confirmation decision / response decision / object IDs; **gold
tool-name leakage = 0; hidden/style/process leakage = 0** (now covering the expanded retail
candidate set, up from 149). **PASS.**

### 1.6 Smoke (G8)
Two independent smokes agree: this reviewer's `smoke_g6_*` (24 runs, 0 invalid, all 6
conditions) and the driver's `smoke_retail8_confirmatory` (24 runs). Terminations are
USER_STOP / MAX_STEPS (MAX_STEPS expected on harder mid-band tasks). **PASS.**

### 1.7 Pilot (G9)
`pilot_retail8_confirmatory`: **96/96 cells** (4 tasks × 6 conditions × 2 seeds × 2 models),
**0 invalid, 0 duplicate run_ids**, balanced 48 gemma + 48 gpt-oss, all 6 conditions, seeds
{300,301}. **PASS.**

### 1.8 Scope limitations (acknowledged, not defects)
- **Retail-only domain** — airline is genuine floor for both models (CP-013 diagnosis).
- **Official reward basis not fully local** — all retail candidates are `DB|NL_ASSERTION`;
  primary endpoints are DB-based (`final_state_correct`, `safe_task_success`,
  `local_proxy_success`); `official_reward_basis_success` is reported MISSING. This is the
  Step 4.3 fallback and must be stated in the final claims.
- **3 of 8 tasks degenerate on one model** (retail_64 gemma-floor, retail_23 gemma-ceiling,
  retail_28 gpt-oss-floor); per-model contrasts on those tasks have limited sensitivity and
  must be flagged in the pre-analysis plan and any per-model claim.

**Foundation verdict: PASS.** The confirmatory run rests on a clean, leakage-free, hashed
foundation with a deterministic controlled user and disjoint calibration/confirmatory seeds.

---

## PART 2 — Results review: PASS WITH CLAIM RESTRICTIONS

Review mode limitation: a new independent sub-agent was not available for Phase 14. This
section is a separate evidence-only pass over raw manifests, bundles, terminal/process logs,
analysis inputs, source tables, figures, and failure cases. It is not represented as a fully
independent reviewer session.

### 2.1 Full matrix and denominator: PASS

- Formal root:
  `results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic`.
- Expected/manifest/metric/bundle rows: 480/480/480/480.
- Unique run IDs: 480; duplicate IDs: 0.
- Valid behavioral runs: 479.
- One context-window infrastructure failure is retained:
  `gemma4_31b__retail_41__insult_single__seed302__tpl2__temp0.0`.
- All 480 runs have termination records. Parser and final-environment records cover exactly
  the 479 valid runs.
- All 16 model/task block reports are PASS.

### 2.2 Provenance and invariance: PASS

- Runtime hashes are single-valued and match `FULL_RUN_CONTRACT.json`.
- Block deployment IDs match the frozen scheduler assignment.
- Initial-state drift groups: 0 across 80 model/task/seed groups.
- Controlled-user opening drift groups: 0.
- Controlled-user turn-0 coverage: all 479 valid runs, with condition coverage matching each
  group's valid manifest rows.
- No mixed formal roots, post-hoc task deletions, or treatment-driven task selection were
  found.

### 2.3 Pairing and bootstrap: PASS

- Pairing key:
  `model_alias, task_id, seed, template_block`.
- Single-turn conditions pair only to `neutral_single`.
- `abuse_repeated` pairs only to `neutral_repeated`.
- `neutral_repeated - neutral_single` is labeled exposure, not valence.
- Matched-pair table contains 400 planned contrast rows before outcome-specific missingness.
- Primary CIs use 10,000 task-cluster bootstrap replicates. `task_id`, not individual runs,
  is the resampling unit; all model/seed rows for a sampled task remain together.
- Pooled and per-model tables preserve raw and BH-FDR-adjusted p-values.

### 2.4 Equivalence and invalid-run rules: PASS

- Endpoint margins are ±0.10; policy/premature margins are ±0.05; required-fact coverage is
  ±0.10.
- Equivalence is declared only when the full percentile CI lies inside the margin.
- No pooled endpoint cell passes equivalence.
- The invalid-rate difference for insult vs neutral is 1.25pp, below the frozen 5pp flag.
- MAX_STEPS is retained as behavior in `safe_task_success`, not reclassified as invalid.
- `final_state_correct` and `local_proxy_success` remain missing for 37 valid MAX_STEPS runs;
  complete-pair counts are explicitly lower and are not presented as full-denominator rates.

### 2.5 Endpoint claims: RESTRICTED

Across 15 pooled endpoint cells:

- FDR-significant cells: 0.
- Equivalent-within-margin cells: 0.

The correct claim is:

> no reliable endpoint effect detected; endpoint robustness was not established.

The data do not support “no effect,” global robustness, or a replicated repeated-abuse
completion benefit.

### 2.6 Process claims: LIMITED SUPPORT

Two pooled process cells survive BH-FDR:

1. `praise_affect_single - neutral_single` increases agent tool calls by 0.525,
   95% CI [0.250, 0.800], adjusted p=0.0172.
2. `abuse_repeated - neutral_repeated` decreases normalized critical-argument distance to the
   frozen reference by 0.0363, 95% CI [-0.0542, -0.0182], adjusted p=0.0172.

Neither is accompanied by a multiplicity-corrected endpoint, policy-failure, or premature-
action effect. Reference-distance changes are diagnostic and do not imply correctness.

An exploratory gpt-oss cell shows praise-trust direct tool-sequence divergence below the
matched repeated-exposure noise floor. It does not support greater praise-induced drift.

### 2.7 Metric-semantics correction: PASS AFTER REPAIR

The first analysis pass incorrectly mapped `user_abandonment_markers` to agent task
abandonment. Raw inspection showed that this field is user-side and mostly captures the
controlled user's normal `###STOP###`. The final analysis:

- does not use it as agent abandonment;
- retains `agent_task_abandonment` as missing/not identifiable;
- reports no validated abandonment case;
- records the limitation in `analysis_status.json` and the final report.

Policy failure, premature action, invalid run, and trajectory distance retain their documented
semantics.

### 2.8 Task/model heterogeneity: CLAIM RESTRICTION

Per-model endpoint directions differ in several cells and task-level deltas include positive,
negative, and zero values under every contrast. Three tasks were already flagged as
single-model degenerate during calibration. No secondary GLMM interaction was fit because
`Rscript/lme4` is unavailable.

Any claim must therefore be retail-only, two-model, and task-dependent. No global model
ranking or cross-domain conclusion is supported.

### 2.9 Failure cases and figures: PASS

- Failure cases are mechanically selected from the frozen matched-pair table.
- Each case records matched run IDs, same model/task/seed/template block, tool traces, state
  hashes, evaluator deltas, and the repeated-exposure trajectory noise floor.
- The report contains endpoint-change, trajectory-only, policy, premature-action, missed-
  branch, praise/insult, repeated-abuse, opposite-direction, and null cases.
- Agent abandonment is explicitly reported as not identifiable.
- Figure source values match `summary_by_model_condition.csv` and
  `paired_contrasts_task_cluster_bootstrap.csv`.

## Final reviewer verdict

**PASS WITH CLAIM RESTRICTIONS.**

The experiment and primary statistics are reproducible and internally auditable. The final
claim must remain:

> No multiplicity-corrected endpoint effect was detected, endpoint equivalence was not
> established, and only selective process-level differences were observed under substantial
> task/model heterogeneity.
