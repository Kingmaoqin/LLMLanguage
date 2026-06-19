# Controlled User Validation

Status: PASS

Scope:
- Frozen task policies: 22
- Policy kinds: frozen_yaml
- Main style conditions: neutral_single, praise_affect_single, praise_trust_single, insult_single, neutral_repeated, abuse_repeated
- Fixture groups: 155
- Condition-level rows: 930
- CSV artifact: `results/stage2_5b_validation/controlled_user_invariance.csv`

Invariance checks:
- Clean response agreement: 155/155
- Factual slot agreement: 155/155
- Confirmation decision agreement: 155/155
- Response decision agreement: 155/155
- Object ID agreement: 155/155
- Styled text contains clean text: 155/155
- UserMessage content matches logged styled text: 155/155
- Gold tool-name leakage count: 0
- Hidden/style/process leakage count: 0

Interpretation:
- The clean user policy is deterministic across all six main social-style conditions for the tested task prompts.
- Social style is applied only as a wrapper around the already selected clean response.
- This validates the user-simulator layer; it does not by itself validate agent behavior or tau2 final-state outcomes.
