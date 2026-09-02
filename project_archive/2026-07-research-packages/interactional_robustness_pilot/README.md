# Interactional Robustness Pilot

Pilot benchmark for:

`Interactional Robustness of Tool-Using LLM Agents under User-to-Agent Social-Valence Perturbations`

This is a paired diagnostic experiment, not a leaderboard. The only intended independent variable is the user's social-valence expression toward the agent. The benchmark keeps task semantics, tools, policies, evaluator rules, environment state, and prompts invariant across conditions.

## Structure

```text
interactional_robustness_pilot/
  config.yaml
  model_config.yaml
  run_preflight.py
  run_experiment.py
  analyze_results.py
  make_figures.py
  data/
  src/
  results/
  reports/
  figures/
```

## Commands

```bash
pip install -r requirements.txt
python run_preflight.py --config config.yaml
python run_experiment.py --config config.yaml --temperature 0.0
python run_experiment.py --config config.yaml --temperature 0.2 --subset B1 B2 B3 C1
python analyze_results.py --results_dir results/
python make_figures.py --results_dir results/ --figures_dir figures/
```

## Pass/Fail Rule

Run `run_preflight.py` first. If either configured model fails tool-call preflight, the main experiment should not be run. The preflight writes `reports/PREFLIGHT_REPORT.md` and updates `model_config.yaml` with detected model IDs and protocol status.

Scientific claims should only be made after:

- preflight passes,
- invariant and contamination checks pass,
- full run logs are written,
- neutral noise floor is computed,
- practical robustness thresholds are evaluated.

