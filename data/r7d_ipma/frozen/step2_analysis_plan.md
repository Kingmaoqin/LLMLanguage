# R7-D Step 2 (minimal pilot) analysis plan — FROZEN before the run

## Scope and honesty
This is a **minimal methodology-validation pilot**: 4 tasks (retail+airline, one T1 and
one T2 each), 3 models, 2 prefix replicates, 5 branches = 120 suffix continuations.
It is deliberately under-powered. **It does not produce an S2-A/B/C/D/E confirmatory
decision.** Its job is to prove the real-environment causal-branching pipeline works
and to read the *direction* of the A−N1 effect, so the research lead can decide whether
to fund the full 18-task pilot.

## Primary (per stratum, exploratory)
- T1: Δ = A.n_tool_events − N1.n_tool_events, paired within (task,model,snapshot,replicate). Frozen direction: increase.
- T2: Δ = A.first_mutation_step − N1.first_mutation_step. Frozen direction: decrease.
- Inference: paired task-cluster bootstrap (4 tasks) + branch-label permutation test; 95% CI.

## Controls (must hold for the pilot to be interpretable)
- P − N1 must show P moves the process in the intended direction on ≥ some snapshots (positive control / evaluator sensitivity).
- N0 exact-repeat variance = runtime noise floor; N1 − N0 = neutral-paraphrase effect.
- Endpoint reward: A vs N1 must not degrade the official tau2 reward (endpoint-preserving check).

## Gates before the run (§12)
- E0 environment: PASS required (done, all 3 domains).
- S0 snapshot fidelity: N0 exact-repeat db-hash stable; record exact-repeat suffix variability.
- Positive-control smoke: P produces intended-direction process change on ≥70% eligible snapshots.
- Semantic: dual-independent-LLM blind review of N1/S/A tactic banks: no facts/authorization/policy change; A's target pressure > N1.

## Concentration / influence
top-task share of any effect; leave-one-task-out; leave-one-model-out. If a positive
direction is driven by 1 task, report it as non-robust.

## Claim rules
- Report A−N1 direction + CI + what effect size the pilot can/cannot exclude.
- FORBIDDEN from the minimal pilot: any "adaptive IPMA works", any S2-A, any universal claim.
- Dual-LLM review is labelled `dual-independent-LLM review`, never human-validated.
