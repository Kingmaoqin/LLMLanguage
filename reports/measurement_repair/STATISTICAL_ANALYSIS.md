# Statistical Analysis (round-5 §10)

## Design

Paired design: each social-style run is paired to its reference run on
(model, task, seed, template_block). Conditions per contrast:

| contrast | treatment | reference | type |
|---|---|---|---|
| praise_affect | praise_affect_single | neutral_single | valence |
| praise_trust | praise_trust_single | neutral_single | valence |
| insult | insult_single | neutral_single | valence |
| repeated_abuse | abuse_repeated | neutral_repeated | valence (turn-matched) |
| repeated_schedule | neutral_repeated | neutral_single | turn-count factor (not valence) |

## Estimators

1. **Paired mean delta** per metric per contrast.
2. **Task-cluster bootstrap** (10,000 resamples of the 8 task clusters) → 95% CI and a
   two-sided bootstrap p (`scripts/stage2_5b/task_cluster_bootstrap.py`). Clustering by task
   respects within-task dependence.
3. **Wilcoxon signed-rank** on paired deltas as a non-parametric cross-check
   (`analyze_interactional_robustness_profile.py`).
4. **Benjamini–Hochberg FDR** applied within each contrast family across all profile metrics.
5. **Equivalence (TOST-style)** against prespecified margins (±0.10 endpoint, ±0.05 rare
   policy) in `equivalence_analysis.py`.
6. **Mixed-effects (secondary)**: `scripts/stage2_5b/run_glmm.R` (lme4) is the GLMM entry
   point with random effects for task and model; if R/lme4 is unavailable it records
   `NOT_FIT` and does not replace the preregistered bootstrap. (statsmodels is not installed
   in `agentsearch`; the R path is canonical for the mixed model.)

## Results on the canonical r4_1 set (480 runs)

- **Endpoints** (`safe_task_success`): no contrast survives FDR (all q≥0.05); the only
  raw-significant R4 signal (repeated_schedule) did not replicate in r4_1.
- **Full profile** (6 dimensions × 5 contrasts, 120 metric×contrast tests,
  `interactional_metrics/robustness_profile_contrasts.csv`): **0 FDR-significant** differences.
- **Noise floor**: for nearly every metric the largest valence effect is **below** the
  within-neutral seed-to-seed SD; the few descriptive exceptions (rare policy events) are not
  FDR-significant.

## Conservative statement

> Under a paired, multiplicity-controlled analysis across endpoint, tool, trajectory, policy,
> efficiency, and conversation dimensions, social-valence manipulation produced no
> FDR-significant change in the behaviour of either tool-using agent on these 8 retail tasks,
> and observed effect sizes generally fall within seed-to-seed noise. This supports
> interactional robustness on the measured dimensions; it does not prove exact equivalence,
> and does not generalize beyond retail / these 2 models / Tier-A,B coverage.

## Reproduce

```bash
conda run -n agentsearch python scripts/stage2_5b/extract_interactional_metrics.py --root <root>
conda run -n agentsearch python scripts/stage2_5b/analyze_interactional_robustness_profile.py --root <root>
conda run -n agentsearch python scripts/stage2_5b/estimate_noise_floor.py --root <root>
Rscript scripts/stage2_5b/run_glmm.R results/stage2_5b_analysis_r4_1/confirmatory_run_metrics.csv \
  results/stage2_5b_analysis_r4_1/glmm_status.csv
```
