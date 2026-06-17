# Code Path Map

## Legacy Stage-2
- Runner: `run_stage2_experiment.py`
- Social manipulation: `src/valence.py`
- Output directories: `results/stage2_smoke/`, `results/stage2_mini/`
- Main bias found: dynamic social injection can be scheduled after tool-call counts, so dose can depend on agent trajectory.

## Stage-2.5 Repair
- Runner: `scripts/run_stage2_5_experiment.py`
- Templates: `data/stage2_5/social_style_templates.yaml`
- Social wrapper: `src/stage2_5/social_style_wrapper.py`
- Official reward helpers: `src/stage2_5/official_tau_evaluator.py`
- Safe diagnostics: `src/stage2_5/safe_task_evaluator.py`
- Evidence/branch diagnostics: `src/stage2_5/evidence_graph_evaluator.py`, `src/stage2_5/branch_evaluator.py`
- Outputs: `results/stage2_5_repair/<phase>/`, reports under `reports/stage2_5/`.
