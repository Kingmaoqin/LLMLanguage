# Checkpoint CP-033

## Goal

Audit and analyze the post-CP-032 confirmatory runs, repair audit compatibility, and replace
the obsolete pre-repair final report.

## Existing Implementation

The repository contained a 480-run report generated on 2026-06-18 and two flat 240-run roots
generated on 2026-06-20/21. The older report predates benchmark refreeze, mutation-boundary,
and real-prompt controlled-user repairs.

## Problem Evidence

- Old formal results were bound to code before commits `14ab414`, `d028058`, and `ed800bc`.
- Current controlled-user openings use `user_event_idx=0`; audits only recognized legacy
  `user_state=turn_0`.
- The analysis helper accepted only aggregated contrast tables but gave an opaque `KeyError`
  when passed raw matched pairs.
- Provider usage omitted `total_tokens`, leaving that raw field at zero despite non-zero
  prompt/completion token counts.
- The old report described 479 valid runs and obsolete effect estimates.

## Minimal Change Plan

Preserve the hashed runtime implementation, add schema-compatible audit logic, assemble the
existing immutable post-repair bundles into the canonical layout, rerun all audits and
statistics, and replace only the result interpretation.

## Files Changed

- `scripts/stage2_5b/run_full_blocks.py`
- `scripts/stage2_5b/final_integrity_audit.py`
- `scripts/stage2_5b/assemble_confirmatory_roots.py`
- `scripts/stage2_5b/analyze_confirmatory.py`
- `scripts/stage2_5b/equivalence_analysis.py`
- Stage-2.5b tests, proposal, audit reports, and final report

## Git Diff Summary

- Added current/legacy opening-event compatibility.
- Added controlled-user/conversation, non-empty model-output, and token evidence checks.
- Added deterministic flat-root to canonical-block assembly.
- Added leave-one-task-out direction sensitivity for pooled FDR-significant cells.
- Added explicit equivalence input schema errors.
- Replaced obsolete result claims with post-repair estimates and multi-agent scope correction.

## Tests

```text
conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
conda run -n agentsearch python -m py_compile scripts/stage2_5b/*.py src/stage2_5b/*.py tests/stage2_5b/*.py
conda run -n agentsearch ruff check scripts/stage2_5b src/stage2_5b tests/stage2_5b
conda run -n agentsearch python scripts/stage2_5b/final_integrity_audit.py ...
python scripts/stage2_5b/analyze_confirmatory.py ...
```

## Results

- Unit tests: 79/79 PASS.
- Ruff static checks: PASS.
- Runtime hashes: exact match to both source run contracts.
- Integrity: 480 expected, 480 valid, 0 invalid.
- Pairing: 400/400 planned contrast rows.
- Unique atomic bundle hashes: 480/480.

## Artifact Inspection

The canonical root contains 16 balanced model/task blocks. Bundles contain 7,467 non-empty
assistant messages and non-zero prompt/completion token evidence. All six pooled
FDR-significant cells preserve direction under deletion of any one task.

## Dead-Code Check

No second runner, controlled user, evaluator, or analysis path was created. The assembly tool
only reorganizes immutable bundles for the existing canonical audit/analysis interface.

## Reviewer Findings

Independent read-only review was requested against the post-repair roots. Its final verdict is
recorded in `reports/stage2_5b/INDEPENDENT_RESULTS_REVIEW.md`.

## Gate

PASS WITH CLAIM RESTRICTIONS.

## Rework

The raw `total_tokens` logging defect is not silently repaired in hashed runtime artifacts.
Reports use `input_tokens + output_tokens` and state the limitation. A runtime adapter fix
requires a new experiment version if token cost becomes a primary endpoint.

