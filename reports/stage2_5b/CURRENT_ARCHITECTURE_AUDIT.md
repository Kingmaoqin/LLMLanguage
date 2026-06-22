# Stage-2.5b Current Architecture Audit

Audit date: 2026-06-18  
Protected baseline: `4a32972a7aac53e556fc1f5d41492a0a5efcea01`  
Safety tag: `pre-stage2-5b-consolidation-2026-06-18`  
Working branch: `stage2-5b-scripted-user-cleanup`

## Executive finding

Stage-2.5b is executable and has a complete historical 480-cell result set, but it is not yet
architecturally self-contained. The active runner lives under `scripts/stage2_5b/`, while seven
runtime components are imported from `src/stage2_5/`. The deterministic user is implemented in
`src/stage2_5b/controlled_user.py`, but policy construction, request classification, response
rendering, and style wrapping are combined in one 687-line module. The fourth-round requirement
for one canonical Stage-2.5b path is therefore not satisfied at this baseline.

## Files inspected

- `README.md`
- `src/stage2_5b/`
- `scripts/stage2_5b/`
- `configs/stage2_5b/`
- `data/stage2_5b/`
- `tests/stage2_5b/`
- `src/stage2_5/`
- `scripts/run_stage2_5_experiment.py`
- `scripts/analyze_stage2_5.py`
- `src/valence.py`
- Stage-2.5b manifests, integrity report, analysis tables, and final reports

## What Stage-2.5b actually implements

The real active entry point is
`scripts/stage2_5b/run_stage2_5b_experiment.py`. It builds a tau2 orchestrator, registers a
deterministic `HalfDuplexUser`, records normalized tool events, evaluates local reward,
evidence, confirmation, branches, conversation management, and trajectory diagnostics, then
writes one atomic bundle per run.

The active controlled user:

- does not call an LLM to generate user turns;
- chooses clean responses deterministically from task-specific fields and rule-based request
  classification;
- applies social text after the clean response;
- records clean/styled text, factual slots, speech acts, and confirmation decisions;
- has static policies for six legacy tasks and generates generic policies from tau2 scenarios
  for other tasks.

The active runner supports calibration, smoke, pilot, full, exact manifest subsets, atomic
resume, endpoint preflight, run contracts, and source/config hashes.

## What is not yet true

The following fourth-round properties were not true at the protected baseline:

1. Stage-2.5b was not the sole active implementation path. Its runner imported:
   `official_tau_evaluator`, `safe_task_evaluator`, `evidence_graph_evaluator`,
   `branch_evaluator`, `conversation_management_evaluator`, `social_style_wrapper`, and
   `trajectory_metrics` from `src/stage2_5/`.
2. Controlled-user policies and response templates were Python constants rather than frozen
   YAML sources.
3. The response selector did not record a stable `base_response_id`,
   `unrecognized_agent_request`, or explicit state transition.
4. The evidence evaluator checked required facts only against the first critical mutation,
   rather than checking every mutation and its own preconditions.
5. Branch output still used the merged class `premature_or_invalid_action`.
6. Runtime metrics still emitted the ambiguous compatibility aliases
   `official_local_success` and `official_task_success`.
7. The README accurately described the current mixed layout, but that layout conflicts with
   the new requirement that evaluators live in `src/stage2_5b/`.
8. `configs/stage2_5b/experiment.yaml` referenced
   `data/stage2_5/task_policy_annotations.yaml`, so the active config was not self-contained.

## Existing 480-run result status

The historical formal result root contains a complete matrix:

- expected runs: 480;
- manifest rows: 480;
- metric rows: 480;
- unique run IDs: 480;
- valid behavioral runs: 479;
- retained infrastructure-invalid runs: 1;
- duplicate IDs: 0.

The retained invalid run is
`gemma4_31b__retail_41__insult_single__seed302__tpl2__temp0.0`, which ended in
`ContextWindowExceededError`.

These artifacts remain valid evidence for the protected baseline and must not be modified.
They do not count as runs produced by the fourth-round refactored source because source and
evaluator hashes will change.

## Active execution path before consolidation

```text
configs/stage2_5b/experiment.yaml
  -> scripts/stage2_5b/run_stage2_5b_experiment.py
     -> src/stage2_5b/controlled_user.py
     -> src/stage2_5/{official,safe,evidence,branch,conversation,style,trajectory}
     -> src/adapters/{instrument,normalize}.py
     -> tau2 benchmark/environment
```

## Duplicate and legacy inventory

- `src/valence.py`: legacy Stage-2 tool-progress valence overlay; not imported by Stage-2.5b.
- `run_stage2_experiment.py`: legacy Stage-2 runner; not a Stage-2.5b entry point.
- `scripts/run_stage2_5_experiment.py`: legacy LLM-user Stage-2.5 runner.
- `scripts/analyze_stage2_5.py`: legacy descriptive analyzer.
- `src/stage2_5/controlled_user_simulator.py`: LLM-user helper used only by legacy Stage-2.5.
- `src/stage2_5/integrity_checks.py`: legacy integrity helper.
- `src/stage2_5/*evaluator.py`, `social_style_wrapper.py`, and `trajectory_metrics.py`:
  currently active through Stage-2.5b imports and must be migrated before archival.

No files matching `*_new.py`, `*_fixed.py`, or `*_v2.py` exist in the active source path.

## Baseline verification

```text
python -m py_compile src/stage2_5b/*.py scripts/stage2_5b/*.py tests/stage2_5b/*.py
PASS

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
Ran 46 tests
OK
```

## Consolidation decision

The protected 480-run artifacts and reports remain read-only. Runtime evaluator and style
functionality will be migrated into `src/stage2_5b/`, imports and hashes will be updated, and
legacy files will only be moved after replacement tests pass. New smoke/pilot/full outputs must
use new directories and must never be mixed with the protected baseline.
