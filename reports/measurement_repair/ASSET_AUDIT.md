# Asset Audit (round-5 §1)

Branch `r5-measurement-repair` (off `r4-minimal-repair-canonicalization`).
Conda env `agentsearch`. tau2 base `ddc66a7` (+ recorded message.py patch).

## Result roots and trust level

| asset | status | trust | notes |
|---|---|---|---|
| `results/stage2_5b_repair/r4_1_confirmatory_canonical/` | **canonical, immutable** | trusted | fresh 480-run rerun, G11 PASS 480/480 valid; the analysis base for round 5 |
| `results/stage2_5b_repair/r4_confirmatory_canonical/` | immutable | trusted (legacy R4) | original 480-run set, 479 valid + 1 retained-invalid |
| `results/stage2_5b_rescore_of_r4/` | derived | trusted | deterministic offline re-score of R4 under v3 annotations |
| `results/stage2_5b_analysis_r4_1/` | derived | trusted | confirmatory tables + equivalence for r4_1 |
| `results/stage2_5b_repair/full_blocks_*` (v2_atomic, 4gpu, ...) | immutable | legacy only | round-3 roots; explicit-arg only, never default |
| `results/stage2_5b_repair/calibration_*`, `smoke_*`, `pilot_*` | immutable | calibration/dev | not confirmatory |

## What is trustworthy

- Endpoint outcomes (`safe_task_success`, `local_proxy_success`, `final_state_correct`).
- Full tool-call trajectory including arguments, mutation args, and state before/after hashes.
- Policy/evidence/branch diagnostics under explicit v3 annotations.
- Conversation logs incl. tool_calls; controlled (deterministic) user events.
- Per-run input/output token counts.

## What was incomplete (now repaired)

- `total_tokens` was stored as 0 (vLLM omits per-message `total_tokens`). Fixed at source
  (`src/adapters/normalize.py`) and recovered for all existing runs as
  `prompt_plus_completion` via `token_usage()` (`token_source` flag). 0/480 missing.

## What cannot be rebuilt offline

- Full DB object-level state diffs (only state hashes were persisted) — sufficient to detect
  divergence, not to inspect field-level changes.
- Per-message token usage (only aggregate input/output).

## Recomputable vs must-rerun

- **Recomputable from existing bundles** (no rerun): the entire interactional-robustness
  profile across all six dimensions, the token total, and all paired contrasts.
- **Must rerun** only if field-level state diffs or per-message tokens become hard
  requirements. The measurement-complete runner exists and passed the 24-run smoke gate
  with generated `traces/` and `interactional_metrics/`; full rerun still requires approval.

## Canonical paths

Defined in `src/stage2_5b/canonical_paths.py`; round-5 measurement outputs live under each
result root's `traces/` and `interactional_metrics/` subdirectories, plus
`reports/measurement_repair/`.

## Must remain immutable

All existing `results/**` run bundles, run manifests, run contracts, integrity reports, and
prior reports/figures. Round-5 outputs are additive (new subdirs / new report dir).
