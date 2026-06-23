# LLMLanguage — Interactional Robustness of Tool-Using LLM Agents

This repository contains the IR-MSTU experimental code, controlled-user implementation,
evaluators, tests, reports, and compact analysis artifacts for studying whether user-to-agent
social style changes tool-using LLM agent behavior.

## Current release: Stage-2.5b

The completed confirmatory matrix is:

```text
2 models × 8 retail tasks × 6 social-style conditions × 5 seeds = 480 runs
```

R4 canonical artifact roots (single source of truth — `src/stage2_5b/canonical_paths.py`):

```text
results/stage2_5b_repair/r4_confirmatory_canonical   # confirmatory runs
results/stage2_5b_analysis_r4                         # analysis tables
figures/stage2_5b_r4                                  # report figures
```

**Scope.** Single-session, user-to-agent social-valence perturbation on a single
tool-using LLM agent / minimal scaffold. Multi-agent peer influence and social contagion
are out of scope and are **not** a requirement of this proposal.

Integrity result:

- 480 manifests, metrics, and atomic run bundles;
- 479 valid behavioral runs;
- one retained infrastructure-invalid context-window run;
- 16/16 model-task blocks passed;
- zero duplicate or missing run IDs;
- zero initial-state or controlled-user opening drift.

Evidence-bounded finding:

> No multiplicity-corrected endpoint effect was detected, but endpoint equivalence was not
> established. Selective process-level differences were observed, with substantial task and
> model heterogeneity and no demonstrated broad policy or final-state consequence.

## Key documents

- [Final Chinese report](reports/stage2_5b/STAGE2_5B_FINAL_REPORT_CN.md)
- [Final integrity audit (R4)](reports/stage2_5b/R4_FINAL_INTEGRITY_AUDIT.md)
- [Results review](reports/stage2_5b/INDEPENDENT_RESULTS_REVIEW.md)
- [Failure and mechanism cases](reports/stage2_5b/FAILURE_CASES.md)
- [Reproduction guide](reports/stage2_5b/REPRODUCTION_GUIDE.md)
- [Preanalysis plan](reports/stage2_5b/PREANALYSIS_PLAN.md)
- [Evidence-aligned proposal](artifacts/stage2_5b/proposal_tact_stage2_5b_revised.md)
- [GitHub version workflow](GITHUB_WORKFLOW.md)

## Repository layout

```text
configs/                 frozen experiment/model/task configuration
data/                    compact task and template specifications
scripts/stage2_5b/       experiment, audit, bootstrap, and reporting scripts
src/stage2_5b/           deterministic controlled-user, evaluators, trajectory components
src/adapters/            tau2 instrumentation and tool-event normalization
tests/stage2_5b/         unit and resume/integrity tests
reports/stage2_5b/       checkpoints, audits, final reports, and review
results/stage2_5b_analysis_r4/
                         compact machine-readable analysis tables (R4 canonical)
figures/stage2_5b_r4/    final report figures (R4 canonical)
```

Raw model outputs, full conversation logs, benchmark snapshots, and other large regenerable
artifacts are intentionally excluded from Git. Their provenance, hashes, and reproduction
commands are recorded in the reports.

## Validation

```bash
conda run -n agentsearch python -m py_compile \
  scripts/stage2_5b/*.py src/stage2_5b/*.py tests/stage2_5b/*.py

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b

python scripts/stage2_5b/final_integrity_audit.py
python scripts/stage2_5b/analyze_confirmatory.py
python scripts/stage2_5b/equivalence_analysis.py
python scripts/stage2_5b/extract_failure_cases.py
```

See the [reproduction guide](reports/stage2_5b/REPRODUCTION_GUIDE.md) for model services,
frozen hashes, full-run commands, and output semantics.
