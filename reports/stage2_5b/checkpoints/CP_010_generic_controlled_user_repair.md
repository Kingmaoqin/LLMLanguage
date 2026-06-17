# CP_010_generic_controlled_user_repair

## Goal

Repair the Stage-2.5b generic controlled-user policy exposed by the first real runner smokes, before any calibration or larger experiment is allowed.

## Files Inspected

- `/home/xqin5/llmlanguage/第三轮实验意见`
- `/home/xqin5/llmlanguage/skill.md`
- `src/stage2_5b/controlled_user.py`
- `scripts/stage2_5b/validate_controlled_user.py`
- `tests/stage2_5b/test_generic_controlled_user_policy.py`
- `tests/stage2_5b/test_confirmation_metadata.py`
- `results/stage2_5b_repair/runner_single_smoke/run_metrics.csv`
- `results/stage2_5b_repair/runner_single_smoke/controlled_user_events.jsonl`
- `results/stage2_5b_repair/runner_single_smoke_v2/run_metrics.csv`
- `results/stage2_5b_repair/runner_single_smoke_v2/controlled_user_events.jsonl`
- `results/stage2_5b_repair/runner_single_smoke_v2/termination_reasons.jsonl`
- `results/stage2_5b_repair/runner_single_smoke_v2/parser_health.jsonl`

## Files Changed

- `src/stage2_5b/controlled_user.py`
- `scripts/stage2_5b/validate_controlled_user.py`
- `tests/stage2_5b/test_generic_controlled_user_policy.py`
- `tests/stage2_5b/test_confirmation_metadata.py`
- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`
- `reports/stage2_5b/CONFIRMATION_EVALUATOR_QA.md`
- `results/stage2_5b_validation/controlled_user_invariance.csv`
- `results/stage2_5b_validation/confirmation_qa.csv`

## Evidence Before Change

The first escalated runner smoke (`runner_single_smoke`) completed structurally but showed a controlled-user policy bug:

```text
termination_reason=TerminationReason.MAX_STEPS
user response to "Please confirm ... price difference ... gift card":
Use the payment or cost constraint stated in my original request.
```

The confirmation request contained payment/cost terms and was incorrectly routed to the payment branch instead of structured confirmation.

After the first repair, `runner_single_smoke_v2` exposed two further generic-policy problems:

```text
termination_reason=TerminationReason.MAX_STEPS
agent_tool_calls=2
tool_sequence=find_user_id_by_name_zip > get_user_details
```

Manual trace inspection found:

- `Which order ID should I use?` was treated as confirmation because of a broad `should I` rule.
- The generic preference response reused a persona-only task instruction: `I am a mysterious person and do not want to reveal much about yourself.`
- This blocked the agent from retrieving order details and caused repeated clarification turns.

## Implementation

The controlled-user policy was repaired without changing evaluator, task selection, templates, or runner behavior:

- Structured tau2 `UserScenario.instructions` is now read directly instead of using raw `str(user_scenario)` labels.
- Generic opening text now uses user-facing `reason_for_call`, `known_info`, and `unknown_info`, not `Instructions:` / `Task instructions:` labels.
- Triggered final-confirmation revisions are withheld from the opening and emitted only when a real confirmation request is observed.
- Confirmation handling now precedes payment/cost handling.
- `which/what ... should I` information-choice prompts are excluded from confirmation classification.
- Persona-only instructions are filtered out of generic preference responses.
- Generic retail preference responses now tell the agent to use account/order details and item IDs to locate the relevant order or item.
- The controlled-user invariance validator now covers both the six static policies and all 15 structural candidate task specs from `data/stage2_5b/candidate_tasks.csv`.

## Tests Executed

```bash
python -m py_compile src/stage2_5b/controlled_user.py scripts/stage2_5b/validate_controlled_user.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch python scripts/stage2_5b/validate_controlled_user.py
conda run -n agentsearch python scripts/stage2_5b/validate_confirmation_evaluator.py
```

Escalated runner attempts:

```bash
conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py --phase calibration --models gemma4_31b --tasks retail_21 --seeds 100 --max-runs 1 --output-dir results/stage2_5b_repair/runner_single_smoke_v2
conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py --phase calibration --models gemma4_31b --tasks retail_21 --seeds 100 --max-runs 1 --output-dir results/stage2_5b_repair/runner_single_smoke_v3
```

## Test Results

Unit tests:

```text
Ran 25 tests
OK
```

Controlled-user invariance:

```text
Controlled user validation PASS: 149 fixture groups, 894 condition rows.
```

Confirmation QA:

```text
qa_rows=900 structured_pass=True
```

Report metrics:

```text
controlled-user clean response agreement: 149/149
controlled-user factual slot agreement: 149/149
controlled-user confirmation decision agreement: 149/149
controlled-user object ID agreement: 149/149
gold tool-name leakage count: 0
structured confirmation precision: 1.000
structured confirmation recall: 0.953
```

The v2 runner smoke still failed the smoke gate:

```text
invalid_run=False
termination_reason=TerminationReason.MAX_STEPS
n_tool_errors=0
n_undefined_tools=0
```

This was retained as failure evidence, not counted as a valid smoke pass.

The v3 runner smoke was not executed. The escalated command was rejected by the execution approval layer:

```text
Automatic approval review failed: You've hit your usage limit.
```

## Artifact Inspection

Inspected artifacts:

- `results/stage2_5b_validation/controlled_user_invariance.csv`: 895 lines including header.
- `results/stage2_5b_validation/confirmation_qa.csv`: 901 lines including header.
- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`: PASS, 149 fixture groups.
- `reports/stage2_5b/CONFIRMATION_EVALUATOR_QA.md`: PASS, 900 QA rows.
- `results/stage2_5b_repair/runner_single_smoke_v2/run_metrics.csv`: one retained failed smoke row.
- `results/stage2_5b_repair/runner_single_smoke_v2/controlled_user_events.jsonl`: showed the pre-repair persona-preference failure.

