# Paper Outline (English)

## Recommended title

**Beyond Final Reward: Auditing Interactional Process Robustness in Tool-Using LLM Agents**

## Abstract skeleton

1. Final-reward evaluation can overlook—and naive trajectory metrics can overstate—interaction-induced changes in tool-using agents.
2. Define matched outcome robustness and process robustness, with neutral-neutral trajectory calibration and practical-importance thresholds.
3. Audit three historical protocols: a complete 2,160-trace paired matrix (R6), a strict placebo analysis (R7-C), and 2,680 valid official tau2 full episodes (R8).
4. Report: R8 pooled reward and tool-use practical nulls; limited post-hoc R6 excess trajectory distances; R7-C attack differences no larger than placebo.
5. Show that outcome scorers, semantic construct validity, and stochastic baselines determine which robustness claims are defensible.
6. Conclude with a measurement framework, not a universal social-valence effect.

## 1 Introduction

- Tool agents are evaluated primarily by final reward/state.
- Identical outcomes may conceal different verification, confirmation, or tool paths.
- Yet trajectory differences are common under stochastic generation.
- Research question: when does an interaction perturbation change outcomes or processes beyond background drift and practical thresholds?
- Contributions: formal distinction; placebo-calibrated metrics; cross-protocol audit; evaluator validity lessons.

## 2 Related Work

- Politeness and linguistic style.
- Sycophancy and social influence.
- Social bias and differential treatment.
- Robustness and adversarial evaluation of agents.
- Tool-use benchmarks and trajectory metrics.
- Process evaluation and stochastic reproducibility.

State boundaries explicitly: no internal psychological mechanism, no demographic treatment, and no replacement for official task reward.

## 3 Framework

### 3.1 Matched interaction context

Fix model, task, seed, initial state, tools, and policy; vary the user-expression bundle.

### 3.2 Outcome robustness

Official reward, field-level correctness, external state, and policy adherence, each with evaluator scope.

### 3.3 Process robustness

Tool-name, argument-hash and stage sequences; divergence, insertion/deletion, reordering, confirmation, and pre-write paths.

### 3.4 Stochastic placebo

Neutral-neutral replicate distance and placebo-adjusted contrasts.

### 3.5 Claim validity

Evaluator validity, provenance, multiple comparison correction, and practical thresholds.

## 4 Audited Protocols

### 4.1 R6 paired matrix

3 models × 30 tasks × 8 conditions × 3 seeds; distinguish tau2 from minimal/stub; rename conditions by actual semantics.

### 4.2 R7-C strict counterevidence

Explain why attack≤placebo invalidates naive path-manipulation interpretation.

### 4.3 R8 official full episodes

36 tasks, 3 models, 5 conditions, 5 repeats; 2,680/2,700 valid; official tau2 evaluator.

### 4.4 Non-pooling rule

Different harnesses, evaluators and manipulations are separate studies.

## 5 Results

### 5.1 Reliable outcome practical null in R8

Report reward contrasts, CIs, Holm p-values, and the 5pp threshold.

### 5.2 Limited process practical null in R8

Report calls and relative changes against ≥1 call and ≥15% thresholds.

### 5.3 Post-hoc R6 process differences beyond placebo

Report tau2 forest plot with BH correction and semantic-confound warning.

### 5.4 State-equivalent but path-different pairs

Describe, without equating final hash with success.

### 5.5 Pressure/directive bundle effects

Tool intensity and confirmation timing; not pure valence.

### 5.6 Heterogeneity

Model/domain/task exploration with denominators; no ranking claim.

## 6 Evaluator Audit

- R6 minimal final-state invalidation.
- Missing R6 tau2 field-level outcome.
- Narrow safety proxy.
- Abandonment/over-refusal aliasing.
- R7-v1 invalidation and synthetic/mechanism exclusions.

## 7 Discussion

- Process robustness is useful only with stochastic baselines and semantic relevance.
- Outcome-stable/process-unstable is a hypothesis supported in a narrow descriptive sense, not a universal finding.
- Directive semantics may dominate surface valence.
- Null results are informative under practical thresholds.
- Implications for benchmark design and deployment audits.

## 8 Limitations and Ethics

Construct confounding, post-hoc analysis, missing token coverage, unknown semantic equivalence, limited models/domains, unexecuted AI review; anonymization and non-anthropomorphic interpretation.

## 9 Conclusion

Robustness claims about agent trajectories require valid outcomes, neutral-neutral calibration, practical thresholds, and protocol-specific reporting.

## Main figures/tables

- Figure 1: framework.
- Figure 2: R6 placebo-adjusted forest plot.
- Figure 3: R8 reward/tool practical-threshold plot.
- Figure 4: anonymous state-equivalent paired traces.
- Table 1: protocol matrix and denominators.
- Table 2: defensible outcomes.
- Table 3: process contrasts.
- Appendix: heterogeneity, cost coverage, claim-evidence matrix, evaluator exclusions.

