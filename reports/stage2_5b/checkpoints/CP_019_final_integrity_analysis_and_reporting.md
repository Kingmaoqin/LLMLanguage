# Checkpoint CP-019

## Goal

Complete the 480-run confirmatory matrix, pass G11, execute the frozen primary analysis,
correct any result-stage metric-semantics issue, and produce the final reports and proposal
revision.

## Files Inspected

- `results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic/`
- all 16 block reports and logs
- all 480 manifests, metrics, atomic bundles, and terminal/process aggregate files
- `reports/stage2_5b/PREANALYSIS_PLAN.md`
- `results/stage2_5b_analysis/*`
- `reports/stage2_5b/FAILURE_CASES.md`
- `reports/stage2_5b/INDEPENDENT_RESULTS_REVIEW.md`
- legacy Stage-2 and Stage-2.5 reports
- `/home/xqin5/llmlanguage/proposal_tact(1).md`

## Files Changed

- `scripts/stage2_5b/final_integrity_audit.py`
- `scripts/stage2_5b/analyze_confirmatory.py`
- `scripts/stage2_5b/task_cluster_bootstrap.py`
- `scripts/stage2_5b/equivalence_analysis.py`
- `scripts/stage2_5b/run_glmm.R`
- `scripts/stage2_5b/extract_failure_cases.py`
- final Stage-2.5b reports, review, reproduction guide, and proposal artifacts

## Evidence Before Change

- The formal run initially stopped at 420/480 because the final task had not started.
- No final G11 audit, confirmatory result table, failure-case report, reproduction guide, or
  evidence-aligned proposal revision existed.
- The preanalysis plan required task-cluster bootstrap, equivalence testing, correct paired
  baselines, invalid-run retention, process analysis, and task/model diagnostics.
- The first result pass revealed that `user_abandonment_markers` was user-side and mostly
  captured normal controlled-user STOP messages, not agent task abandonment.

## Implementation

- Resumed and completed both retail_28 blocks; all 16 blocks now PASS.
- Added a global audit of manifests, metrics, bundles, contracts, hashes, deployments,
  termination/parser/final-state coverage, orphan events, balance, initial states, and
  controlled-user openings.
- Implemented 10,000-replicate task-cluster paired bootstrap with BH-FDR.
- Added prespecified equivalence classification and matched-neutral direct trajectory
  distances adjusted by repeated-exposure noise floor.
- Added endpoint, process, per-model, per-task, invalid-rate, and figure source tables.
- Added a secondary R GLMM entry point; recorded that R/lme4 is unavailable.
- Corrected abandonment semantics by leaving agent-side abandonment missing rather than using
  user STOP markers.
- Generated matched failure/mechanism cases, final Chinese report, reproduction guide,
  independent-results-review Part 2, revised proposal artifact, and proposal changelog.

## Tests Executed

```bash
python -m py_compile scripts/stage2_5b/*.py src/stage2_5b/*.py tests/stage2_5b/*.py
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch python scripts/stage2_5b/run_full_blocks.py \
  --workers 4 \
  --gemma-base-urls http://127.0.0.1:8005/v1 http://127.0.0.1:8006/v1
python scripts/stage2_5b/final_integrity_audit.py
python scripts/stage2_5b/analyze_confirmatory.py
python scripts/stage2_5b/equivalence_analysis.py
python scripts/stage2_5b/extract_failure_cases.py
```

## Test Results

- Stage-2.5b unit tests: 46/46 PASS.
- Block reports: 16/16 PASS.
- G11: PASS.
- Runs: 480 expected, 480 metrics, 480 bundles, 479 valid, 1 retained invalid.
- Matched contrast rows: 400.
- Pooled endpoint FDR-significant cells: 0.
- Pooled endpoint equivalent cells: 0.
- Pooled process FDR-significant cells: 2.
- Equivalence table rows: 90; equivalent cells across pooled/per-model scopes: 17.
- GLMM: NOT FIT because Rscript/lme4 is unavailable; primary bootstrap completed.

## Artifact Inspection

- No duplicate, missing, orphan, mixed-hash, initial-state-drift, or controlled-user-drift
  finding remains.
- One context-window invalid run is retained in all integrity denominators.
- Praise-affect increases tool calls by 0.525, CI [0.250, 0.800], adjusted p=0.0172.
- Repeated abuse changes diagnostic critical-argument reference distance by -0.0363,
  CI [-0.0542, -0.0182], adjusted p=0.0172.
- No endpoint contrast is multiplicity-corrected significant or equivalent within ±10pp.
- Failure cases include matched traces, state hashes, evaluator deltas, and neutral exposure
  noise floors.
- Agent task abandonment remains not identifiable; user STOP is not used as a proxy.

## Reviewer Verdict

PASS WITH CLAIM RESTRICTIONS.

## Reviewer Concerns

- Retail-only, two-model scope.
- Eight task clusters yield wide endpoint CIs.
- Complete official NL assertion success is unavailable.
- Final/local endpoints are missing for 37 valid MAX_STEPS runs.
- R/lme4 and a new independent result-review subagent were unavailable.
- Template semantic ratings lack a three-judge panel.

## Resolution

- Final claims are limited to no reliable endpoint effect detected, no established endpoint
  equivalence, selective process differences, and task/model heterogeneity.
- No global robustness, over-compliance, over-refusal, abuse benefit, or cross-domain claim is
  made.
- All limitations are recorded in the final report, results review, proposal revision, and
  reproduction guide.

## Final Gate Decision

G11_FINAL_INTEGRITY_PASS. CONFIRMATORY ANALYSIS COMPLETE. FINAL VERDICT:
PASS WITH CLAIM RESTRICTIONS.

## Next Allowed Step

Only post-confirmatory expansion: more task clusters, a non-retail non-floor domain,
additional preflighted model families, complete official text-component evaluation, and
human-validated conversation-management labels.
