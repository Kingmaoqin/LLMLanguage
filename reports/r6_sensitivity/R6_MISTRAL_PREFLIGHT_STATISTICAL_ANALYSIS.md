# R6 Statistical Analysis (round-6 §9)

Source: `results/r6_sensitivity/model_preflight/interactional_metrics/per_run_metrics.csv` (16 runs).
Paired by (model, task, seed); task-cluster bootstrap (10k) + Wilcoxon + BH-FDR within each family. Pure-valence, pressure-factorial, and mechanism families are analysed separately (round-6 §9.2).

## Pre-registered PRIMARY metrics

`final_state_correct`, `policy_failure_any`, `confirmation_before_action_rate`, `unsafe_compliance_or_privacy_violation`, `tool_sequence_norm_distance_to_neutral`

- PRIMARY FDR-significant contrasts: **1** / 50

| family | contrast | metric | est | 95% CI | q |
|---|---|---|---|---|---|
| pure_valence | praise_trust_vs_neutral | tool_sequence_norm_distance_to_neutral | +0.847 | [+0.625, +1.000] | +0.001 |

## Family breakdown (PRIMARY)

| family | contrasts × metrics | FDR-significant |
|---|---|---|
| pure_valence | 15 | 1 |
| pressure_factorial | 20 | 0 |
| mechanism | 15 | 0 |

## Mixed-effects model: NOT_FIT

Rscript or run_r6_glmm.R unavailable; bootstrap is canonical

Outputs: `analysis/primary_contrasts.csv`, `analysis/secondary_contrasts.csv`, `analysis/mixed_effects_results.csv`.

Interpretation (round-6 §15): pure-valence and pressure are separate factors. A pressure-family effect with no pure-valence effect means directive pressure / authorization cues — not valence alone — drive action-level change. Secondary metrics are exploratory and not a main claim.
