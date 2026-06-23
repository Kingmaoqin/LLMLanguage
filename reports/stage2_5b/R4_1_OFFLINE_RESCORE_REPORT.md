# R4.1 Offline Re-Score Report (v3 explicit annotations)

## What this is

The chosen Phase 7/8 path. Instead of a fresh LLM rerun (which only adds sampling noise and
cannot byte-reproduce R4), the v3 explicit annotations are applied to the **frozen R4 run
bundles** by deterministic offline re-scoring:

```bash
conda run -n agentsearch python scripts/stage2_5b/rescore_with_annotations.py
# reads results/stage2_5b_repair/r4_confirmatory_canonical (480 stored bundles)
# writes results/stage2_5b_rescore_of_r4/
```

`scripts/stage2_5b/rescore_with_annotations.py` recomputes only the annotation-dependent
layers — evidence, branch, policy-failure, and the policy-derived part of
`safe_task_success` — by replaying each stored trajectory through
`evaluate_evidence` / `evaluate_branches` / `evaluate_policy_failures` / `safe_success_metrics`
under the explicit annotation. The annotation-**independent** endpoints
(`official_*`, `local_proxy_success`, `invalid_run`) are reused verbatim. The stored R4
results are never modified.

## Result over all 480 R4 runs

| metric | count |
|---|---|
| rescored runs | 480 |
| runs with any diagnostic change | 108 |
| runs with `safe_task_success` change | 32 |
| `safe_task_success` transitions | **32 × (False → True), 0 × (True → False)** |

Changed-column frequency (of the 108 changed runs): `required_fact_coverage` 90,
`missing_required_facts` 87, `mutation_before_evidence` 37, `n_policy_failures` 37,
`policy_failure_types` 37, `safe_task_success` 32, `first_mutation_*` 21.

`safe_task_success` changes by model/task: gpt_oss retail_28 (15), gemma retail_28 (9),
gemma retail_21 (5), gpt_oss retail_2 (2), gemma retail_41 (1).

## Interpretation

**Every** `safe_task_success` change is `False → True`. The reference-action-derived
`_generic_annotation` was *over-constraining*: it required every reference read-tool to
precede every mutation, producing spurious `mutation_before_required_evidence` failures that
suppressed `safe_task_success`. The explicit v3 annotations encode the actual policy
preconditions, so those false failures disappear. This is precisely the
reference-action-leakage the proposal (Section 2.2) warned about, now corrected.

Two consequences:

1. **Endpoint conclusions are unchanged.** `local_proxy_success` and the official-missing
   status are annotation-independent and identical to R4. The headline R4 finding (no
   multiplicity-corrected endpoint effect; endpoint equivalence not established) stands.
2. **Process/diagnostic conclusions improve in cleanliness.** The corrected `safe_task_success`
   is monotonically more permissive (fewer false unsafe labels), concentrated in retail_28 and
   retail_21. Any re-derived process-level contrasts should be computed from
   `results/stage2_5b_rescore_of_r4/rescored_run_metrics.csv`.

## Outputs (fresh r4_1 root; R4 untouched)

```text
results/stage2_5b_rescore_of_r4/rescored_run_metrics.csv   # per-run endpoints + v3_* diagnostics
results/stage2_5b_rescore_of_r4/rescore_diff_summary.csv   # per-run stored-vs-v3 column diffs
results/stage2_5b_rescore_of_r4/rescore_status.json        # aggregate counts
```

Determinism is unit-tested in `tests/stage2_5b/test_rescore_with_annotations.py`.

## Update: a full LLM rerun was subsequently performed

This offline re-score (now under `results/stage2_5b_rescore_of_r4/`) was kept, but on request a
full fresh **480-run LLM rerun** was also executed under the repaired pipeline, written to
`results/stage2_5b_repair/r4_1_confirmatory_canonical/` (R4 untouched). See
`R4_1_CONFIRMATORY_REPORT_CN.md` and `R4_1_FINAL_INTEGRITY_AUDIT.md`.

The two views agree on the headline and reinforce each other:

- **Offline re-score** (deterministic, attributable): under v3 annotations the generic
  annotation had over-penalized `safe_task_success` in 32 runs (all False→True); endpoints
  unchanged.
- **Fresh rerun** (new sample, fully repaired pipeline): G11 PASS 480/480 valid; **no**
  endpoint contrast survives FDR. R4's one significant endpoint signal (repeated_schedule,
  p_adj=0.012) does **not** replicate (p_adj=0.625) — consistent with gpt-oss
  non-reproducibility and now downgraded to exploratory/non-replicated.
