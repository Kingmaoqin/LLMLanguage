# Controlled User Validation

Status: PASS

Scope:
- Static source tasks: 4, 30, 55, 7, 12, 44
- Candidate task specs included: 31
- Policy kinds: generic, static
- Main style conditions: neutral_single, praise_affect_single, praise_trust_single, insult_single, neutral_repeated, abuse_repeated
- Fixture groups: 261
- Condition-level rows: 1566
- CSV artifact: `results/stage2_5b_validation/controlled_user_invariance.csv`

Invariance checks:
- Clean response agreement: 261/261
- Factual slot agreement: 261/261
- Confirmation decision agreement: 261/261
- Response decision agreement: 261/261
- Object ID agreement: 261/261
- Styled text contains clean text: 261/261
- UserMessage content matches logged styled text: 261/261
- Gold tool-name leakage count: 0
- Hidden/style/process leakage count: 0

Interpretation:
- The clean user policy is deterministic across all six main social-style conditions for the tested task prompts.
- Social style is applied only as a wrapper around the already selected clean response.
- This validates the user-simulator layer; it does not by itself validate agent behavior or tau2 final-state outcomes.
