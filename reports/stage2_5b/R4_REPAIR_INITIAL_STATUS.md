# R4 Minimal Repair — Initial Status (Phase 0 Freeze)

Generated at the start of the fourth-round minimal/canonicalization repair, before any
code or experiment was touched. This is the frozen baseline the repair is measured against.

## Git state

- Repo root: `/home/xqin5/llmlanguage/ir_mstu_stage2`
- Current commit: `59ec4a9cd7429065b25d50696feaa830c745c3b1`
  ("Stage-2.5b round-4: confirmatory run, analysis, and reports")
- Branch at freeze time: `stage2-5b-scripted-user-cleanup`
- Safety tag created: `pre-r4-minimal-repair-20260622-122324`
- Repair branch created: `r4-minimal-repair-canonicalization`
- Uncommitted changes in this repo at freeze: none (clean working tree)

## Existing results roots (NOT modified by this repair)

```text
results/stage2_5_audit
results/stage2_5b_analysis            # legacy/pre-R4 analysis outputs
results/stage2_5b_analysis_r4         # R4 analysis outputs (canonical)
results/stage2_5b_audit
results/stage2_5b_repair              # contains both legacy and R4 confirmatory roots
results/stage2_5b_validation
results/stage2_5_repair
results/stage2_dryrun, stage2_dryrun2, stage2_gate_check, stage2_mini, stage2_smoke
```

Key roots inside `results/stage2_5b_repair/`:

- `full_blocks_retail8_confirmatory_v2_atomic/` — the OLD confirmatory root that active
  scripts currently default to (the problem this repair fixes).
- `r4_confirmatory_canonical/` — the R4 canonical confirmatory root. 16 run directories
  (2 models × 8 retail tasks) plus `FULL_RUN_CONTRACT.json`.

R4 analysis already materialized in `results/stage2_5b_analysis_r4/`:
`confirmatory_run_metrics.csv`, `matched_pairs.csv`,
`paired_contrasts_task_cluster_bootstrap.csv`, `equivalence_results.csv`,
`per_task_diagnostics.csv`, `summary_by_model_condition.csv`,
`leave_one_task_out_sensitivity.csv`, `analysis_status.json`.

R4 figures in `figures/stage2_5b_r4/`.
R4 integrity report: `results/stage2_5b_repair/r4_final_integrity_report.csv`.

## Canonical roots this repair will pin (per Section 4.1 / 6.1)

```text
R4_RESULTS_ROOT   = results/stage2_5b_repair/r4_confirmatory_canonical
R4_ANALYSIS_ROOT  = results/stage2_5b_analysis_r4
R4_FIGURES_ROOT   = figures/stage2_5b_r4
R4_REPORTS_ROOT   = reports/stage2_5b
R4_INTEGRITY_CSV  = results/stage2_5b_repair/r4_final_integrity_report.csv
```

## Active path inventory

`src/stage2_5b/`:
branch_evaluator.py, controlled_user.py, evaluator.py, evidence_graph.py, __init__.py,
response_library.py, social_style_wrapper.py, trajectory_metrics.py, user_policy.py

`scripts/stage2_5b/`:
analyze_confirmatory.py, assemble_confirmatory_roots.py, audit_all_results.py,
audit_reward_basis.py, calibrate_and_freeze_tasks.py, check_templates.py,
equivalence_analysis.py, extract_failure_cases.py, final_integrity_audit.py,
freeze_benchmark.py, run_full_blocks.py, run_glmm.R, run_stage2_5b_experiment.py,
scan_candidate_tasks.py, select_calibrated_tasks.py, task_cluster_bootstrap.py,
validate_confirmation_evaluator.py, validate_controlled_user.py

`tests/stage2_5b/`: 79 tests across 28 test modules (all passing at freeze).

## Legacy path inventory (audit-only, must NOT be imported by active runtime)

```text
legacy/stage2/        (run_stage2_experiment.py, analyze_stage2.py, src/valence.py, ...)
legacy/stage2_5/      (run_stage2_5_experiment.py, analyze_stage2_5.py, src/stage2_5/*, configs/*)
```

## Baseline test result

```text
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
Ran 79 tests in 0.161s — OK
```

Conda env for this project: `agentsearch` (not MDPC).

## Pre-existing facts confirmed during freeze (relevant to later phases)

- **2.1 stale defaults**: `analyze_confirmatory.py`, `final_integrity_audit.py`,
  `extract_failure_cases.py` all default `--results` to
  `results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic`, and
  default analysis/figures to `results/stage2_5b_analysis` / `figures/stage2_5b`
  (NOT the `_r4` canonical roots).
- **2.2 generic annotation**: `data/stage2_5b/task_policy_annotations.yaml` contains only
  6 legacy tasks (sources 4/30/55 retail, 7/12/44 airline). NONE of the 8 confirmatory
  tasks (retail 41/6/19/2/21/64/23/28) have explicit annotations, so all 8 currently fall
  back to `_generic_annotation` via `_annotation_for(...)`.
- **2.3 benchmark dirty patch**: `/home/xqin5/tau2-bench` has one dirty file
  `src/tau2/data_model/message.py` (+12 lines: a `parse_string_arguments` field validator).
  The diff is embedded inside `artifacts/stage2_5b/tau_snapshot_manifest.json` but is NOT
  exported as a standalone patch file with its own hash. tau2 HEAD = origin/main =
  `ddc66a777e520373975f15d3abec989cfe2ec371`.
- **2.4 evaluator semantics**: `tests/stage2_5b/test_reward_metric_semantics.py` already
  exists and asserts NL_ASSERTION ⇒ official missing, local proxy computed, safe-success
  basis. Gaps to add: ALL_IGNORE_BASIS non-redefinition, confirmation-before-mutation and
  prohibited-mutation safe-success guards.

## Gate 0 — PASS

- [x] Repair branch created (`r4-minimal-repair-canonicalization`)
- [x] Safety tag created (`pre-r4-minimal-repair-20260622-122324`)
- [x] Old results untouched
- [x] Active/legacy inventory generated
- [x] No experiments run before code changes
