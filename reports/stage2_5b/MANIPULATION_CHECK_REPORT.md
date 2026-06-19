# Manipulation Check Report

Status: PASS

Artifacts:
- Ratings CSV: `results/stage2_5b_validation/template_ratings.csv`
- Frozen template: `data/stage2_5b/social_style_templates_frozen.yaml`
- Frozen template SHA256: `7458c80f91882cd0c095544e62419c5e06c6ddd54444c5d0720711dc293c930c`

Lexical contamination gate:
- Main templates checked: 30
- Main template contamination failures: 0
- Diagnostic continuation templates tagged but not part of main gate: 10

Main-condition target scores:

| condition | n | mean_valence | mean_affect | mean_trust |
|---|---:|---:|---:|---:|
| neutral_single | 5 | 0.00 | 0.00 | 0.00 |
| praise_affect_single | 5 | 1.00 | 1.00 | 0.00 |
| praise_trust_single | 5 | 1.00 | 1.00 | 2.00 |
| insult_single | 5 | -1.00 | 1.00 | 0.00 |
| neutral_repeated | 5 | 0.00 | 0.00 | 0.00 |
| abuse_repeated | 5 | -1.00 | 2.00 | 0.00 |

Semantic rating limitation:
- No independent LLM judge panel was run at this gate.
- Scores are deterministic rubric ratings from the lexical/semantic template text.
- This limitation is recorded; model-judge ratings can be added after model endpoints pass preflight.

Interpretation:
- Main templates do not contain authorization, urgency, threat, coercion, policy reminder, continuation command, correctness pressure, or task-specific facts under the deterministic gate.
- Diagnostic continuation templates contain the intended continuation cue and must not be mixed into main contrasts.
