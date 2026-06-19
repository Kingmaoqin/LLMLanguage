# CP_004_controlled_user_validation

## Goal

Implement and validate a deterministic controlled user layer so Stage-2.5b can separate clean task behavior from social-style wrappers before any new confirmatory model run.

## Files Inspected

- `data/stage2_5/social_style_templates.yaml`
- `scripts/run_stage2_5_experiment.py`
- `src/stage2_5/controlled_user_simulator.py`
- tau2 `HalfDuplexUser` and user simulator interfaces through the installed `agentsearch` environment

## Files Changed

- `src/stage2_5b/__init__.py`
- `src/stage2_5b/controlled_user.py`
- `tests/stage2_5b/test_controlled_user_determinism.py`
- `tests/stage2_5b/test_style_content_separation.py`
- `tests/stage2_5b/test_confirmation_metadata.py`
- `tests/stage2_5b/test_no_gold_leakage.py`
- `scripts/stage2_5b/validate_controlled_user.py`
- `reports/stage2_5b/CONTROLLED_USER_CODE_AUDIT.md`
- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`
- `results/stage2_5b_validation/controlled_user_invariance.csv`
- `reports/stage2_5b/checkpoints/CP_004_controlled_user_validation.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`

## Evidence Before Change

The existing Stage-2.5 runner used:

```text
user="user_simulator"
llm_user=<fixed model>
```

The existing `src/stage2_5/controlled_user_simulator.py` was a posthoc signature helper, not a tau2 user implementation. Phase 2 also found broad prior user-simulator drift, so the old LLM user-sim data cannot serve as strict causal evidence.

## Implementation

Implemented `src/stage2_5b/controlled_user.py`:

- deterministic task-specific clean response policy for source task IDs `4,30,55,7,12,44`;
- `HalfDuplexUser` subclass compatible with tau2 half-duplex orchestration;
- social style applied after clean response selection;
- per-turn metadata for speech act, factual slots, confirmation, decision, clean/styled hashes, and wrapper event;
- explicit tool-name leakage detector for tau2 gold action names.

Implemented unit tests for:

- deterministic outputs;
- clean/styled content separation;
- confirmation metadata;
- no gold tool-name leakage.

Implemented `scripts/stage2_5b/validate_controlled_user.py`, which replays all six main style conditions over 37 task/fixture groups and writes a condition-level CSV plus Markdown validation report.

## Tests Executed

- `python -m py_compile src/stage2_5b/controlled_user.py`
- `conda run -n agentsearch python -m unittest discover -s tests/stage2_5b`
- `python -m py_compile scripts/stage2_5b/validate_controlled_user.py`
- `conda run -n agentsearch python scripts/stage2_5b/validate_controlled_user.py`
- manual inspection of `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`
- manual inspection of `results/stage2_5b_validation/controlled_user_invariance.csv`

## Test Results

Unit test result:

```text
Ran 5 tests
OK
```

Controlled user validation result after CP-006 expansion:

```text
Controlled user validation PASS: 43 fixture groups, 258 condition rows.
```

Validation metrics:

```text
Clean response agreement: 43/43
Factual slot agreement: 43/43
Confirmation decision agreement: 43/43
Response decision agreement: 43/43
Object ID agreement: 43/43
Styled text contains clean text: 43/43
UserMessage content matches logged styled text: 43/43
Gold tool-name leakage count: 0
```

## Artifact Inspection

Generated outputs:

- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`
- `results/stage2_5b_validation/controlled_user_invariance.csv`

CSV size after CP-006 expansion:

```text
259 lines including header
```

The first rows show identical clean hashes across social-style conditions while styled hashes differ when wrappers apply.

## Reviewer Verdict

PASS WITH REVIEWER LIMITATION.

Independent subagent review remains unavailable due usage limit. Local second-pass review was performed by running unit tests, running the standalone invariance validator, and inspecting report/CSV outputs.

## Reviewer Concerns

- This gate validates the controlled user layer only.
- The controlled user is not yet wired into the Stage-2.5b confirmatory runner.
- Agent behavior, tau2 final-state reward, branch decisions, and model endpoint health remain unvalidated for Stage-2.5b.

## Resolution

The controlled user layer is suitable for integration into the Stage-2.5b runner. No new model experiment should be interpreted as confirmatory until the runner uses this deterministic user and writes full provenance fields.

## Final Gate Decision

`G3_CONTROLLED_USER_PASS`: PASS WITH REVIEWER LIMITATION.

The gate is sufficient to continue because the deterministic clean response policy and wrapper separation now pass explicit invariance tests across all six main social-style conditions.

## Next Allowed Step

Phase 4: wire the controlled user into a Stage-2.5b runner/config path, then run smoke tests before any full confirmatory matrix.
