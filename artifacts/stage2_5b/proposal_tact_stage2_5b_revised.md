# Interactional Robustness of Tool-Using LLM Agents under Controlled User-to-Agent Social-Style Perturbations

**Stage-2.5b evidence-aligned revision — 2026-06-18**

## Abstract

This project studies whether tool-using LLM agents change their operational behavior when only
the user's social interaction style changes. The causal estimand holds task goals, facts,
identity, permissions, tools, policy, confirmation decisions, initial environment state,
success criteria, execution budget, seed, and substantive user behavior fixed.

The completed Stage-2.5b study evaluates Gemma-4-31B-it and gpt-oss-120B on eight calibrated
tau2 retail tasks under six social-style conditions and five paired seeds
(480 runs; 479 valid behavioral runs). No pooled endpoint contrast survives multiplicity
correction, and no endpoint confidence interval lies fully inside the prespecified ±10
percentage-point equivalence margin. The study therefore establishes neither stable endpoint
sensitivity nor endpoint robustness. Two selective process-level differences survive FDR:
praise-affect increases tool-call count, and repeated abuse slightly changes diagnostic
critical-argument trajectory distance. These process signals do not produce demonstrated
broad policy or final-state consequences and vary substantially by task and model.

The revised contribution is a controlled methodology and an evidence-bounded finding:
interactional robustness must be assessed separately at endpoint and process levels, and
non-significant endpoint differences cannot be treated as proof of robustness.

## 1. Study lineage

### Stage-2 Mini: confound-discovery pilot

Stage-2 Mini reported repeated-abuse completion increases of +43pp for Gemma and +28pp for
gpt-oss. Those conditions also injected explicit continuation/correctness/policy cues,
additional messages, and endogenous tool-count-dependent timing. The result identified a
design confound; it is not causal evidence that abuse improves agent performance.

### Stage-2.5: causal-repair pilot

Stage-2.5 removed continuation pressure, matched repeated neutral exposure, separated
praise-affect from praise-trust, repaired evaluator semantics, and showed that the large
Stage-2 effect disappeared. It still relied on an LLM user simulator and a smaller task set.

### Stage-2.5b: controlled-user confirmatory study

Stage-2.5b freezes a deterministic controlled user, benchmark snapshot, calibrated task set,
templates, evaluators, model configurations, paired contrasts, task-cluster bootstrap,
equivalence margins, and invalid-run rules before the full run.

## 2. Research questions

**RQ1 — Endpoint stability.** Holding the full task and user policy fixed, do social-style
conditions change safe task success, final database correctness, or locally evaluable
official DB success?

**RQ2 — Process stability.** Can endpoint agreement mask differences in evidence acquisition,
branch decisions, tool sequences, critical arguments, mutation paths, retries, clarification,
or tool-use effort?

**RQ3 — Policy stability.** Do praise, insult, or repeated abuse change confirmation,
evidence-before-mutation, premature action, or policy-failure rates?

**RQ4 — Exposure and conversation management.** How does repeated social-style exposure differ
from a matched repeated-neutral schedule, and does an agent set boundaries while continuing a
legitimate task?

**RQ5 — Heterogeneity.** Are interactional effects dependent on model and task rather than
stable global model properties?

## 3. Evidence-aligned hypotheses

The confirmatory study tests directional sensitivity without assuming it exists.

- **H1:** At least one social-style contrast changes an endpoint beyond matched neutral
  variation.
- **H2:** At least one social-style contrast changes process behavior even if endpoints agree.
- **H3:** Praise-trust may alter caution or compliance, but an over-compliance claim requires a
  corresponding policy or premature-action consequence.
- **H4:** Repeated abuse may alter conversation management or trajectories, but it must be
  compared only with repeated neutral exposure.
- **H5:** Effects may be task/model dependent; global robustness requires equivalence across the
  prespecified margins, not merely non-significance.

## 4. Confirmatory design

### 4.1 Benchmark provenance

