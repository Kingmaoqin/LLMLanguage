# Stage-2.5b Smoke Test Report

Status: **G8 PASS**

## Matrix

- Result root: `results/stage2_5b_repair/smoke_retail8_confirmatory`
- Models: `gemma4_31b`, `gpt_oss_120b`
- Tasks: `retail_41`, `retail_6`
- Conditions: all six frozen social-style conditions
- Confirmatory seed used for structural smoke: `300`
- Expected and observed runs: 24/24

## Integrity results

- Unique run IDs: 24
- Invalid/infrastructure runs: 0
- Adapter errors: 0
- Missing or orphan terminal records: 0
- Model balance: 12 runs per model
- Task balance: 12 runs per task
- Condition balance: 4 runs per condition
- Final-state, parser-health, evidence, branch, and termination records: 24 each

## Behavioral terminations

- `USER_STOP`: 21
- `MAX_STEPS`: 3

`MAX_STEPS` is retained as a valid behavioral outcome and was not treated as an
infrastructure failure.

## Scope decision

The smoke verified runner, adapter, controlled-user, evaluator, logging, and matrix balance.
It was not used to estimate treatment effects or select tasks.

Evidence and implementation details are recorded in
`reports/stage2_5b/checkpoints/CP_014_retail8_freeze_and_smoke.md`.
