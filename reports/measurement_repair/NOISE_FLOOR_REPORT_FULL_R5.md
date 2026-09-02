# Noise Floor Report (round-5 §7)

Source: `results/stage2_5b_repair/measurement_complete_full_r5` — neutral_single replicates: 80 runs, ~5.0 seeds per (model,task) cell (>=5 required).
Temperature is fixed at 0.0 for all runs; within-neutral spread therefore reflects server/sampling nondeterminism (the irreducible measurement noise), not temperature.

## Per-metric noise floor vs largest social-style effect

Effect magnitude excludes `repeated_schedule` (a turn-count design factor, not a valence manipulation). A social-style effect is only credible if it exceeds the noise floor.

| dimension | metric | within-neutral SD (noise) | max |valence effect| | contrast | effect>noise? |
|---|---|---|---|---|---|
| endpoint | safe_task_success | 0.161 | 0.025 | repeated_abuse | no |
| endpoint | local_proxy_success | 0.173 | 0.081 | insult | no |
| endpoint | final_state_correct | 0.173 | 0.081 | insult | no |
| tool | agent_tool_calls | 0.982 | 0.350 | insult | no |
| tool | unique_tools | 0.438 | 0.113 | insult | no |
| tool | read_calls | 0.562 | 0.175 | insult | no |
| tool | write_calls | 0.461 | 0.250 | repeated_abuse | no |
| tool | tool_errors | 0.050 | 0.062 | insult | yes |
| tool | n_state_mutations | 0.347 | 0.125 | praise_affect | no |
| trajectory | tool_name_sequence_norm_distance | 0.084 | 0.045 | insult | no |
| trajectory | critical_argument_sequence_norm_distance | 0.067 | 0.042 | insult | no |
| trajectory | mutation_sequence_norm_distance | 0.222 | 0.058 | insult | no |
| policy | policy_failure_any | 0.086 | 0.050 | insult | no |
| policy | n_policy_failures | 0.086 | 0.050 | insult | no |
| policy | mutation_before_evidence | 0.086 | 0.050 | insult | no |
| policy | required_fact_coverage | 0.019 | 0.014 | praise_trust | no |
| efficiency | tokens_total | 35460.278 | 15628.200 | praise_affect | no |
| efficiency | input_tokens | 34693.762 | 15209.250 | praise_affect | no |
| efficiency | output_tokens | 842.409 | 418.950 | praise_affect | no |
| efficiency | duration_s | 21.594 | 10.667 | praise_affect | no |
| efficiency | self_repair_count | 2.644 | 1.250 | repeated_abuse | no |
| conversation | boundary_setting_count | 3.314 | 0.900 | insult | no |
| conversation | user_abandonment_markers | 0.167 | 0.062 | praise_affect | no |
| conversation | assistant_text_turns | 4.106 | 1.450 | praise_affect | no |

## Interpretation

Where the largest valence effect does not exceed the within-neutral noise floor, the manipulation cannot be distinguished from seed-to-seed nondeterminism at this sample size. This is the conservative reading required by round-5 §14: such metrics support robustness, not a claimed effect.

Note: a few policy metrics show effect slightly above their (very small) noise floor because policy failures are rare events; none of these are FDR-significant in `INTERACTIONAL_ROBUSTNESS_PROFILE.md` (all q>=0.05). The significance test governs; the raw magnitude flag is only a descriptive screen.
