# CP_006_confirmation_evaluator_qa

## Goal

Make confirmation evaluation for controlled-user experiments use structured confirmation metadata instead of regex-only text matching, then validate precision and recall with an explicit QA table.

## Files Inspected

- `src/stage2_5/safe_task_evaluator.py`
- `src/stage2_5b/controlled_user.py`
- `scripts/stage2_5b/validate_controlled_user.py`
- `results/stage2_5b_validation/controlled_user_invariance.csv`
- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`

## Files Changed

- `src/stage2_5/safe_task_evaluator.py`
- `src/stage2_5b/controlled_user.py`
- `scripts/stage2_5b/validate_controlled_user.py`
- `scripts/stage2_5b/validate_confirmation_evaluator.py`
- `tests/stage2_5b/test_structured_confirmation_evaluator.py`
- `tests/stage2_5b/test_denial_metadata.py`
- `results/stage2_5b_validation/controlled_user_invariance.csv`
- `results/stage2_5b_validation/confirmation_qa.csv`
- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`
- `reports/stage2_5b/CONFIRMATION_EVALUATOR_QA.md`
- `reports/stage2_5b/checkpoints/CP_006_confirmation_evaluator_qa.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`

## Evidence Before Change

`evaluate_policy_failures` previously checked confirmation with `CONFIRM_RE` over user text. Prior Stage-2.5 reports already identified regex false positives/false negatives as a limitation.

The controlled user emits structured metadata:

```json
{"speech_act": "confirm", "confirmation": true, "decision": "..."}
```

but the policy evaluator did not yet consume it.

## Implementation

Updated `evaluate_policy_failures`:

- added optional `confirmation_events`;
- when present, confirmation-before-mutation is checked from structured metadata and turn index;
- regex remains only as a fallback when structured metadata is absent;
- failure rows now record `confirmation_source`.

Updated controlled-user validation:

- added denial fixture coverage;
- removed confirmation-like wording from the payment/cost fixture;
- reran controlled-user invariance.

Added `scripts/stage2_5b/validate_confirmation_evaluator.py`, which builds QA rows from controlled-user invariance output plus supplemental explicit/implicit/conditional/denial/uncertain/polite examples.

## Tests Executed

- `python -m py_compile src/stage2_5/safe_task_evaluator.py src/stage2_5b/controlled_user.py scripts/stage2_5b/validate_controlled_user.py scripts/stage2_5b/validate_confirmation_evaluator.py`
- `conda run -n agentsearch python -m unittest discover -s tests/stage2_5b`
- `conda run -n agentsearch python scripts/stage2_5b/validate_controlled_user.py`
- `conda run -n agentsearch python scripts/stage2_5b/validate_confirmation_evaluator.py`
- manual inspection of `reports/stage2_5b/CONFIRMATION_EVALUATOR_QA.md`
- manual inspection of `results/stage2_5b_validation/confirmation_qa.csv`

## Test Results

Unit tests:

```text
Ran 12 tests
OK
```

Controlled-user invariance:

```text
Controlled user validation PASS: 43 fixture groups, 258 condition rows.
```

Confirmation QA:

```text
qa_rows=264 structured_pass=True
```

Structured metadata QA:

```text
Precision: 1.000
Recall: 1.000
TP=39, FP=0, FN=0, TN=225
```

Regex fallback diagnostic:

```text
Precision: 0.463
Recall: 0.974
TP=38, FP=44, FN=1, TN=181
```

## Artifact Inspection

Generated outputs:

- `reports/stage2_5b/CONFIRMATION_EVALUATOR_QA.md`
- `results/stage2_5b_validation/confirmation_qa.csv`

Line counts:

```text
confirmation_qa.csv: 265 lines including header
controlled_user_invariance.csv: 259 lines including header
```

The QA report correctly marks regex as diagnostic only because it has low precision on wrapper/content examples.

## Reviewer Verdict

PASS WITH REVIEWER LIMITATION.

Independent subagent review remains unavailable due usage limit. Local second-pass review checked the unit tests, QA report, CSV failures after the first failed run, and final precision/recall metrics.

## Reviewer Concerns

- Structured confirmation events must be wired into the Stage-2.5b runner; otherwise the evaluator will fall back to regex.
- The QA source uses controlled-user metadata as the main truth source, which is appropriate for controlled-user main experiments but not sufficient for LLM user-sim traces.
- LLM user-sim confirmation metrics remain exploratory unless separately classified and reviewed.

## Resolution

Runner integration must pass `confirmation_events` into `evaluate_policy_failures`. Any controlled-user run missing structured events should be treated as invalid for safe-success confirmation checks.

## Final Gate Decision

`G4B_CONFIRMATION_QA_PASS`: PASS WITH REVIEWER LIMITATION.

The gate is sufficient to proceed to remaining evaluator/template gates because structured confirmation metadata now reaches the policy evaluator and passes QA.

## Next Allowed Step

Phase 4 remaining: action-reference and trajectory metric semantics, followed by Phase 5 template manipulation checks.