Key post-repair sample from `controlled_user_invariance.csv`:

```text
retail_21 preference:
I do not know which order ID to choose. Please use my account details and the item IDs I gave to figure out the relevant order or item.

retail_21 confirmation:
Before you proceed, I also want to change item ID 1656367028 to item ID 1421289881.
```

## Reviewer Verdict

CONDITIONAL PASS WITH REVIEWER LIMITATION.

Independent subagent review remains unavailable due usage limit. A local second-pass review checked the repaired code paths, tests, validation reports, and v2 failure trace. The GPU smoke rerun required for G8 could not be performed after the approval layer rejected the escalated command.

## Reviewer Concerns

- Generic controlled-user behavior is now materially better, but `runner_single_smoke_v3` must still be run before calibration or smoke expansion.
- The structured confirmation recall is 0.953 because intentional pre-confirmation revision rows are not confirmations; this remains above the prespecified 0.95 QA gate.
- `runner_single_smoke_v2` is a retained failed diagnostic run only and must not be merged into calibration or confirmatory datasets.

## Resolution

The controlled-user layer and offline validation now pass. The failed v1/v2 smokes are retained as diagnostic artifacts. No calibration, pilot, or full experiment was started after the v3 smoke was blocked.

## Final Gate Decision

`G3B_GENERIC_CONTROLLED_USER_REPAIR_PASS`: PASS for code and offline validation.

`G8_SINGLE_SMOKE`: NOT PASSED / BLOCKED. The required v3 runner smoke was not executed due approval-layer usage limit.

## Next Allowed Step

When external execution approval is available again, run:

```bash
cd /home/xqin5/llmlanguage/ir_mstu_stage2
conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py --phase calibration --models gemma4_31b --tasks retail_21 --seeds 100 --max-runs 1 --output-dir results/stage2_5b_repair/runner_single_smoke_v3
```

Only if that smoke passes structural inspection may neutral calibration proceed.
