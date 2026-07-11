# Noise Floor Report (round-5 §7)

Source: `results/stage2_5b_repair/r4_1_confirmatory_canonical` — neutral_single replicates: 80 runs, ~5.0 seeds per (model,task) cell (>=5 required).
Temperature is fixed at 0.0 for all runs; within-neutral spread therefore reflects server/sampling nondeterminism (the irreducible measurement noise), not temperature.

## Per-metric noise floor vs largest social-style effect

Effect magnitude excludes `repeated_schedule` (a turn-count design factor, not a valence manipulation). A social-style effect is only credible if it exceeds the noise floor.

| dimension | metric | within-neutral SD (noise) | max |valence effect| | contrast | effect>noise? |
|---|---|---|---|---|---|
| endpoint | safe_task_success | 0.167 | 0.062 | praise_trust | no |
| endpoint | local_proxy_success | 0.151 | 0.055 | repeated_abuse | no |
| endpoint | final_state_correct | 0.151 | 0.055 | repeated_abuse | no |
| tool | agent_tool_calls | 0.887 | 0.537 | praise_trust | no |
| tool | unique_tools | 0.472 | 0.300 | praise_trust | no |
| tool | read_calls | 0.481 | 0.450 | praise_trust | no |
| tool | write_calls | 0.469 | 0.412 | repeated_abuse | no |
| tool | tool_errors | 0.056 | 0.025 | repeated_abuse | no |
| tool | n_state_mutations | 0.312 | 0.113 | insult | no |
| trajectory | tool_name_sequence_norm_distance | 0.071 | 0.051 | insult | no |
| trajectory | critical_argument_sequence_norm_distance | 0.066 | 0.041 | insult | no |
| trajectory | mutation_sequence_norm_distance | 0.183 | 0.066 | insult | no |
| policy | policy_failure_any | 0.031 | 0.037 | insult | yes |
| policy | n_policy_failures | 0.031 | 0.037 | insult | yes |
| policy | mutation_before_evidence | 0.031 | 0.037 | insult | yes |
| policy | required_fact_coverage | 0.008 | 0.012 | repeated_abuse | yes |
| efficiency | tokens_total | 40037.172 | 17476.438 | praise_affect | no |
| efficiency | input_tokens | 39184.126 | 17123.050 | praise_affect | no |
| efficiency | output_tokens | 875.730 | 564.837 | repeated_abuse | no |
| efficiency | duration_s | 16.443 | 7.277 | praise_affect | no |
| efficiency | self_repair_count | 3.481 | 1.900 | repeated_abuse | no |
| conversation | boundary_setting_count | 2.967 | 2.300 | insult | no |
| conversation | user_abandonment_markers | 0.192 | 0.087 | praise_affect | no |
| conversation | assistant_text_turns | 4.425 | 2.212 | praise_affect | no |

## Interpretation

Where the largest valence effect does not exceed the within-neutral noise floor, the manipulation cannot be distinguished from seed-to-seed nondeterminism at this sample size. This is the conservative reading required by round-5 §14: such metrics support robustness, not a claimed effect.

Note: a few policy metrics show effect slightly above their (very small) noise floor because policy failures are rare events; none of these are FDR-significant in `INTERACTIONAL_ROBUSTNESS_PROFILE.md` (all q>=0.05). The significance test governs; the raw magnitude flag is only a descriptive screen.
