# Independent Review Checklist (round-5 §16)

A reviewer can verify each claim with the listed artifact/command.

| # | Claim | Check | Status |
|---|---|---|---|
| 1 | No existing results overwritten | round-5 outputs are new subdirs (`traces/`, `interactional_metrics/`) + new report dir; R4/r4_1 bundles untouched | ✅ |
| 2 | No runtime LLM user simulator | runner uses `controlled_user_no_llm`; `tests/stage2_5b/test_no_runtime_user_llm.py` | ✅ |
| 3 | Task semantics identical across conditions | templates are wrappers only; `BENCHMARK_CONDITION_AUDIT.md` | ✅ |
| 4 | No authorization/urgency/threat contamination | verbatim template review; `BENCHMARK_CONDITION_AUDIT.md` | ✅ |
| 5 | Token bug fixed + provenance flagged | `src/adapters/normalize.py`; `tests/stage2_5b/test_trace_metrics.py`; 0/480 missing | ✅ |
| 6 | Traces reconstructable from existing runs | `RECONSTRUCTION_AUDIT.md`: 480/480 complete, 0 schema failures | ✅ |
| 7 | Multidimensional profile (not single score) | `INTERACTIONAL_ROBUSTNESS_PROFILE.md`; 6 dimensions, 120 metric×contrast rows | ✅ |
| 8 | Multiplicity control | task-cluster bootstrap + Wilcoxon + BH FDR; `STATISTICAL_ANALYSIS.md` | ✅ |
| 9 | Noise floor reported | `NOISE_FLOOR_REPORT.md`; within-neutral SD vs effects | ✅ |
| 10 | Uncomputable metrics marked missing, not 0 | `interactional_metrics()` emits None; `official_reward_basis_success` missing for NL_ASSERTION | ✅ |
| 11 | Reproducibility provenance | run_meta carries git_commit, *_hash, token_source; manifests + benchmark patch manifest | ✅ |
| 12 | Endpoint stability not equated to robustness | profile + report wording (round-5 §14) | ✅ |
| 13 | Measurement-complete rerun available + smoke-gated | `run_measurement_complete_experiment.py`; smoke `measurement_complete_smoke_r5`: 24/24 runs, 24 traces, 24 interactional metric rows, 0 invalid | ✅ |
| 14 | All code tested | `conda run -n agentsearch python -m unittest discover -s tests/stage2_5b -p 'test_*.py'`: 134 tests pass incl. new trace schema/metrics | ✅ |
| 15 | Full rerun gated on approval | not launched; awaiting user go-ahead | ⏳ |

## Known limitations (must stay in the paper)

- Retail-only; 2 models; Tier-C boundary/unsafe under-covered.
- `official_reward_basis_success` not fully offline-computable (NL_ASSERTION) → local proxy.
- State divergence is hash-level (no field-level DB diff).
- gpt-oss is not bit-reproducible at temp 0; single-sample effects can be fragile.
