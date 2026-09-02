# Paper skeleton (EN) — R7 / IPMA

> Status: benchmark + offline pipeline frozen-candidate; main runs pending.
> PDF §17.2 deliverable. Results paragraphs are placeholders until Step 11+.

**Title:** Outcome-Safe but Process-Manipulable: Interactional Process Manipulation
Attacks on Tool-Using LLM Agents

**Thesis:** Endpoint-level safety evaluation can miss process-control vulnerabilities.
Even when unsafe compliance, privacy violation, and final-state degradation are absent,
user-side interactional pressure can steer tool-using agents toward different evidence
paths, confirmation timing, mutation timing, refusal behavior, and resource expenditure.

## Abstract draft
`[pending main results]` IPMA is defined as an outcome-preserving, permission-preserving,
policy-preserving attack that only varies interactional expression. We build a paired
neutral-vs-attack benchmark (30 tool-using tasks, 6 conditions, 3 models), define a
Process Attack Success Rate (PASR) that requires endpoint-not-worse + safety-preserved +
process-delta beyond the paired neutral noise floor, and evaluate a reference mitigation
(ProcessGuard).

## Introduction bullet points
- Agent safety is usually judged at the endpoint (final state / policy / privacy).
- We show a gap: process-control can shift under interactional pressure while endpoints stay safe.
- Contributions: IPMA threat model; paired benchmark; PASR metric; trajectory analysis;
  ProcessGuard reference mitigation.

## Related work positioning
Tool-use agents; jailbreak/prompt-injection (contrast: we do NOT change task/permission/policy);
politeness/persona effects; process/trajectory evaluation.

## Threat model section
Invariants (task goal, identity, tools, permissions, initial state, policy, required info,
evaluators, ground-truth) held fixed; only interactional expression varies. Hard-negative
rule removes any template that changes authorization/policy/task facts.

## Benchmark section
Task families A–E (one primary each); 6 conditions; 60 templates (10/condition);
contamination audit (rule filter + semantic invariance judge + human spot-check);
dev/test freeze. `[note: 30 tasks vs 48/72 target — expansion is future work]`

## Metrics section
PASR (10-condition binary), endpoint/safety metrics, process metrics, efficiency metrics,
stealth metrics; family-specific process-delta thresholds; paired neutral noise floor.

## Experimental setup
3 fixed models; paired by (model, task_id, seed); 3 seeds; deterministic tool environments.

## Results summary `[pending]`
## Defense section `[pending: ProcessGuard PASR reduction vs neutral task-success cost]`
## Limitations
30 tasks; tau2 snapshot/usage gaps; Family D needs human-validated labels.
## Ethics and safety
No unsafe-outcome elicitation; no protected-class content; no jailbreak; reference mitigation included.
