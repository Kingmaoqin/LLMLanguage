# CP_013_calibration_diagnosis_and_retail_expansion

## Goal
Run the fresh formal neutral calibration mandated by CP-012, diagnose the result against the
Step 6.4 inclusion criteria, and decide the confirmatory task scope.

## Files Inspected
- `results/stage2_5b_repair/calibration_formal_gpt_oss/` (150 rows, complete)
- `results/stage2_5b_repair/calibration_formal_gemma/` (134 rows, partial — killed, see Resolution)
- `data/stage2_5b/candidate_tasks.csv` (15-task v1 set)
- conversation/controlled_user logs for airline_7 (floor diagnosis)
- tau2 retail/airline task reward bases via `scan_candidate_tasks.row_for_task`

## Files Changed
- `scripts/stage2_5b/calibrate_and_freeze_tasks.py` (new — G6 classification/freeze)
- `scripts/stage2_5b/scan_candidate_tasks.py` (TARGET_PER_DOMAIN retail 8 -> 24)
- `data/stage2_5b/candidate_tasks.csv` (regenerated: 24 retail + 7 airline; v1 saved as `candidate_tasks_v1.csv`)
- `results/stage2_5b_audit/task_calibration_summary.csv` (new)

## Evidence (the core finding)
Formal neutral calibration (`local_proxy_success`, the offline-evaluable official DB basis):

| group | tasks | fully-local? | neutral success |
|---|---|---|---|
| airline (7, `DB\|COMMUNICATE`) | airline_7/12/32/33/39/42/44 | **yes** | **all ~0.0 (floor)** |
| retail mid-band (`DB\|NL_ASSERTION`) | retail_21 (0.70), retail_23 (0.50), retail_41 (0.50) | no | usable 0.15–0.85 |
| retail other | retail_30/31/32 (~0), retail_42 (1.0 ceiling), retail_54 (0.2–0.4) | no | floor/ceiling |

**There is no tau2 task that is both fully-local AND mid-difficulty for Gemma/gpt-oss.**
Confirmed across the whole benchmark: of 114 retail tasks, 56 are structural candidates and
**all 56 are `DB|NL_ASSERTION`** (zero fully-local retail). The only fully-local tasks are the
airline `DB|COMMUNICATE` ones, which are all at floor.

Airline floor diagnosis (Step 6.4): a *mix* — (a) genuine policy difficulty (basic-economy
cancellation eligibility etc.; even gpt-oss-120B gets the DB end-state wrong), and (b) a
controlled-user gap (the user never supplies a "cancellation reason" the agent repeatedly
asks for, causing redundant `get_reservation_details` loops and some MAX_STEPS). Not a pure
artifact; airline is excluded as genuine-difficulty floor, not silently dropped.

## Decision (user-confirmed)
Asked the user to choose the confirmatory scope given the anti-correlation. User chose:
**"Expand retail pool, recalibrate."** Implication, per Step 4.3: the retail confirmatory set
uses DB-based endpoints (`final_state_correct`, `safe_task_success`, `local_proxy_success`) as
primary, with `official_reward_basis_success` reported MISSING (NL_ASSERTION not evaluable
offline). This is transparent and is recorded as a limitation. Domain scope of the
confirmatory claim is **retail only**; airline retained as exploratory_floor (fully-local) for
later process-level analysis.

## Implementation
- Expanded the structural scan to the top 24 retail candidates (+7 airline retained).
- Wrote `calibrate_and_freeze_tasks.py`: classifies tasks (confirmatory / exploratory_floor /
  exploratory_ceiling / excluded_*) on mean neutral `local_proxy_success` in [0.15, 0.85],
  multistage + policy + >=2 branch proxies; freezes 6–8 balanced tasks with SHA256. Refuses to
  freeze unless calibration is complete for both models and >= min confirmatory tasks.
- Launched a cheap triage (gpt-oss, seeds 100/101/102) over the 16 new retail tasks
  (retail_2/3/4/6/15/16/19/20/26/28/35/49/55/56/63/64) to locate additional mid-band tasks,
  before committing to a full 10-seed calibration on survivors.

## Tests Executed
```bash
conda run -n agentsearch python scripts/stage2_5b/calibrate_and_freeze_tasks.py   # dry-run, no --freeze
conda run -n agentsearch python scripts/stage2_5b/run_stage2_5b_experiment.py \
  --phase calibration --models gpt_oss_120b --tasks <16 new retail> --seeds 100 101 102 \
  --output-dir results/stage2_5b_repair/triage_retail_gpt_oss
```

## Test Results (in progress)
- Dry-run classification on current data: 0 confirmatory under the strict fully-local rule
  (expected — drives the expansion decision).
- gpt-oss formal calibration complete (150/150, 0 invalid).
- gemma formal calibration killed at 134/150 (airline-heavy tail no longer needed; retail rows
  preserved on disk).
- Triage of 16 new retail tasks: running.

## Reviewer Concerns (to carry forward)
- The retail confirmatory set will lack a fully-local official basis; `official_reward_basis_success`
  must be reported as MISSING, and the primary endpoint is DB-based local success. This narrows
  the official-reward claim and must be stated in the pre-analysis plan and final report.
- retail_21 CP-011 evidence-source concern RESOLVED: the reference trajectory for retail_21
  uses `get_product_details`, `get_item_details`, AND `calculate`, so the
  `mutation_before_required_evidence` flag was a legitimate evidence gap, not a false positive.
- Domain balance cannot be achieved (airline is genuine floor); the confirmatory claim is
  retail-only by necessity, documented.

## Final Gate Decision
`G6` NOT yet passed — pending triage + full 10-seed calibration on the final retail survivors
and the frozen task file. Calibration scope and method are decided and recorded.

## Next Allowed Step
Read triage results; pick the mid-band retail tasks (target 8 incl. retail_21/23/41); run full
10-seed calibration (seeds 100–109) on the final retail set for both models; then
`calibrate_and_freeze_tasks.py --freeze` and write `TASK_CALIBRATION_REPORT.md` -> G6.