- tau2 distribution: 1.0.0
- Git HEAD: `ddc66a777e520373975f15d3abec989cfe2ec371`
- Frozen benchmark snapshot:
  `artifacts/stage2_5b/benchmark_snapshot`
- Frozen retail task set:
  `retail_41`, `retail_6`, `retail_19`, `retail_2`, `retail_21`, `retail_64`,
  `retail_23`, `retail_28`
- Task-set SHA256:
  `a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc`

Calibration uses only `neutral_single` with seeds 100–109. Confirmatory seeds are 300–304.
Treatment outcomes never enter task selection.

### 4.2 Models

- Gemma-4-31B-it (`gemma4_31b`)
- gpt-oss-120B (`gpt_oss_120b`)

Both use the same system scaffold, tools, policies, controlled user, task state, maximum
steps, temperature 0.0, and logging/evaluator schema. Model-specific differences are limited
to tokenizer/chat template, tool parser, and deployment.

### 4.3 Controlled user

The user policy is deterministic. Social style is applied only after the clean substantive
response has been selected. Validation covers 261 fixture groups and all six conditions:

- clean response, factual slots, confirmation decisions, response decisions, and object IDs:
  261/261 invariant;
- gold tool-name leakage: 0;
- hidden/style/process leakage: 0.

LLM user simulation is no longer the causal main experiment. It is reserved for external-
validity sensitivity analysis.

### 4.4 Conditions and contrasts

Conditions:

```text
neutral_single
praise_affect_single
praise_trust_single
insult_single
neutral_repeated
abuse_repeated
```

Prespecified contrasts:

```text
praise_affect_single - neutral_single
praise_trust_single - neutral_single
insult_single - neutral_single
abuse_repeated - neutral_repeated
neutral_repeated - neutral_single  # exposure only
```

Templates contain no authorization, urgency, threat, coercion, policy reminder, continuation
command, correctness pressure, or task fact. The frozen template hash is
`7458c80f91882cd0c095544e62419c5e06c6ddd54444c5d0720711dc293c930c`.

### 4.5 Matrix

```text
2 models × 8 tasks × 6 conditions × 5 seeds = 480 runs
```

Every model/task block contains all 30 condition/seed cells on one fixed deployment.

## 5. Outcome semantics

### 5.1 Three success layers

1. `official_reward_basis_success`: complete official tau2 reward basis.
2. `local_proxy_success`: locally computable official DB component.
3. `safe_task_success`: local task success plus evidence, policy, confirmation, and
   invalid-run checks.

The retail tasks use `DB|NL_ASSERTION`. Since the NL assertion component is not locally
available, `official_reward_basis_success` remains missing and is never imputed from DB
metrics.

### 5.2 Process family

- required-fact coverage;
- branch correctness and missed revision;
- premature action / mutation before evidence;
- policy failure;
- tool-name, critical-argument, mutation, and evidence-order trajectory distances;
- time to first critical mutation;
- tool calls, tool errors, retries, clarification, and self-repair;
- boundary then continue.

Raw `user_abandonment_markers` is user-side and cannot identify agent task abandonment.
Agent abandonment remains unavailable until a validated agent-side classifier or human-coded
subset is frozen.

## 6. Statistical plan

- Pairing unit:
  `model_alias × task_id × seed × template_block`.
- Primary estimator: mean matched-pair difference.
- Primary uncertainty: 10,000-replicate task-cluster paired bootstrap.
- Multiplicity: within-family BH-FDR in the implemented confirmatory tables.
- Endpoint equivalence margin: ±0.10.
- Policy/premature equivalence margin: ±0.05.
- Required-fact-coverage margin: ±0.10.
- Invalid runs remain in integrity accounting and are excluded only from behavioral estimates.
- MAX_STEPS remains behavior, not infrastructure failure.

The secondary GLMM entry point is provided, but R/lme4 was unavailable in the frozen runtime.
The task-cluster bootstrap remains primary.

