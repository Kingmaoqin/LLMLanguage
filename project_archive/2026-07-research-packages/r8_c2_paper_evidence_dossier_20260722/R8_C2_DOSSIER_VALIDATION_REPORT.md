# R8 C2 Dossier Validation Report

- Generated: 2026-07-22
- Data mutation: none
- New rollouts/reviewers: none
- Main document characters: 79,039
- Chinese characters (CJK code points): 13,040
- Whitespace-delimited tokens: 8,819
- Required target: approximately 15,000–25,000 Chinese characters; completeness takes precedence.

## Output SHA-256

| File | SHA-256 | Scope |
| --- | --- | --- |
| R8_C2_PAPER_WRITING_EVIDENCE_DOSSIER_ZH.md | `6ebfdd586f84badb6c0ff3d5b298984ffd8d450481aeeff61845f1e925bf755a` | exact full file bytes |
| R8_C2_DOSSIER_SOURCE_MANIFEST.json | `6e018b61364221b3d8235eeeb01c2774afc1c4e3f1c98c93b6c380e2041ff936` | exact full file bytes |
| R8_C2_DOSSIER_NUMERICAL_RECONCILIATION.csv | `a1ff5631ef4f1e9c3cfa13ab2dccfa0b3b2d1f406cfc14ab06c0dcdff731fa3e` | exact full file bytes |

The front-matter `document_sha256` is `3905255424c593fd2271818c62d3ff24f9de2ef837e589dfdf3695e96e886a13` and is the SHA-256 of the document with that field replaced by 64 zeroes. This canonical convention avoids an impossible self-referential full-file digest. The exact full-file digest is listed above.

## Automated Checks

| Check | Pass |
| --- | --- |
| required_sections_1_to_43 | PASS |
| required_tail_blocks | PASS |
| valid_episode_literal | PASS |
| task_cluster_literal | PASS |
| construct_limitation | PASS |
| post_hoc_disclosed | PASS |
| unknown_parameters_marked | PASS |
| no_sensitive_argument_values_in_cases | PASS |
| compound_bug_disclosed | PASS |
| ipw_bug_disclosed | PASS |

## Numerical Audit Decisions

- Frozen main estimand: RAW_CROSS_REPEAT_REPRODUCTION, equal task-cluster inference.
- Frozen reward: +0.014815, 90% CI [-0.014815, 0.046296], TOST p=0.038837.
- Frozen process excess: 0.111777 / 0.085626 / 0.091717.
- Correct compound count: 16 explicit domain+task keys. The 17-task `OUTCOME_MARGIN_SENSITIVITY.csv` compound rows are excluded.
- `inverse_availability_weighting` is excluded as weighting evidence because the implementation did not apply weights.
- No raw R8 trace, metrics, frozen registry, or prior audit output was modified.

## Manual Review Notes

The document distinguishes task clusters from episode/pair/specification denominators, distinguishes full-pipeline FPR from ordinary p-values, retains the post-hoc status, and uses association language because the C1/C2 renderer-key construct difference is not closed. Representative cases expose only anonymous IDs, tool names, task type, outcome relations, and change categories.
