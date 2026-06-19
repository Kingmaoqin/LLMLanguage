# ASSET_SCAN_REPORT — IR-MSTU Stage-2 (Step 0)

Read-only audit of local assets before any implementation. No files invented; every path below was verified to exist on 2026-06-09.

## 1. Primary benchmark asset — FOUND
- **`/home/xqin5/tau2-bench`** — tau2-bench **v1.0.0**, installed editable (`tau2 1.0.0 -> /home/xqin5/tau2-bench`) in conda envs `p08_skilloverload` and `agentsearch`.
- Console entry point: `tau2 = tau2.cli:main` (`tau2 run --domain <d> --agent-llm <m> --user-llm <m> --num-trials N --num-tasks K`).
- Provider abstraction: **LiteLLM** (`.env` keys). LiteLLM supports OpenAI-compatible custom endpoints → can target our local vLLM servers via `openai/<model>` + `api_base`.
- Other tau2 copies (NOT primary): `/home/xqin5/reactproject/tau2-agentbeats*`, `/home/xqin5/agenticAI/agentbeats_submissions/tau2_bench`, uv cache `tau2-0.2.1.dev0`. **Use `/home/xqin5/tau2-bench` (newest, editable, complete).**

## 2. tau2 internals relevant to Stage-2
- **Domains** (`data/tau2/domains/`): `retail`, `airline`, `telecom`, `banking_knowledge`, `mock`. Each has `tasks.json`, `policy.md`, `db.json`/`db.toml`, `split_tasks.json`.
- **Task schema** (`src/tau2/data_model/tasks.py`): `id`, `description{purpose,relevant_policies,notes}`, `user_scenario{persona, instructions{task_instructions, domain, reason_for_call, known_info, unknown_info}}`, `initial_state`, `evaluation_criteria{actions[], communicate_info, nl_assertions, reward_basis}`.
  - `user_scenario.instructions.task_instructions` = the **user's persona/style** (e.g. "You are detail-oriented…"). This is the **minimal-invasive social-valence injection point**.
  - `evaluation_criteria.actions` = the required tool calls **with exact arguments** → ground truth for evidence coverage, branch decisions and final-state mutation.
- **Engine modules (reusable as-is)**: `runner/` (batch, simulation, checkpoint), `orchestrator/`, `environment/`, `user/` (LLM `user_simulator.py`), `agent/`, `evaluator/` (`evaluator_env.py` = DB-state check, `evaluator_action.py` = required-action check, `evaluator_communicate.py`, `evaluator_nl_assertions.py`, `evaluator.py`), `metrics/`, `data_model/`.

## 3. Task complexity inventory (satisfies plan §3.2)
Counted tasks with ≥5 required actions AND a state mutation (cancel/exchange/refund/modify/update/book/return):
- **retail**: 114 tasks total → **57** qualify (e.g. id 4/30/32/55 = 13 actions; id 3/21 = 12).
- **airline**: 50 tasks total → **8** qualify (id 44 = 19 actions; id 39/42 = 10–11; id 7/12/18 = 5, with cancel/update/rebook mutations).
- Conclusion: tau2 already provides multi-stage, mutation-bearing, policy-constrained workflows. **No task needs to be written from scratch** (plan §3.1 satisfied).

## 4. Model-serving assets
- Local vLLM: env `llm` (vLLM 0.9.2), env `p08_skilloverload`/`agentsearch` (vLLM 0.20.2 — required for gpt-oss / GLM-4.5 archs).
- See `MODEL_ENDPOINT_CHECK` (to be produced at run time) and `IMPLEMENTATION_GAP_LIST.md` §Models for the roster gap (2 of 4 mandated models are not local).
- GPU: 4× A100 80GB, **shared & contended** with co-tenant `zihao_runs` jobs (3 GPUs often occupied). Stage-1 was completed by single-GPU sequential serving + watchdog; same approach planned here.

## 5. Stage-1 reusable assets
- `/home/xqin5/llmlanguage/interactional_robustness_pilot/` — Stage-1 pilot (480 runs). Reusable patterns documented in `STAGE1_REUSE_MAP.md` (valence templates, manipulation checker, noise-floor/practical-threshold analysis, plotting, OpenAI-compatible client, watchdog/single-GPU serving recipe).

## 6. Headline recommendation
Use **tau2-bench retail + airline** as the Stage-2 benchmark. **Reuse tau2's environment + evaluator + (optionally) user simulator**; add a thin IR-MSTU layer that (a) injects social-valence into the user turns, (b) emits the normalized event/log schema, (c) wraps tau2's evaluator output into IR-MSTU metrics. Two design forks (valence-injection mechanism; model roster) require a user decision before the runner is written — see `IMPLEMENTATION_GAP_LIST.md`.
