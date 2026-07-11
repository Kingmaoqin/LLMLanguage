# Round-5 Measurement-Complete Smoke Report

Command:

```bash
conda run -n agentsearch python scripts/stage2_5b/run_measurement_complete_experiment.py --phase smoke --tag r5
```

Output root: `results/stage2_5b_repair/measurement_complete_smoke_r5/`
Matrix: 2 models × 2 tasks (retail_41, retail_6) × 6 conditions × 1 seed = 24 runs.

## Smoke gate — PASS

| check | result |
|---|---|
| run bundles | 24 |
| reconstructed traces | 24 (100% complete, 0 schema failures) |
| per-run interactional-metric rows | 24 |
| models / tasks / conditions | 2 / 2 / 6 |
| duplicate run_ids | 0 |
| token_source | prompt_plus_completion ×24 (0 missing) |
| auto post-steps | reconstruct + extract ran automatically via the wrapper |

The token fix is now confirmed end-to-end on **fresh** runs (not just recovered offline):
the source-level `_usage_tokens` emits a correct positive total with provenance.

The wrapper writes a single flat result root; `reconstruct_traces_from_existing_artifacts.py`
handles both the flat layout and the block-structured R4/R4.1 layout.

Unit tests: 134 passing (`conda run -n agentsearch python -m unittest discover -s tests/stage2_5b`).

## Decision

Smoke validates the full measurement-complete pipeline. The full (`--phase full`) and pilot
runs remain **gated on explicit approval** (round-5 §15 / user instruction). No full rerun
started. Measurement completeness on existing data is already established (see
`RECONSTRUCTION_AUDIT.md`, `INTERACTIONAL_ROBUSTNESS_PROFILE.md`).
