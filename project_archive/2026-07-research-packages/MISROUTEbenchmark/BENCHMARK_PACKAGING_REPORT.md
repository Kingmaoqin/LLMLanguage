# MISROUTE benchmark packaging report

Prepared: repository built and verified; **not pushed**.

## What was produced

A standalone, documented, reproducible, GitHub-ready benchmark repository at
`misroute-github/`, packaging the interactional tool-agent process-robustness study
(static-urgency contrast) into a public benchmark named **MISROUTE**.

- **Repository path:** `misroute-github/`
- **Files:** 119 (excl. `.git`, generated `outputs/`)
- **Repo size:** 6.4 MB (released data 5.5 MB)
- **Package:** 36 Python modules, ~3,000 LOC
- **Tests:** 48, all passing; `ruff` clean
- **Released data:** 2,680 derived episodes (airline + retail), pseudonymized
- **Toy benchmark:** 16 synthetic episodes, no LLM/GPU/API

## Provenance and derivation

- **Source of truth:** the audited frozen evidence dossier (static-urgency contrast).
- **Raw traces → public data:** 2,680 native episode traces were derived into
  public-schema records; user-message text dropped; all argument values
  pseudonymized via a global equality-preserving map; conditions/models renamed to
  semantic ids. See `SOURCE_TO_PUBLIC_MAPPING.csv`, `INTERNAL_SOURCE_INVENTORY.csv`.
- **Reference pipeline → library:** the internal analysis script was
  reimplemented as a clean modular library with identical numeric semantics.

## Reproduction verification (recomputed == frozen)

Every deterministic frozen number reproduces bit-for-bit from the released data
under analysis seed `20260722`:

| Quantity | Frozen | Recomputed |
| --- | --- | --- |
| reward difference | +0.014815 | +0.014815 |
| tool+argument excess | 0.111777 | 0.111777 |
| tool-name excess | 0.085626 | 0.085626 |
| stage excess | 0.091717 | 0.091717 |
| same-outcome (BOTH_SUCCESS/SAME_FINAL_STATE, arg) | 0.099388 / 0.150167 | match |
| task breadth (arg/tool/stage positive) | 31/30/29 of 36 | match |
| modal adherence / new-path / change-rate | −0.3671 / 0.6306 / 0.7593 | match |

`misroute reproduce-paper` → **PASS (58/58)**; `--full` (5000-iter falsification) →
**PASS (60/60)**; `misroute reproduce-paper --toy` → **PASS** in ~1 s.

## Release validation

`scripts/validate_release.py` → **RELEASE READY: YES**. Checks: required files,
forbidden terminology (R6–R9 / Tier-A / internal names / absolute paths — all
absent), secret scan, JSON validity, data-hash match, doc links, toy + paper
reproduction, pytest. Privacy scan: **0** emails / names / phones / addresses /
secrets in the release.

## Benchmark readiness scoring (0–10; all must be ≥ 8)

| # | Dimension | Score | Basis |
| --- | --- | --- | --- |
| 1 | Installation | 9 | `pip install -e .`; deps numpy/pandas/scipy only |
| 2 | Quickstart | 9 | CLI-first; toy < 30 s; runnable examples |
| 3 | Reproducibility | 10 | bit-for-bit deterministic; per-run manifest |
| 4 | Paper reproduction | 10 | one command; fail-closed 58/58 (60/60 full) |
| 5 | Extensibility | 8 | Condition / AgentAdapter / UserSimulator + add-domain |
| 6 | Documentation | 9 | README + 13 docs + benchmark card + data card |
| 7 | Testing | 9 | 48 tests, CI matrix, paper regression, lint clean |
| 8 | Data provenance | 9 | upstream manifest, data card, source mapping |
| 9 | Licensing | 9 | MIT + NOTICE + third-party audit; fail-closed |
| 10 | Privacy / security | 9 | pseudonymized values, 0 PII, automated scans |
| 11 | Benchmark semantic stability | 9 | versioned schema; data/code/expected separated; regression gate |
| 12 | GitHub presentation | 8 | schematic, structure, push checklist, CITATION |

**Minimum score 8 → RELEASE READY: YES.**

## Deliverables

In the repo (`misroute-github/`): `README.md`, `LICENSE`, `NOTICE`,
`CITATION.cff/.bib`, `pyproject.toml`, CI, `misroute/` package, `benchmark/`,
`data/paper` + `data/toy`, `paper/expected_results.json`, `docs/`, `tests/`,
`scripts/`, `examples/`, `THIRD_PARTY_LICENSE_AUDIT.md`,
`PRIVACY_AND_SECRET_AUDIT.md`, `RELEASE_VALIDATION_REPORT.md`,
`GITHUB_PUSH_CHECKLIST.md`.

At packaging level (internal, not pushed): `INTERNAL_SOURCE_INVENTORY.csv`,
`SOURCE_TO_PUBLIC_MAPPING.csv`, `BENCHMARK_PACKAGING_REPORT.md`,
`_packaging/derive_paper_data.py`.

## Unresolved issues / notes

- `OWNER` / author fields are placeholders to be filled before push.
- DISJOINT / RANDOM NN pairings and falsification FPRs depend on within-cell
  episode ordering; they are reported as sensitivity checks (loose tolerance), not
  gated bit-for-bit. All main point estimates are gated and exact.
- Level-3 live evaluation needs the upstream environment installed + an adapter;
  it fails closed with guidance until then. Offline analysis/reproduction are fully
  self-contained.
- Not pushed anywhere (no git push / GitHub / HF / Zenodo / PyPI), per instructions.

## RELEASE READY: YES
