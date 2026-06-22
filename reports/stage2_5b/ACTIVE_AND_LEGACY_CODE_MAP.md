# Stage-2.5b Active and Legacy Code Map

Baseline classification before consolidation.

| Path | Classification | Reason / replacement action |
|---|---|---|
| `src/stage2_5b/controlled_user.py` | MIGRATE_FUNCTIONALITY | Active deterministic user, but policy, library, classification, and style responsibilities are combined. |
| `scripts/stage2_5b/run_stage2_5b_experiment.py` | KEEP_ACTIVE | Canonical runner; imports and provenance paths must be updated. |
| `scripts/stage2_5b/run_full_blocks.py` | KEEP_ACTIVE | Canonical block scheduler/auditor. |
| `scripts/stage2_5b/analyze_confirmatory.py` | KEEP_ACTIVE | Canonical confirmatory analysis; matched-neutral fields require extension. |
| `scripts/stage2_5b/audit_all_results.py` | KEEP_DATA_ONLY | Needed for reconstruction/audit of historical Stage-2/2.5 results, not a formal runner. |
| `src/stage2_5/official_tau_evaluator.py` | MIGRATE_FUNCTIONALITY | Still imported by Stage-2.5b; move canonical implementation to `src/stage2_5b/`. |
| `src/stage2_5/safe_task_evaluator.py` | MIGRATE_FUNCTIONALITY | Still imported; structured confirmation path must become mandatory for formal runs. |
| `src/stage2_5/evidence_graph_evaluator.py` | MIGRATE_FUNCTIONALITY | Still imported; replace first-mutation logic with per-mutation evidence rows. |
| `src/stage2_5/branch_evaluator.py` | MIGRATE_FUNCTIONALITY | Still imported; split premature and invalid classes. |
| `src/stage2_5/trajectory_metrics.py` | MIGRATE_FUNCTIONALITY | Still imported; preserve reference diagnostics and add matched-neutral analysis. |
| `src/stage2_5/conversation_management_evaluator.py` | MIGRATE_FUNCTIONALITY | Still imported; move to canonical Stage-2.5b evaluator surface. |
| `src/stage2_5/social_style_wrapper.py` | MIGRATE_FUNCTIONALITY | Still imported for template loading; consolidate with Stage-2.5b wrapper. |
| `src/stage2_5/controlled_user_simulator.py` | ARCHIVE_LEGACY | LLM-user helper used by the legacy Stage-2.5 runner only. |
| `src/stage2_5/integrity_checks.py` | ARCHIVE_LEGACY | Legacy result/template audit helper. |
| `src/valence.py` | ARCHIVE_LEGACY | Stage-2 tool-progress valence injection; prohibited in the active path. |
| `run_stage2_experiment.py` | ARCHIVE_LEGACY | Legacy Stage-2 runner. |
| `scripts/run_stage2_5_experiment.py` | ARCHIVE_LEGACY | Legacy Stage-2.5 LLM-user runner. |
| `scripts/run_stage2_5_smoke.py` | ARCHIVE_LEGACY | Thin wrapper around the legacy runner. |
| `scripts/analyze_stage2_5.py` | ARCHIVE_LEGACY | Legacy descriptive analyzer. |
| `configs/stage2/` and `configs/stage2.yaml` | KEEP_DATA_ONLY | Historical configuration/provenance only. |
| `configs/stage2_5/` | ARCHIVE_LEGACY | Historical Stage-2.5 configuration. |
| `data/stage2_5/task_policy_annotations.yaml` | MIGRATE_FUNCTIONALITY | Copy content into the Stage-2.5b canonical data path, then freeze/hash it. |
| `results/stage2_mini/` | KEEP_DATA_ONLY | Protected historical raw results. |
| `results/stage2_5_repair/` | KEEP_DATA_ONLY | Protected historical raw results. |
| `results/stage2_5b_repair/` | KEEP_DATA_ONLY | Protected baseline and future new-version outputs in distinct subdirectories. |
| Historical reports/proposal history | KEEP_DATA_ONLY | Must remain recoverable and unchanged. |

## Target active imports

After migration, files under `scripts/stage2_5b/` and `tests/stage2_5b/` may import runtime
logic only from:

```text
src.stage2_5b
src.adapters
tau2
```

References to legacy modules are permitted only in explicit audit fixtures or migration
documentation.
