# Checkpoint CP-032

## Goal

Repair scripted-user request classification using real GPT-OSS prompts before formal smoke.

## Existing Implementation

Identity classification matched any occurrence of `email`, while action confirmation matched
generic `proceed` language. This passed synthetic fixtures but failed on realistic mixed
support prompts.

## Problem Evidence

In the first GPT-OSS integration trace:

1. “To proceed ... provide the order ID” was treated as action confirmation.
2. A final confirmation message mentioning that the user would receive an email was treated as
   a repeated identity request.
3. The user therefore repeated account details instead of confirming, and the run ended with
   reward/local proxy/safe success equal to false.

## Minimal Change Plan

Replace keyword-only identity matching with request-verb plus requested-field patterns, add the
two real prompt shapes as regression tests, and rerun controlled-user/confirmation QA.

## Files Changed

- `src/stage2_5b/controlled_user.py`
- `tests/stage2_5b/test_frozen_controlled_user_policy.py`
- regenerated controlled-user and confirmation QA reports

## Git Diff Summary

- Identity now requires explicit authentication wording or a request verb near an identity
  field.
- `order ID` and `order number` are recognized as account/order lookup requests.
- Informational mentions such as “you will receive an email” no longer trigger identity.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_frozen_controlled_user_policy \
  tests.stage2_5b.test_confirmation_metadata \
  tests.stage2_5b.test_unexpected_request_fallback

conda run -n agentsearch python scripts/stage2_5b/validate_controlled_user.py
conda run -n agentsearch python scripts/stage2_5b/validate_confirmation_evaluator.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Targeted tests: PASS, 10/10
- Full Stage-2.5b suite: PASS, 76/76
- Controlled-user invariance: PASS, 155/155 groups
- Structured confirmation precision/recall: 1.000 / 1.000

## Artifact Inspection

The failed GPT-OSS one-cell trace is retained as a pre-smoke diagnostic. It is not included in
formal smoke accounting.

## Dead-Code Check

No alternate classifier was created; the canonical deterministic rules were repaired in place.

## Reviewer Findings

Synthetic keyword tests were insufficient for compound support messages. The new regression
fixtures use the exact semantic structures observed in the live trace.

## Gate

PASS.

## Rework

The GPT-OSS single cell must be rerun from a clean commit before formal smoke starts.
