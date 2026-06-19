# Stage-2.5b Pilot Test Report

Status: **G9 PASS**

## Matrix

- Result root: `results/stage2_5b_repair/pilot_retail8_confirmatory`
- Models: `gemma4_31b`, `gpt_oss_120b`
- Tasks: `retail_2`, `retail_41`, `retail_6`, `retail_19`
- Conditions: all six frozen social-style conditions
- Seeds: `300`, `301`
- Expected and observed runs: 96/96

## Integrity results

- Unique run IDs: 96
- Invalid/infrastructure runs: 0
- Adapter errors: 0
- Missing, duplicate, or orphan IDs: 0
- Model balance: 48 runs per model
- Task balance: 24 runs per task
- Condition balance: 16 runs per condition
- Seed balance: 48 runs per seed
- Final-state, parser-health, evidence, branch, and termination records: 96 each
- Conversation records: 2,992
- Normalized tool events: 810

## Behavioral terminations

- `USER_STOP`: 83
- `MAX_STEPS`: 13

All 13 `MAX_STEPS` runs remained in the pilot accounting. They were not reclassified as
invalid or removed.

## Use restriction

The pilot was inspected only for implementation integrity, runtime stability, matrix
balance, and global non-degeneracy. Pilot treatment contrasts were not used to change tasks,
models, outcomes, contrasts, equivalence margins, or the confirmatory analysis.

The preanalysis plan was frozen after this gate at
`reports/stage2_5b/PREANALYSIS_PLAN.md`; implementation details are recorded in
`reports/stage2_5b/checkpoints/CP_015_pilot_and_preanalysis.md`.
