# Next Steps (round-5 §9, §17)

## Status

Measurement pipeline is repaired and validated on existing data **without a rerun**:
the 480 r4_1 runs reconstruct to complete traces, the token bug is fixed, and the full
six-dimension robustness profile shows 0 FDR-significant differences. A measurement-complete
runner exists and passed smoke: `measurement_complete_smoke_r5` has 24/24 runs, 24/24 traces,
24/24 interactional metric rows, and 0 invalid runs. Full rerun remains gated on approval.

## Is a full rerun required?

**No, not for measurement completeness.** Every analysis dimension is recoverable from the
frozen bundles (see `RECONSTRUCTION_AUDIT.md`). A fresh full rerun is only warranted if either:

1. field-level DB state diffs are required (currently hash-level only), or
2. per-message token usage is required (currently aggregate input/output), or
3. you want a second independent sample to test replication of any borderline effect.

If you approve a fresh measurement-complete full run, it writes to a new versioned root and
never overwrites R4 / r4_1.

## Cluster commands (run in order; only after approval for `--phase full`)

```bash
cd /home/xqin5/llmlanguage/ir_mstu_stage2
# endpoints: gemma4_31b @127.0.0.1:8005, gpt_oss_120b @127.0.0.1:8192

# completed code+smoke gate:
conda run -n agentsearch python scripts/stage2_5b/run_measurement_complete_experiment.py --phase smoke --tag r5

# gated on approval:
conda run -n agentsearch python scripts/stage2_5b/run_measurement_complete_experiment.py --phase pilot
conda run -n agentsearch python scripts/stage2_5b/run_measurement_complete_experiment.py --phase full
# the wrapper auto-runs reconstruct + extract; then:
NEW=results/stage2_5b_repair/measurement_complete_full_<stamp>
conda run -n agentsearch python scripts/stage2_5b/final_integrity_audit.py --root $NEW \
  --csv $NEW/final_integrity_report.csv --report reports/measurement_repair/MC_FULL_INTEGRITY.md
conda run -n agentsearch python scripts/stage2_5b/analyze_interactional_robustness_profile.py --root $NEW
conda run -n agentsearch python scripts/stage2_5b/estimate_noise_floor.py --root $NEW
```

## Only after measurement is locked (round-5 §15, P3/P4)

- Tier-C boundary/unsafe task coverage.
- Expand beyond retail (airline / calendar / workspace) and 2 → 3–5 models.
- LLM-user-simulator sensitivity as a robustness check (kept out of the main, deterministic design).

## Push order

All of the above runs on the cluster first; push to GitHub only after artifacts are verified
(round-5 top rule). This round's code + reports + analysis on existing data are ready to push;
the full measurement-complete rerun is **not** started pending approval.
