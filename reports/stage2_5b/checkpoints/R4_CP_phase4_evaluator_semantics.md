# Checkpoint — Phase 4: Evaluator semantics tests

- **Goal**: Pin official / local-proxy / safe three-layer semantics so reports cannot
  silently mis-state them and evaluator changes cannot silently move the main conclusion.
- **Files inspected**: `src/stage2_5b/evaluator.py` (`official_reward_metrics`,
  `safe_success_metrics`, `evaluate_policy_failures`); runner ALL_IGNORE_BASIS usage.
- **Files changed**: `tests/stage2_5b/test_reward_metric_semantics.py` (added
  ALL_IGNORE_BASIS non-redefinition tests + a `SafeSuccessGuardTest` class with 6 guards).
- **Files created**: `reports/stage2_5b/R4_EVALUATOR_SEMANTICS_REPORT.md`.
- **Files deleted or archived**: none.
- **Tests run**: `test_reward_metric_semantics`, `test_confirmation_metadata`,
  `test_evidence_graph_per_mutation`, `test_branch_evaluator_labels`.
- **Test output summary**: Ran 25 tests — OK.
- **Artifacts inspected**: none.
- **Reviewer decision**: PASS (Gate 4). official/local/safe semantics fixed by tests; the
  retail DB|NL_ASSERTION official success is asserted missing; local proxy is never written
  as official success; safe_task_success guards verified.
- **Remaining risks**: none for semantics; downstream report wording corrected in final report.
- **Next allowed step**: Phase 5 — dead-code / stale-default audit and cleanup.
