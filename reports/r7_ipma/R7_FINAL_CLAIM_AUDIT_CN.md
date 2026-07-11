# R7 final claim audit

- **SUPPORTED** — R7 has 1620 traces / 1350 attack-neutral pairs: trace/per-run/pair count can be verified, but live_run_summary is not full-run summary
- **PROVISIONAL** — PASR≈14%: reported=189/1350; formula-compatible raw recompute=176/1350; strict endpoint-supported PASR=96
- **UNSUPPORTED** — attack and neutral differ only by interactional pressure: 418 pairs fail clean user text invariant; semantic template/human audit also incomplete
- **SUPPORTED** — unsafe/privacy = 0 and safety preserved: raw events and metrics support no unsafe/privacy violations
- **FORBIDDEN** — final outcome unaffected: endpoint_not_worse is 92-94%, not 100%; tau2 endpoint oracle has unsupported final_state_correct
- **PROVISIONAL** — endpoint_not_worse=93.3%: computed under script/proxy semantics; strict oracle-supported denominator must be reported
- **PROVISIONAL** — templates have 0 semantic drift: rule_based_offline only; no completed LLM/human semantic audit
- **FORBIDDEN** — 30-task R7 is confirmatory benchmark: below planned 48/72; freeze evidence lacks git support
- **FORBIDDEN** — ProcessGuard is effective: overall 0.110→0.110
- **SUPPORTED** — ProcessGuard is underpowered/inconclusive: defense subset and comparison support this wording
