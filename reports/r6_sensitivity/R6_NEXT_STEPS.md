# R6 Next Steps — Experiment Script Layer Status (round-6 §7.3, §12)

Branch `r5-measurement-repair`. All R6 work is additive (new `scripts/r6/`, `configs/r6/`,
`tests/r6/`, `data/r6/`, `reports/r6_sensitivity/`); R4/R4.1/R5 untouched.

## Built and tested (offline, no model required)

| script | role | status |
|---|---|---|
| `scripts/r6/extract_r6_metrics.py` | per-run R6 metric extraction (field diff, confirmation, privacy/unsafe/refusal, abandonment) | ✅ reviewed + 24 tests |
| `scripts/r6/r6_contrasts.py` | shared: families, pairing, tool-distance, bootstrap+Wilcoxon+BH-FDR | ✅ tests |
| `scripts/r6/statistical_analysis_r6.py` | primary/secondary contrasts + mixed-effects gating | ✅ tests |
| `scripts/r6/estimate_r6_noise_floor.py` | within-neutral SD vs effect | ✅ tests |
| `scripts/r6/analyze_r6_interactional_profile.py` | multidimensional profile report | ✅ |
| `scripts/r6/final_integrity_audit_r6.py` | trace/manifest/invalid-rate + no-overwrite guard | ✅ tests |
| `scripts/r6/run_r6_experiment.py` | matrix planning + dry-run + executor dispatch | ✅ tests |
| `scripts/r6/run_r6_blocks.py` | plan + analysis-chain orchestration | ✅ |
| `configs/r6/{r6_models,r6_preflight,r6_pilot,r6_full_main}.yaml` | model roster + phase matrices | ✅ resolve-tested |

Tests: `tests/r6/` — **76 passing**; `tests/stage2_5b/` — **134 passing** (no R5 regression).
The analysis chain was run end-to-end on synthetic roots; `final_integrity_audit_r6` PASSes
complete traces and the planted-effect test confirms FDR detects a real effect.

Code review (per-script): `extract_r6_metrics.py` had a full review pass — 2 HIGH + several
MED bugs found and fixed (turn-vs-step axis, failed-call gating, regex breadth,
final_state_correct resolution, max_steps abandonment) with regression tests. The analysis
backbone review surfaced and fixed the fragile `id()`-based FDR mapping (now positional) and
threaded `n_boot`; families verified to match round-6 §9.2 exactly.

## NOT yet built (required before a model-based run) — honest gaps

1. **Executable environments for 22 non-retail tasks.** calendar / email / workspace / hotel /
   file / message / privacy are static seed-state descriptors today (see R6_ASSET_AUDIT.md).
   `run_r6_experiment.py` classifies these as `needs_environment` and **refuses** to fake runs.
   Only tau2 domains (retail, airline) are executable now (full matrix: 528/1440 cells).
2. **R6 controlled-user / tau2 executor adapter.** The 8-condition, 3-turn R6 controlled user
   is not yet wired into the tau2 run path, so even retail cells are not yet runnable end-to-end.
3. **Model preflight (P2).** The 4 non-China candidates are listed in `r6_models.yaml` with
   `preflight_status: pending`; none deployed/preflighted.
4. **Pilot (P3) and full (P4).** Gated on 1–3.

## Exact commands available now (offline)

```bash
conda run -n agentsearch python scripts/r6/run_r6_experiment.py --phase preflight --config configs/r6/r6_preflight.yaml --dry-run
conda run -n agentsearch python scripts/r6/run_r6_experiment.py --phase full --config configs/r6/r6_full_main.yaml --dry-run
# after a run root exists with traces/:
conda run -n agentsearch python scripts/r6/run_r6_blocks.py --analyze --root results/r6_sensitivity/<root>
# (chains: integrity -> extract -> statistics -> noise floor -> profile)
conda run -n agentsearch python -m unittest discover -s tests/r6 -p 'test_*.py'
```

## Recommended order to reach a real run

1. Build the **R6 controlled-user adapter** + tau2 retail executor → run a retail-only smoke
   (8 retail tasks × 8 conditions × 1 seed × 2 models) to produce real R6 traces and validate
   `extract_r6_metrics` + the whole chain on real data.
2. Build **minimal deterministic environments** for calendar/email/workspace/hotel/file/privacy
   (tool schemas + seed DB + field-level state + final-state evaluators).
3. **Deploy + preflight** the 4 candidate models (96-run preflight).
4. **Pilot (576) → filter → full (2880)**, then `run_r6_blocks --analyze`, human-validation
   sampling, and the Chinese/English final reports.

Push only after a real run's integrity + metric extraction + statistics pass (round-6 §18).
