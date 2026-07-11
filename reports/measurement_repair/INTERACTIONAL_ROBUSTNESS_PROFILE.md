# Interactional Robustness Profile (round-5 §6, §14)

Source: `results/stage2_5b_repair/r4_1_confirmatory_canonical/interactional_metrics/per_run_metrics.csv` (480 runs).
Paired by (model, task, seed, template_block); task-cluster bootstrap (10k) CI + Wilcoxon signed-rank + Benjamini-Hochberg within each contrast family.

## Headline

- FDR-significant dimension differences: **0** across all contrasts/metrics.
- No dimension shows an FDR-significant difference: endpoint stability is accompanied by trajectory/policy/state/conversation stability.

## FDR-significant findings by dimension

_None._

## Per-dimension significance count

| dimension | n FDR-significant |
|---|---|
| endpoint | 0 |
| tool | 0 |
| trajectory | 0 |
| policy | 0 |
| efficiency | 0 |
| conversation | 0 |

Full table: `interactional_metrics/robustness_profile_contrasts.csv`.
