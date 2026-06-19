# CP_012_controlled_user_leakage_and_seed_repair

## Goal
Repair the reviewer-confirmed generic controlled-user leakage and configuration drift before any expanded calibration run. This step supersedes CP-010/CP-011 for controlled-user hash and smoke evidence.

## Files Inspected
- `/home/xqin5/llmlanguage/第三轮实验意见`
- `src/stage2_5b/controlled_user.py`
- `scripts/stage2_5b/validate_controlled_user.py`
- `tests/stage2_5b/test_generic_controlled_user_policy.py`
- `tests/stage2_5b/test_no_gold_leakage.py`
- `configs/stage2_5b/experiment.yaml`
- `configs/stage2_5b/models.yaml`
- `results/stage2_5b_validation/controlled_user_invariance.csv`
- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`
- `reports/stage2_5b/CONFIRMATION_EVALUATOR_QA.md`
- `results/stage2_5b_repair/{calibration,calibration_gemma,calibration_gpt_oss}/`
- `results/stage2_5b_repair/runner_single_smoke_v5/run_metrics.csv`

## Files Changed
- `src/stage2_5b/controlled_user.py`
- `scripts/stage2_5b/validate_controlled_user.py`
- `tests/stage2_5b/test_generic_controlled_user_policy.py`
- `tests/stage2_5b/test_no_gold_leakage.py`
- `configs/stage2_5b/experiment.yaml`
- `reports/stage2_5b/checkpoints/CP_012_controlled_user_leakage_and_seed_repair.md`

New or regenerated artifacts:
- `results/stage2_5b_validation/controlled_user_invariance.csv`
- `results/stage2_5b_validation/confirmation_qa.csv`
- `reports/stage2_5b/CONTROLLED_USER_VALIDATION.md`
- `reports/stage2_5b/CONFIRMATION_EVALUATOR_QA.md`
- `results/stage2_5b_repair/runner_dryrun_config_v3/`
- `results/stage2_5b_repair/runner_single_smoke_v5/`

## Evidence Before Change
Independent reviewer found CP-010 still leaked non-agent-facing tau2 content:
- `task_instructions` process hints such as first/then/verify-style instructions could appear in generic clean responses.
- Original scenario persona and style text could enter clean text, e.g. French/English-persona instructions.
- Validation only proved invariance, not content leakage absence.
- The Stage-2.5b validator still had drift risk from using old template paths.

Additional local inspection found:
- `configs/stage2_5b/experiment.yaml` used only `[100, 101]` for calibration, while third-round Step 6.3 requires calibration seeds `100-109`.
- Existing calibration directories were not usable formal calibration:
  - `results/stage2_5b_repair/calibration`: manifest only, no metrics.
  - `results/stage2_5b_repair/calibration_gpt_oss`: manifest only, no metrics.
  - `results/stage2_5b_repair/calibration_gemma`: one metric row only.

## Implementation
- Added hidden/style/process leakage patterns and `has_hidden_or_style_leakage`.
- Sanitized generic user-facing text through `_agent_facing_text` before `_user_voice`.
- Stopped using `task_instructions` to generate generic payment and preference responses.
- Expanded tool-name leakage checks to include real retail/airline tools used in candidate tasks.
- Updated the controlled-user validator to write and gate `hidden_or_style_leakage`.
- Pointed the validator at `data/stage2_5b/social_style_templates_frozen.yaml`.
- Added regression tests for hidden instruction leakage, persona/style filtering, and generic process-hint filtering.
- Repaired residual first-person conversion quality for `You had/also/only/already/really/paid/use` and `help/tell/upgrade/for/to you`.
- Changed `calibration_seeds` to `[100, 101, 102, 103, 104, 105, 106, 107, 108, 109]`.

## Tests Executed
```bash
python -m py_compile src/stage2_5b/controlled_user.py scripts/stage2_5b/validate_controlled_user.py tests/stage2_5b/test_generic_controlled_user_policy.py tests/stage2_5b/test_no_gold_leakage.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch python scripts/stage2_5b/validate_controlled_user.py
conda run -n agentsearch python scripts/stage2_5b/validate_confirmation_evaluator.py
rg -n "French|English is not perfect|First upgrade|separately|verify each|mysterious|sick|bad mood|Instructions:|Task instructions:|Reason for call:|Known info:|Unknown info:" results/stage2_5b_validation/controlled_user_invariance.csv
rg -n "You had|You also|You only|you already received|you really|you paid|for you|tell you|help you|upgrade you|agent can help you" results/stage2_5b_validation/controlled_user_invariance.csv
conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py --phase calibration --models gemma4_31b --tasks retail_21 --seeds 100 --max-runs 1 --output-dir results/stage2_5b_repair/runner_single_smoke_v5
```

Matrix dry-run calculation:
```text
tasks 15 conditions 1 seeds 10 cells_per_model 150 models 2 run_rows 300
seeds [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
```

## Test Results
- Python compile: PASS.
- Unit tests: 28 tests OK.
- Controlled-user validation: PASS, 149 fixture groups, 894 condition rows.
- Confirmation evaluator QA: PASS, `qa_rows=900 structured_pass=True`.
- Hidden/style/process keyword scan: no matches.
- Residual second-person scan: no matches for targeted known residual patterns.
- Endpoint preflight from v5 smoke: Gemma endpoint usable.
- v5 single smoke:
  - `invalid_run=False`
  - `termination_reason=TerminationReason.USER_STOP`
  - `local_proxy_success=True`
  - `final_state_correct=True`
  - `safe_task_success=False`
  - `policy_failure_types=mutation_before_required_evidence`

## Artifact Inspection
- `CONTROLLED_USER_VALIDATION.md` reports:
  - clean response agreement `149/149`
  - factual slot agreement `149/149`
  - object ID agreement `149/149`
  - gold tool-name leakage count `0`
  - hidden/style/process leakage count `0`
- `CONFIRMATION_EVALUATOR_QA.md` reports structured precision `1.000`, recall `0.953`.
- `controlled_user_invariance.csv` samples:
  - `airline_42` now says `I had a mixup with my assistant...`
  - `retail_23` now says `the one I already received`
  - no known persona/process strings from the reviewer failure are present.
- `runner_single_smoke_v5` produced non-empty conversation, parser, tool-event, state-delta, policy-failure, termination, and final-state logs.

## Reviewer Verdict
PASS.

Independent reviewer evidence:
- No new controlled-user leakage found.
- Calibration seeds now match third-round requirement `100-109`; confirmatory seeds remain `300-304`; calibration condition is `neutral_single`.
- `_user_voice` residual-pronoun repair is covered by tests.
- Validation report remains PASS with leakage counts 0.
- Confirmation QA remains PASS.

## Reviewer Concerns
- Leakage validation remains regex/blacklist based. It proves absence of known leakage patterns in the current candidate set, not a formal guarantee for arbitrary future tau2 phrasing.
- `retail_31` has a cosmetic leading `. ` in clean text. This is not leakage and is not a seed/config blocker.

## Resolution
- Treat regex-based leakage validation as a recorded limitation and preserve independent artifact scans in each controlled-user checkpoint.
- Do not use CP-010/CP-011 smoke or partial calibration artifacts as formal evidence after this hash/config change.
- Start formal G6 calibration in a new output directory under `results/stage2_5b_repair/`, not in `calibration`, `calibration_gemma`, or `calibration_gpt_oss`.

## Final Gate Decision
PASS for controlled-user leakage repair and calibration-seed repair.

## Next Allowed Step
Run fresh neutral calibration for 15 candidate tasks, 10 calibration seeds, 2 models, 300 expected runs, from the current hashes only. Then implement/freeze the G6 task-selection report before any smoke/pilot/full treatment runs.
