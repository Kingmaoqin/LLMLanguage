# GitHub Version Management

Repository: `Kingmaoqin/LLMLanguage`

## Branch policy

- `main` contains the latest reviewed, reproducible major version.
- Every major experimental or architectural change starts from an updated `main` branch.
- Use a dedicated branch named `codex/<short-description>` or
  `experiment/<short-description>`.
- Do not run unrelated major changes in the same branch.

## Required contents of a major-version pull request

Each major version must include:

1. code, configuration, and tests;
2. the frozen experiment or analysis plan;
3. the final report and claim limitations;
4. reproduction commands;
5. a checkpoint or changelog entry;
6. relevant compact source tables and figures;
7. validation results.

Raw model outputs, full conversation logs, model weights, benchmark snapshots, and other
large regenerable artifacts remain outside Git. Their paths, hashes, and reproduction
instructions must be recorded in reports.

## Release procedure

```bash
git switch main
git pull --ff-only
git switch -c codex/<version-description>

# Implement and validate the major change.
git status --short
git diff --check
python -m unittest discover -s tests/stage2_5b

git add <explicit paths>
git commit -m "<version description>"
git push -u origin codex/<version-description>
```

Open a draft pull request against `main`. The pull request description must state:

- what changed;
- why it changed;
- scientific or engineering impact;
- validation commands and results;
- remaining limitations.

After review, merge the pull request and create an annotated semantic tag:

```bash
git switch main
git pull --ff-only
git tag -a vX.Y.Z -m "<release summary>"
git push origin vX.Y.Z
```

## Current release convention

The first public release is the Stage-2.5b controlled-user confirmatory study. Subsequent
large versions should increment:

- major version for incompatible benchmark or research-design changes;
- minor version for new confirmatory models/domains or substantial analysis additions;
- patch version for report, evaluator, or reproducibility corrections that do not change the
  frozen estimand.
