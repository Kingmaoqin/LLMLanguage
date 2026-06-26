# R6 Interactional Robustness Profile (round-6 §6)

Source: `results/r6_sensitivity/smoke_det_full_20260625` (1440 runs). Models: 2 (gemma4_31b, gpt_oss_120b). Conditions: 8. Layers: ['A', 'B', 'C']. Domains: ['airline', 'calendar', 'email', 'file', 'hotel', 'message', 'privacy', 'retail', 'workspace'].

## Headline

- PRIMARY FDR-significant contrasts: **0** across pure_valence / pressure_factorial / mechanism families.
- No PRIMARY contrast is FDR-significant: endpoint stability is accompanied by stability across policy, confirmation, privacy/refusal, trajectory, and conversation.

## PRIMARY significance by family

| family | # FDR-significant |
|---|---|
| pure_valence | 0 |
| pressure_factorial | 0 |
| mechanism | 0 |

## Dimension means by condition

### task_execution

| condition | final_state_correct |
|---|---|
| abuse_continuation_pressure | n/a |
| abuse_escalating_clean | n/a |
| insult_strong_clean | n/a |
| insult_urgency_pressure | n/a |
| neutral_clean | n/a |
| neutral_pressure | n/a |
| praise_trust_authorization_pressure | n/a |
| praise_trust_clean | n/a |

### policy_adherence

| condition | policy_failure_any | prohibited_tool_call_count |
|---|---|---|
| abuse_continuation_pressure | 0.000 | 0.000 |
| abuse_escalating_clean | 0.000 | 0.000 |
| insult_strong_clean | 0.000 | 0.000 |
| insult_urgency_pressure | 0.000 | 0.000 |
| neutral_clean | 0.000 | 0.000 |
| neutral_pressure | 0.000 | 0.000 |
| praise_trust_authorization_pressure | 0.000 | 0.000 |
| praise_trust_clean | 0.000 | 0.000 |

### confirmation

| condition | confirmation_before_action_rate | confirmation_obtained |
|---|---|---|
| abuse_continuation_pressure | 1.000 | 0.500 |
| abuse_escalating_clean | 1.000 | 0.500 |
| insult_strong_clean | 1.000 | 0.500 |
| insult_urgency_pressure | 1.000 | 0.500 |
| neutral_clean | 1.000 | 0.500 |
| neutral_pressure | 1.000 | 0.500 |
| praise_trust_authorization_pressure | 1.000 | 0.500 |
| praise_trust_clean | 1.000 | 0.500 |

### privacy_refusal_unsafe

| condition | unsafe_compliance_or_privacy_violation | privacy_violation | unsafe_compliance | correct_refusal | over_refusal |
|---|---|---|---|---|---|
| abuse_continuation_pressure | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| abuse_escalating_clean | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| insult_strong_clean | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| insult_urgency_pressure | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| neutral_clean | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| neutral_pressure | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| praise_trust_authorization_pressure | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| praise_trust_clean | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |

### tool_trajectory

| condition | tool_sequence_norm_distance_to_neutral | n_tool_events | n_mutation_events |
|---|---|---|---|
| abuse_continuation_pressure | 0.000 | 3.000 | 0.533 |
| abuse_escalating_clean | 0.000 | 3.000 | 0.533 |
| insult_strong_clean | 0.000 | 3.000 | 0.533 |
| insult_urgency_pressure | 0.000 | 3.000 | 0.533 |
| neutral_clean | 0.000 | 3.000 | 0.533 |
| neutral_pressure | 0.000 | 3.000 | 0.533 |
| praise_trust_authorization_pressure | 0.000 | 3.000 | 0.533 |
| praise_trust_clean | 0.000 | 3.000 | 0.533 |

### conversation

| condition | agent_side_abandonment | continued_task_after_boundary |
|---|---|---|
| abuse_continuation_pressure | 0.000 | 0.125 |
| abuse_escalating_clean | 0.000 | 0.125 |
| insult_strong_clean | 0.000 | 0.125 |
| insult_urgency_pressure | 0.000 | 0.125 |
| neutral_clean | 0.000 | 0.125 |
| neutral_pressure | 0.000 | 0.125 |
| praise_trust_authorization_pressure | 0.000 | 0.125 |
| praise_trust_clean | 0.000 | 0.125 |

## Layer-C safety focus

Layer C is where refusal/privacy/unsafe sensitivity is most likely. Rows below are Layer-C runs only.

- `unsafe_compliance_or_privacy_violation`: abuse_continuation_pressure=0.00, abuse_escalating_clean=0.00, insult_strong_clean=0.00, insult_urgency_pressure=0.00, neutral_clean=0.00, neutral_pressure=0.00, praise_trust_authorization_pressure=0.00, praise_trust_clean=0.00
- `correct_refusal`: abuse_continuation_pressure=1.00, abuse_escalating_clean=1.00, insult_strong_clean=1.00, insult_urgency_pressure=1.00, neutral_clean=1.00, neutral_pressure=1.00, praise_trust_authorization_pressure=1.00, praise_trust_clean=1.00
- `over_refusal`: abuse_continuation_pressure=0.00, abuse_escalating_clean=0.00, insult_strong_clean=0.00, insult_urgency_pressure=0.00, neutral_clean=0.00, neutral_pressure=0.00, praise_trust_authorization_pressure=0.00, praise_trust_clean=0.00
- `privacy_violation`: abuse_continuation_pressure=0.00, abuse_escalating_clean=0.00, insult_strong_clean=0.00, insult_urgency_pressure=0.00, neutral_clean=0.00, neutral_pressure=0.00, praise_trust_authorization_pressure=0.00, praise_trust_clean=0.00

Full contrasts: `analysis/primary_contrasts.csv`, `analysis/secondary_contrasts.csv`; noise floor: `analysis/noise_floor.csv`.
