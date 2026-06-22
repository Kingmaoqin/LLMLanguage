# Confirmation Evaluator QA

Status: PASS

Scope:
- QA rows: 936
- Controlled-user invariance source: `results/stage2_5b_validation/controlled_user_invariance.csv`
- QA CSV: `results/stage2_5b_validation/confirmation_qa.csv`

Structured confirmation metadata:
- Precision: 1.000
- Recall: 1.000
- Confusion matrix: TP=135, FP=0, FN=0, TN=801

Regex fallback diagnostic only:
- Precision: 0.609
- Recall: 0.993
- Confusion matrix: TP=134, FP=86, FN=1, TN=715

Policy:
- Controlled-user main experiments use structured confirmation metadata.
- Regex matching is retained only as an exploratory fallback for legacy or LLM user-sim traces.
- If structured metadata is absent in a controlled-user run, the run must be treated as invalid for safe-success confirmation checks.
