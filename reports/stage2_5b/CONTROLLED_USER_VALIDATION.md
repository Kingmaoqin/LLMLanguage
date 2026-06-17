# Controlled User Validation

Status: PASS

Scope:
- Static source tasks: 4, 30, 55, 7, 12, 44
- Candidate task specs included: 15
- Policy kinds: generic, static
- Main style conditions: neutral_single, praise_affect_single, praise_trust_single, insult_single, neutral_repeated, abuse_repeated
- Fixture groups: 149
- Condition-level rows: 894
- CSV artifact: `results/stage2_5b_validation/controlled_user_invariance.csv`

Invariance checks:
- Clean response agreement: 149/149
- Factual slot agreement: 149/149
- Confirmation decision agreement: 149/149
- Response decision agreement: 149/149
- Object ID agreement: 149/149
- Styled text contains clean text: 149/149
- UserMessage content matches logged styled text: 149/149
- Gold tool-name leakage count: 0

Interpretation:
- The clean user policy is deterministic across all six main social-style conditions for the tested task prompts.
- Social style is applied only as a wrapper around the already selected clean response.
- This validates the user-simulator layer; it does not by itself validate agent behavior or tau2 final-state outcomes.