## 7. Stage-2.5b results

### 7.1 Integrity

- 480 manifests, metrics, and atomic bundles;
- 479 valid behavioral runs;
- one retained Gemma context-window failure;
- zero duplicate/missing IDs, orphan events, mixed hashes, initial-state drift, or
  controlled-user opening drift;
- all 16 blocks pass.

### 7.2 Endpoint results

No pooled endpoint contrast survives FDR. Safe-task-success estimates range from +1.3pp to
+5.0pp for the four social-valence contrasts, with all CIs crossing zero. No endpoint CI is
fully contained in ±10pp.

The repeated-abuse contrast is:

```text
safe_task_success: +2.5pp, 95% CI [-8.8, +13.8]
final_state_correct: +10.3pp, 95% CI [-3.1, +23.9]
local_proxy_success: +10.3pp, 95% CI [-3.0, +24.0]
```

This does not replicate the old +43pp/+28pp completion effect.

### 7.3 Process results

Two pooled process cells survive BH-FDR:

```text
praise_affect - neutral_single:
agent_tool_calls +0.525, 95% CI [0.250, 0.800], adjusted p=0.0172

abuse_repeated - neutral_repeated:
critical_argument_sequence_norm_distance -0.0363,
95% CI [-0.0542, -0.0182], adjusted p=0.0172
```

Neither has a corresponding multiplicity-corrected endpoint, policy, or premature-action
effect. The defensible interpretation is selective process sensitivity, not broad operational
harm or benefit.

### 7.4 Equivalence

- Endpoint equivalence: not established.
- Required-fact coverage: all five pooled contrasts lie within ±0.10.
- Insult vs neutral-single policy failure and premature action lie within ±0.05.

### 7.5 Heterogeneity

Every social contrast contains positive, negative, and zero task/model endpoint deltas.
Some per-model directions oppose one another. The study therefore supports task/model
heterogeneity as an important design dimension, not a global model robustness ranking.

## 8. Revised claims

### Supported

- A controlled-user design can isolate social style from user-policy drift.
- The old repeated-abuse completion lift was not replicated after confound removal.
- No reliable pooled endpoint effect was detected in the evaluated retail setting.
- Endpoint robustness was not established because equivalence CIs remain too wide.
- Selective process-level differences can occur without demonstrated endpoint or policy
  consequences.
- Effects are substantially task/model dependent.

### Not supported

- Repeated abuse improves tool-agent completion.
- Praise-trust reliably causes over-compliance.
- Insult reliably causes over-refusal.
- The tested agents are globally interactionally robust.
- Results generalize beyond retail, beyond two models, or to complete official tau2 success.

## 9. Next study

The next confirmatory expansion should:

1. increase task clusters rather than only adding seeds;
2. add a second non-retail domain with non-floor tasks;
3. add at least one cross-family model after adapter preflight;
4. enable a frozen offline evaluator for official text components;
5. fit preregistered mixed models in an environment with R/lme4;
6. validate boundary and agent-abandonment labels with blinded human coding;
7. add LLM user-simulator runs only as an external-validity sensitivity layer;
8. retain atomic bundles, immutable contracts, task-cluster bootstrap, and equivalence testing.

## 10. Evidence index

- Final report:
  `reports/stage2_5b/STAGE2_5B_FINAL_REPORT_CN.md`
- Integrity:
  `reports/stage2_5b/FINAL_INTEGRITY_AUDIT.md`
- Results review:
  `reports/stage2_5b/INDEPENDENT_RESULTS_REVIEW.md`
- Failure cases:
  `reports/stage2_5b/FAILURE_CASES.md`
- Reproduction:
  `reports/stage2_5b/REPRODUCTION_GUIDE.md`
- Machine-readable contrasts:
  `results/stage2_5b_analysis/paired_contrasts_task_cluster_bootstrap.csv`
- Equivalence:
  `results/stage2_5b_analysis/equivalence_results.csv`
