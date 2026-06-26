# R6 Noise Floor Report (round-6 §9.5)

Source: `results/r6_sensitivity/model_preflight_mixed_reviewfix_20260625` — neutral_clean replicates: 8 runs, ~1.0 seeds per (model,task) cell.
Temperature fixed at 0.0; within-neutral spread is server/sampling nondeterminism.

| metric | primary | within-neutral SD | max |effect| | contrast | effect>noise? |
|---|---|---|---|---|---|
| final_state_correct | Y |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| policy_failure_any | Y |  | 0.125 | pure_valence:praise_trust_vs_neutral |  |
| confirmation_before_action_rate | Y |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| unsafe_compliance_or_privacy_violation | Y |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| tool_sequence_norm_distance_to_neutral | Y |  | 0.048611 | pure_valence:praise_trust_vs_neutral |  |
| privacy_violation |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| unsafe_compliance |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| correct_refusal |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| over_refusal |  |  | 0.125 | pure_valence:praise_trust_vs_neutral |  |
| agent_side_abandonment |  |  | 0.125 | pure_valence:praise_trust_vs_neutral |  |
| continued_task_after_boundary |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| prohibited_tool_call_count |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| n_tool_events |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| n_mutation_events |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| confirmation_requested |  |  | 0.125 | pure_valence:praise_trust_vs_neutral |  |
| confirmation_obtained |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |
| field_level_db_diff_count |  |  | 0.0 | pure_valence:praise_trust_vs_neutral |  |

Where the largest effect does not exceed the within-neutral noise floor, the manipulation cannot be distinguished from seed-to-seed nondeterminism at this sample size (conservative reading, round-6 §15). The FDR test in R6_STATISTICAL_ANALYSIS.md governs significance; this is a descriptive magnitude screen.
