# BENCHMARK_INVENTORY — local benchmark assets

## tau2-bench (PRIMARY) — `/home/xqin5/tau2-bench`, v1.0.0, editable
| Domain | tasks.json | policy.md | db | qualifying tasks (≥5 actions + mutation) |
|---|---|---|---|---|
| retail | 114 tasks | `policy.md` | `db.json` | **57** |
| airline | 50 tasks | `policy.md` | `db.json` | **8** |
| telecom | tasks.json/_full/_small | `main_policy.md` (+ workflow/manual) | `db.toml`,`user_db.toml` | not scored (Stage-2 v1 = retail+airline only) |
| banking_knowledge | (knowledge/RAG) | — | — | out of scope (needs retrieval-config) |
| mock | tiny | — | — | smoke/testing only |

Each domain ships: simulated user (LLM), domain API tools, policy guidelines, customer-service workflows, **final DB-state evaluator**, repeated-trial reliability setting — i.e. everything plan §9 wants.

### Reusable engine (do NOT reimplement)
- `src/tau2/runner/` — batch + per-task simulation + checkpoint/resume.
- `src/tau2/environment/` — deterministic tool execution over the domain DB.
- `src/tau2/user/user_simulator.py` — LLM user simulator driven by `user_scenario.instructions`.
- `src/tau2/agent/` — tool-using agent loop.
- `src/tau2/evaluator/` — `evaluator_env` (DB state), `evaluator_action` (required actions w/ args), `evaluator_communicate`, `evaluator_nl_assertions`, top-level `evaluator.py` + `reward_basis`.
- `src/tau2/metrics/`, `src/tau2/data_model/` (Task/Message/Simulation pydantic models).

### Pre-existing baseline results (context, not used as our data)
`data/tau2/results/final/*.json` — gpt-4.1 / o4-mini / claude-3.7 on retail/airline/telecom, 4 trials. Useful only as difficulty reference.

## Secondary / not selected
- `/home/xqin5/reactproject/tau2-agentbeats`, `tau2-agentbeats-leaderboard`, `/home/xqin5/agenticAI/agentbeats_submissions/tau2_bench` — AgentBeats wrappers around tau2; not needed (we use the canonical install).
- No local **AgentDojo** / **ToolEmu** / **AgentBench** found (plan Priority 2/3 sources absent). → Stage-2 v1 stays on tau2 retail+airline (plan §11 explicitly allows this; workspace/HR deferred).
