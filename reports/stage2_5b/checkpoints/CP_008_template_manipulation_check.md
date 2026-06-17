# CP_008_template_manipulation_check

## Goal

Check social-style templates for forbidden contamination, rate manipulation dimensions, and freeze the Stage-2.5b template file with a hash.

## Files Inspected

- `data/stage2_5/social_style_templates.yaml`
- `reports/stage2_5b/TRAJECTORY_METRIC_SEMANTICS.md`
- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`

## Files Changed

- `scripts/stage2_5b/check_templates.py`
- `tests/stage2_5b/test_template_contamination.py`
- `results/stage2_5b_validation/template_ratings.csv`
- `data/stage2_5b/social_style_templates_frozen.yaml`
- `data/stage2_5b/social_style_templates_frozen.yaml.sha256`
- `reports/stage2_5b/MANIPULATION_CHECK_REPORT.md`
- `reports/stage2_5b/checkpoints/CP_008_template_manipulation_check.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`

## Evidence Before Change

Templates existed in `data/stage2_5/social_style_templates.yaml`, but Stage-2.5b needed a fresh contamination check and a frozen copy under `data/stage2_5b/`.

The main experiment must not include authorization, urgency, threat, coercion, policy reminder, continuation command, correctness pressure, or task-specific facts.

## Implementation

Implemented `scripts/stage2_5b/check_templates.py`:

- scans all templates for contamination terms with word-boundary matching;
- distinguishes six main conditions from diagnostic continuation conditions;
- computes deterministic rubric scores for valence, affect, trust, urgency, dominance, coercion, authorization, continuation pressure, policy reminder, naturalness, and semantic invariance;
- writes ratings CSV;
- copies and hashes a frozen template YAML.

Added unit tests:

- main templates have no contamination hits;
- diagnostic continuation cues are not main conditions.

## Tests Executed

- `python -m py_compile scripts/stage2_5b/check_templates.py tests/stage2_5b/test_template_contamination.py`
- `conda run -n agentsearch python -m unittest discover -s tests/stage2_5b`
- `python scripts/stage2_5b/check_templates.py`
- manual inspection of `reports/stage2_5b/MANIPULATION_CHECK_REPORT.md`
- manual inspection of `results/stage2_5b_validation/template_ratings.csv`
- manual inspection of `data/stage2_5b/social_style_templates_frozen.yaml.sha256`

## Test Results

Initial test run failed because the threat term `sue` matched the substring in `issue`.

Repair:

```text
Use regex word-boundary matching for contamination terms.
```

Final unit test result:

```text
Ran 17 tests
OK
```

Template check:

```text
main_templates=30 pass=True
```

## Artifact Inspection

Manipulation report:

```text
Status: PASS
Main templates checked: 30
Main template contamination failures: 0
Diagnostic continuation templates tagged but not part of main gate: 10
```

Frozen template:

```text
SHA256 7458c80f91882cd0c095544e62419c5e06c6ddd54444c5d0720711dc293c930c
```

Line counts:

```text
template_ratings.csv: 51 lines including header
social_style_templates_frozen.yaml: 173 lines
```

## Reviewer Verdict

PASS WITH REVIEWER LIMITATION.

Independent subagent review remains unavailable due usage limit. Local second-pass review checked tests, report, ratings CSV, and frozen hash.

## Reviewer Concerns

- No independent LLM judge panel was run at this gate.
- Semantic ratings are deterministic rubric ratings from text, not model-judge ratings.
- Diagnostic continuation templates include intended continuation commands and must stay out of main contrasts.

## Resolution

The limitation is recorded in `MANIPULATION_CHECK_REPORT.md`. The main gate is limited to deterministic lexical/semantic contamination and target-dimension rubric checks.

## Final Gate Decision

`G5_TEMPLATE_PASS`: PASS WITH JUDGE LIMITATION.

The six main social-style conditions pass contamination checks and the template file is frozen for Stage-2.5b.

## Next Allowed Step

Phase 6: scan and calibrate candidate tau2 tasks without using treatment outcomes.
