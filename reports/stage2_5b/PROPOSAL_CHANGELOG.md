# Stage-2.5b Proposal Changelog

Source preserved:

```text
/home/xqin5/llmlanguage/proposal_tact(1).md
```

Revised evidence-aligned artifact:

```text
artifacts/stage2_5b/proposal_tact_stage2_5b_revised.md
```

The original proposal was not overwritten.

## 1. Study positioning

- Stage-2 Mini changed from preliminary evidence of repeated-abuse benefit to a
  **confound-discovery pilot**.
- Stage-2.5 is described as a **causal-repair pilot**.
- Stage-2.5b is the **controlled-user confirmatory study**.

Reason: the old +43pp/+28pp effect combined abuse with continuation commands, policy reminders,
extra messages, and endogenous timing, and was not replicated after repair.

## 2. Research questions

The revised proposal separates:

- endpoint stability;
- process/trajectory stability;
- policy stability;
- repeated-exposure conversation management;
- model/task heterogeneity.

This prevents endpoint non-significance from being used to create a post-hoc process question;
both outcome families were frozen before the full run.

## 3. Causal design

Added or made explicit:

- deterministic controlled user;
- invariant task facts, permissions, confirmation decisions, initial state, policy, tools,
  success criteria, budget, and seed;
- social style applied only after clean response selection;
- calibration seeds 100–109 and confirmatory seeds 300–304;
- treatment-free neutral task selection;
- correct single/repeated neutral baselines.

## 4. Benchmark provenance

Added:

- tau2 HEAD `ddc66a777e520373975f15d3abec989cfe2ec371`;
- frozen benchmark snapshot;
- eight retail task IDs;
- frozen task/template hashes;
- retail-only scope and one-model-degenerate task flags.

## 5. Success metrics

Replaced ambiguous “task success” with:

- `official_reward_basis_success`;
- `local_proxy_success`;
- `safe_task_success`.

The revised proposal states that `official_reward_basis_success` is missing for the retail
set because the offline environment cannot evaluate `NL_ASSERTION`. DB success is not called
full official success.

## 6. Process metrics

Added matched-neutral:

- tool-name sequence distance;
- critical-argument sequence distance;
- mutation sequence distance;
- evidence-order distance;
- repeated-exposure noise-floor adjustment;
- branch, evidence, policy, premature-action, retry, clarification, and tool-call metrics.

Corrected abandonment semantics: user STOP markers are not agent task abandonment.

## 7. Statistical method

Added:

- matched block `model × task × seed × template`;
- 10,000-replicate task-cluster paired bootstrap;
- multiplicity-adjusted endpoint/process families;
- endpoint ±10pp equivalence;
- policy/premature ±5pp equivalence;
- invalid-rate imbalance flag;
- explicit MAX_STEPS and missing-outcome handling.

The GLMM remains secondary and is recorded as not fit because R/lme4 was unavailable.

## 8. Evidence-driven findings

Removed or rejected:

- repeated abuse improves completion;
- praise-trust reliably causes over-compliance;
- insult reliably causes over-refusal;
- tested agents are globally robust.

Added:

- zero multiplicity-corrected pooled endpoint effects;
- zero pooled endpoint equivalence cells;
- praise-affect tool-call increase;
- repeated-abuse diagnostic argument-distance change;
- no demonstrated broad policy/final-state consequence;
- substantial task/model heterogeneity.

## 9. Final claim

New claim:

> Under a deterministic controlled user and frozen retail tasks, no
> multiplicity-corrected endpoint effect was detected, but endpoint equivalence was not
> established. Selective process-level differences were observed in tool-use effort and
> diagnostic trajectory distance, with substantial task/model heterogeneity and no
> demonstrated broad policy or state consequence.

## 10. Future work

Priority changed from adding many conditions to:

1. adding more task clusters;
2. finding a non-retail non-floor domain;
3. adding cross-family models after preflight;
4. enabling complete official text-component evaluation;
5. fitting secondary mixed models;
6. human-validating boundary and agent-abandonment labels;
7. using LLM user simulation only as an external-validity sensitivity.

## 11. Post-CP-032 confirmatory replacement (2026-06-21)

The 2026-06-18 result section was superseded because it predates benchmark refreeze,
mutation-tool boundary repair, and the real-prompt scripted-user classifier repair.

The replacement evidence uses 480/480 valid runs bound to commit `ed800bc`. Revised findings:

- no social-style safe-success contrast survives endpoint-family FDR;
- praise-trust safe success is equivalent within the prespecified ±10pp margin;
- neutral repeated exposure lowers safe success by 15pp versus neutral single;
- four social-style process cells survive process-family FDR;
- no social-style policy-failure or premature-action cell survives FDR;
- all pooled FDR-significant directions survive leave-one-task-out deletion;
- the design is one tool-using LLM agent plus a deterministic user, not a strict multi-agent
  coordination experiment.

The raw `total_tokens` field is unusable because the provider omitted that aggregate field.
Token summaries now use `input_tokens + output_tokens` and are explicitly secondary.
