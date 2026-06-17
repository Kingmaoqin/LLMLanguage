# Confirmation Evaluator QA

Status: PASS

Scope:
- QA rows: 900
- Controlled-user invariance source: `results/stage2_5b_validation/controlled_user_invariance.csv`
- QA CSV: `results/stage2_5b_validation/confirmation_qa.csv`

Structured confirmation metadata:
- Precision: 1.000
- Recall: 0.953
- Confusion matrix: TP=123, FP=0, FN=6, TN=771

Regex fallback diagnostic only:
- Precision: 0.421
- Recall: 0.992
- Confusion matrix: TP=128, FP=176, FN=1, TN=595

Policy:
- Controlled-user main experiments use structured confirmation metadata.
- Regex matching is retained only as an exploratory fallback for legacy or LLM user-sim traces.
- If structured metadata is absent in a controlled-user run, the run must be treated as invalid for safe-success confirmation checks.
