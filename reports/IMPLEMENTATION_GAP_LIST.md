# IMPLEMENTATION_GAP_LIST — what must be decided/built before running

## A. BLOCKING DECISIONS (need user input — skill principles #2/#3)

### A1. Model roster gap (2 of 4 mandated models not local)
Plan §18 fixes: `gpt-oss-120b`, `Qwen3-32B`, `GLM-4.5-Air`, `Llama-3.3-70B-Instruct`.
| Model | Local? | Path |
|---|---|---|
| gpt-oss-120b | ✅ | `/home/xqin5/hf_p08_models/gpt-oss-120b` |
| GLM-4.5-Air | ✅ | `/home/xqin5/hf_p08_models/GLM-4.5-Air-FP8` (Glm4MoeForCausalLM, vLLM 0.20.2) |
| Qwen3-32B | ❌ | only `Qwen3-14B-FP8`, `Qwen3-8B`, `Qwen3.6-27B` local |
| Llama-3.3-70B-Instruct | ❌ | no weights (only `swebench_llama70B_*` result JSONs) |
Options: (a) **download** the 2 missing; (b) **substitute** locals (Qwen3-14B-FP8 / Qwen3.6-27B for Qwen3-32B; defer Llama or use another 70B); (c) **run 2 now**, mark the other two `not_run_deployment_failure`. Plan §18 forbids silent substitution outside an ablation → needs explicit user call.

### A2. Social-valence injection architecture
tau2's user is an **LLM simulator** driven by `user_scenario.instructions`. Plan §16 specifies **exact templated** valence turns with **mid-turn injection after tool-call 3 and 6**, plus manipulation checks for forbidden phrases. Two ways to reconcile:
- **Option A — persona-instruction injection (max reuse, least invasive):** prepend a valence stance to `task_instructions`; the tau2 user-LLM role-plays it. Pro: minimal, fully reuses tau2 user loop. Con: valence is *generated*, not exact-templated → manipulation check becomes post-hoc on generated turns; mid-turn timing ("after tool call 3/6") not guaranteed.
- **Option B — scripted valence overlay (matches plan §16 exactly):** keep tau2 env/agent/evaluator, but wrap the user channel so the **first turn and the after-3 / after-6 turns are exact templates**, with tau2's user-sim handling only substantive clarifications. Pro: exact templates, deterministic timing, clean manipulation checks. Con: more invasive to tau2's user/orchestrator loop.

Recommendation: **Option B** (the plan's templates + mid-turn timing are explicit and central to manipulation control), implemented as a thin wrapper that does not touch tau2 DB/tools/evaluator.

## B. TO BUILD (after A resolved) — thin IR-MSTU layer over tau2
1. `configs/model_config.yaml` — 4 endpoints (alias, base_url, served model id, vLLM env) → LiteLLM `openai/<id>` + `api_base`.
2. `scripts/check_model_endpoints.py` — `/models` + `/chat/completions` + tool-call parse precheck → `reports/MODEL_ENDPOINT_CHECK.md` (adapt Stage-1 `model_client.py`).
3. `data/social_valence_templates.yaml` — 5 conditions, first_turn + mid_turns (plan §16).
4. `src/manipulation_checks.py` — invariance + forbidden-phrase check over the injected user turns (port Stage-1).
5. `data/irmstu_tasks/tau_adapted_tasks.yaml` — 6 candidate tasks with source IDs, required_evidence, forced_replanning_points, policy tags (no DB/tool/evaluator change).
6. **Valence + logging wrapper** around tau2 runner: inject condition into user channel; emit `raw_model_outputs.jsonl`, `normalized_tool_events.jsonl`, `state_deltas.jsonl`, `final_environment_states.jsonl`, `run_metrics.csv` (plan §30) with state-before/after hashes; reuse tau2 evaluator output (env/action/communicate/nl) mapped to IR-MSTU metrics.
7. `run_stage2_experiment.py` (plan §27) — env reset per run, run-id convention §28, condition hidden from agent.
8. Long-tool preflight (plan §22) on one real tau task, ≥6 calls + mutation + final-state check → `reports/LONG_PREFLIGHT_REPORT.md`.
9. Analysis (port Stage-1 `statistics.py` + noise-floor) + 6 figures + reports.

## C. Integration unknowns to verify during build (skill #1 — look up, don't guess)
- Exact LiteLLM spelling for a local OpenAI-compatible vLLM endpoint (`openai/<id>` + `api_base`/env), and how `tau2 run` passes `--agent-llm`/`--user-llm` through to LiteLLM.
- Programmatic single-task entry (reuse `runner/simulation.py`) vs CLI `tau2 run`, and where to hook the user channel for Option B.
- Whether tau2 exposes per-step tool events + state hashes, or whether the wrapper must derive `state_before/after_hash` from the env DB snapshot.
- tau2 `reward_basis` semantics → map to `final_state_correct` (env), `evidence_coverage` (action), policy adherence.

## D. Operational constraint
4× A100 shared with co-tenant `zihao_runs` (≥3 GPUs often busy). Plan = single-GPU **sequential** serving of the 4 models + keep-alive watchdog (proven in Stage-1). Serving order: GLM-4.5-Air & gpt-oss-120b on vLLM 0.20.2 env; Qwen on `llm`/0.20.2 env. 70B/120B are the slow legs.
