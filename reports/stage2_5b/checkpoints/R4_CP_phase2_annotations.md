# Checkpoint — Phase 2: Disable confirmatory generic-annotation fallback

- **Goal**: Every confirmatory task carries an explicit policy annotation; the confirmatory
  phase can never silently fall back to `_generic_annotation`.
- **Files inspected**: `run_stage2_5b_experiment.py` (`_annotation_for`, `_generic_annotation`,
  phase plumbing, argparse); evaluator/evidence/branch consumers of annotation keys;
  `candidate_tasks.csv` task goals + reference-action sequences for the 8 tasks;
  `IRREVERSIBLE_TOOLS`.
- **Files changed**:
  - `data/stage2_5b/task_policy_annotations.yaml`: version bumped to v3; added EXPLICIT
    annotations for all 8 confirmatory tasks (retail_2/6/19/21/23/28/41/64), authored from
    each tau2 task goal + reference workflow. retail_28 encodes the "do not cancel the whole
    pending order" policy via `prohibited_mutations: [cancel_pending_order]`.
  - `run_stage2_5b_experiment.py`: split `_explicit_annotation`; `_annotation_for` now takes
    `phase` + `allow_generic`. Confirmatory phases (`full`, `pilot`) HARD FAIL with the
    missing task_id if no explicit annotation; non-confirmatory phases require an explicit
    `--allow-generic-annotation` flag to use the fallback. Returned annotations are tagged
    `annotation_source = explicit|generic`. Added `--allow-generic-annotation` CLI flag.
- **Files created**: `tests/stage2_5b/test_confirmatory_annotations.py` (9 tests).
- **Files deleted or archived**: none.
- **Tests run**: `test_confirmatory_annotations` (9, OK); full `tests/stage2_5b` suite.
- **Test output summary**: full suite Ran 99 tests — OK (79 baseline + 11 path + 9 annotation).
- **Artifacts inspected**: annotation YAML parsed and validated (all 8 present, non-empty
  facts/mutations, mutation tools ∈ IRREVERSIBLE_TOOLS).
- **Reviewer decision**: PASS (Gate 2). Confirmatory tasks 100% explicit; generic fallback
  cannot enter the formal pipeline.
- **Remaining risks / important**: The stored R4 results were generated *before* these
  explicit annotations existed (they used `_generic_annotation`). Because `safe_task_success`
  depends on policy failures (evidence-before-mutation, confirmation, prohibited mutation),
  the explicit annotations can change diagnostic metrics and possibly `safe_task_success`.
  By Section 13.2 this is a trigger for a **full rerun into fresh `r4_1_*` roots** — to be
  decided in Phase 7/8 (and gated on live model-server availability). Endpoint
  `local_proxy_success` (DB component) is unaffected by annotation.
- **Next allowed step**: Phase 3 — externalize the tau2 benchmark dirty patch + provenance tests.
