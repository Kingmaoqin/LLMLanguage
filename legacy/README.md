# Legacy experiment code

This directory contains the archived Stage-2 and Stage-2.5 implementations that were replaced
by the canonical Stage-2.5b path.

- `legacy/stage2/`: dynamic valence overlay, Stage-2 runner, analyzer, and config.
- `legacy/stage2_5/`: LLM-user Stage-2.5 runner, evaluators, analyzers, and configs.

These files are retained only for historical audit and result reconstruction. They are not
formal experiment entry points and are not imported by `src/stage2_5b/`,
`scripts/stage2_5b/`, or `tests/stage2_5b/`.

The exact pre-consolidation tree is recoverable from:

```text
pre-stage2-5b-consolidation-2026-06-18
```
