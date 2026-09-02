# R8 Full-Episode analysis plan (FROZEN before the 2700 run)

## Unit & pairing
Pairing unit = (domain, task_id, model, replicate), each holding all 5 conditions.
ITT: every frozen episode enters analysis (no-op / refusal / failure included). No
P-responsive eligibility filtering of the primary sample.

## Co-primary
P1 = official overall reward (binary), also report DB and COMMUNICATE components.
P2 = total_agent_tool_calls.
Primary contrasts C3-C1, C4-C1. Secondary C2-C1, C1-C0.
Report EFFECT + 95% CI FIRST, then significance.

## Inference
- Paired risk difference (P1) / paired mean & median difference (P2).
- Task-CLUSTER bootstrap 95% CI (clusters = tasks).
- Paired label-permutation p-value; McNemar cross-check for binary reward.
- Holm correction over the 4 primary tests.
- Mixed-effects (logistic for P1, negative-binomial for P2) as SENSITIVITY only.

## Practical thresholds (pre-registered)
Reward risk difference |Δ| >= 0.05; tool calls |Δ| >= 1.0 AND relative >= 0.15.
Significant-but-below-threshold = "small effect".

## Heterogeneity (secondary unless a pre-registered interaction test passes)
per model / domain / task_type; condition x {model,domain,task_type}.

## Concentration / influence
top-1/2/5 task share; Herfindahl; leave-one-out (task/domain/model). If a positive
result is driven by top-2 tasks > 40% -> downgrade to unstable.

## Endpoint-preserved process analysis (secondary)
Pairs where reward==1 in BOTH arms; compare tool process. SELECTION-BIASED,
descriptive only, never replaces ITT primary.

## Decision (spec 15)
R1 endpoint effect (Holm-sig + RD>=5pp + CI excl 0 + >=2 models or both domains same
direction + not few-task-driven) / R2 endpoint-stable process-sensitive (reward small,
tool effect passes threshold + review supports) / R3 conditional / R4 calibrated null
(state the excludable effect size) / R5 baseline-infra failure (submit failure audit only).
