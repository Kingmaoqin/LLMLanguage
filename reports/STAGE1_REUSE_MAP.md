# STAGE1_REUSE_MAP — what to reuse from the Stage-1 pilot

Source: `/home/xqin5/llmlanguage/interactional_robustness_pilot/`.

| Stage-1 asset | Path | Stage-2 reuse | Action |
|---|---|---|---|
| OpenAI-compatible client | `src/model_client.py` | LiteLLM (via tau2) replaces it for the agent/user; keep this client only for the endpoint precheck script | adapt → `scripts/check_model_endpoints.py` |
| Manipulation/invariance checker | `src/manipulation_checks.py` | same forbidden-phrase + invariance logic; retarget at tau2 valence-injected user turns | port → `src/manipulation_checks.py` |
| Statistics (bootstrap CI, paired delta, BH-FDR, sign test) | `src/statistics.py` | reuse directly for noise-floor + paired analysis | reuse as-is |
| Plotting | `src/plotting.py` | adapt to Stage-2 figure set (6 figs, §41) | adapt |
| Noise-floor + practical-threshold logic | `analyze_results.py` | same protocol (neutral repeats, threshold gating) over tau2 metrics | port the logic |
| Valence templates | `data/condition_scripts.json` | Stage-2 uses 5 conditions w/ mid-turn injection (plan §16) | new `data/social_valence_templates.yaml` |
| Single-GPU sequential serving + watchdog | (this session's `/tmp/watchdog*.sh`) | same anti-contention serving recipe | reuse recipe |

**Not reusable / replaced**: Stage-1's hand-rolled mock `tool_environment.py`, `agent_loop.py`, `evaluators.py`, `base_tasks.json` — all superseded by tau2's real environment/agent/evaluator/tasks (the whole point of Stage-2). Do **not** port them.

**Conceptual carry-over**: separate "out-of-order *attempt*" from "completed unsafe state"; always gate effects against the neutral noise floor + a practical threshold; report null honestly; keep an `model_error`/invalid bucket distinct from behavioral failure.
