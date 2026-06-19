"""IR-MSTU Stage-2 runner (plan §27-30).

Reuses tau2 end-to-end: build_orchestrator wires the real environment/agent/user-simulator/
evaluator; apply_valence overlays the social-valence condition onto the user channel without
touching the task. Each run resets state (build_orchestrator builds a fresh environment),
hides the condition from the agent (valence lives only in user turns), and emits normalized
logs + an IR-MSTU metrics row.

Run:
    conda run -n agentsearch python run_stage2_experiment.py \
        --config configs/stage2.yaml --temperature 0.0 \
        [--models glm_4_5_air] [--tasks R1_retail_modify_pending] [--max-runs N]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Any

import yaml

from src.adapters.instrument import ToolEventRecorder
from src.adapters.normalize import extract_metrics, normalized_tool_events, parser_health
from src.branch_analysis import adjudicate_branches, write_match_by_tool
from src.manipulation_checks import run_checks as run_manipulation_checks
from src.valence import ValenceController, apply_valence, load_valence_templates

ROOT = Path(__file__).resolve().parent


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _llm_args(model: dict, temperature: float) -> dict:
    """LiteLLM kwargs that route to the local OpenAI-compatible vLLM endpoint."""
    return {"api_base": model["base_url"], "api_key": model.get("api_key", "EMPTY"),
            "temperature": temperature}


def build_matrix(tasks: list[dict], conditions: list[str], neutral_reps: int,
                 pert_reps: int) -> list[dict]:
    matrix = []
    for task in tasks:
        for cond in conditions:
            reps = neutral_reps if cond == "neutral" else pert_reps
            for rep in range(reps):
                matrix.append({"task": task, "condition_id": cond, "repeat_id": rep})
    return matrix


def run_one(model: dict, task: dict, condition_id: str, repeat_id: int, *, templates: dict,
            user_sim_model: dict, temperature: float, exp: dict) -> dict[str, Any]:
    """Run a single (model, task, condition, repeat) via tau2 + valence overlay."""
    from tau2.run import EvaluationType, build_orchestrator, get_tasks, run_simulation
    from tau2.data_model.simulation import TextRunConfig

    domain = task["source_domain"]
    tau2_task = get_tasks(domain, task_ids=[task["source_task_id"]])[0]
    seed = exp["tau2_seed"] + repeat_id

    config = TextRunConfig(
        domain=domain, agent="llm_agent", user="user_simulator",
        llm_agent=model["litellm_model"], llm_args_agent=_llm_args(model, temperature),
        llm_user=user_sim_model["litellm_model"], llm_args_user=_llm_args(user_sim_model, 0.0),
        max_steps=exp["max_steps"], max_errors=exp["max_errors"], seed=seed,
    )
    orch = build_orchestrator(config, tau2_task, seed=seed)

    controller = ValenceController(condition_id, templates[condition_id])
    apply_valence(orch, controller)
    recorder = ToolEventRecorder()
    recorder.attach(orch)

    state_before = orch.environment.get_db_hash()
    # ALL_IGNORE_BASIS = Env(DB) + Action + Communicate, all rule-based and LOCAL. Excludes the
    # NL-assertion judge, which defaults to a remote OpenAI model (tau2.config) we don't use.
    sim = run_simulation(orch, evaluation_type=EvaluationType.ALL_IGNORE_BASIS)
    state_after = orch.environment.get_db_hash()

    run_meta = {
        "run_id": f"{model['alias']}__{task['task_id']}__{condition_id}__rep{repeat_id}__temp{temperature}",
        "model_alias": model["alias"], "task_id": task["task_id"],
        "source_task_id": task["source_task_id"], "domain": domain,
        "condition_id": condition_id, "repeat_id": repeat_id, "temperature": temperature,
    }
    events = normalized_tool_events(
        sim, run_meta, records=recorder.agent_records(),
        evidence_tools=set(task.get("required_evidence") or []),
        mutation_tools=set(task.get("state_mutations") or []),
    )
    metrics = extract_metrics(sim, run_meta, events, injection_log=controller.injection_log,
                              state_before_hash=state_before, state_after_hash=state_after)
    branch_rows = [{**run_meta, **d} for d in adjudicate_branches(
        events, task.get("forced_replanning_points") or [],
        required_evidence=set(task.get("required_evidence") or []),
        write_matches=write_match_by_tool(sim.reward_info),
    )]
    return {
        "metrics": metrics,
        "branch_decisions": branch_rows,
        "events": events,
        "raw_messages": [{**run_meta, **m.model_dump(mode="json")} for m in (sim.messages or [])],
        "conversation": [{**run_meta, "role": getattr(m, "role", None),
                          "content": getattr(m, "content", None),
                          "tool_calls": [tc.name for tc in (getattr(m, "tool_calls", None) or [])],
                          "turn_idx": getattr(m, "turn_idx", None)} for m in (sim.messages or [])],
        "state_deltas": [e for e in events if e["mutated"]],
        "invalid_tool_calls": [e for e in events if e["tool_error"] or e["undefined_tool"]],
        "health": {**run_meta, **parser_health(events, sim)},
        "injections": [{**run_meta, **i} for i in controller.injection_log],
        "final_state": {**run_meta, "state_before_hash": state_before,
                        "state_after_hash": state_after, "reward": metrics["reward"]},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage2.yaml")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--models", nargs="*", help="subset of model aliases (default: all local)")
    ap.add_argument("--tasks", nargs="*", help="subset of IR-MSTU task_ids")
    ap.add_argument("--max-runs", type=int, default=None, help="cap total runs (smoke test)")
    ap.add_argument("--user-sim", default=None, help="override user-simulator model alias")
    ap.add_argument("--skip-endpoint-check", action="store_true", help="skip the pre-run endpoint gate")
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()

    cfg = _load_yaml(ROOT / args.config)
    exp = cfg["experiment"]
    model_cfg = _load_yaml(ROOT / cfg["paths"]["model_config"])
    task_spec = _load_yaml(ROOT / cfg["paths"]["task_spec"])
    templates_path = ROOT / cfg["paths"]["templates"]
    templates = load_valence_templates(templates_path)
    condition_order = yaml.safe_load(templates_path.read_text())["condition_order"]
    out_dir = ROOT / (args.output_dir or cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # Gate on manipulation checks (plan §17): template contamination + task-spec invariance.
    if not run_manipulation_checks(templates_path, ROOT / "reports", ROOT / "results",
                                   task_spec_path=ROOT / cfg["paths"]["task_spec"]):
        raise SystemExit("Manipulation checks failed — aborting (plan §17).")

    models = {m["alias"]: m for m in model_cfg["models"]}
    user_sim_model = models[args.user_sim or model_cfg["user_simulator_llm"]]
    selected_models = [models[a] for a in (args.models or list(models))]

    # Endpoint gate (plan §20/§46): every model that will be hit (agents + user-sim) must pass
    # its tool-call precheck, else a parser/serving failure would masquerade as a behaviour
    # result. run_precheck also writes reports/MODEL_ENDPOINT_CHECK.md on this path.
    if not args.skip_endpoint_check:
        from scripts.check_model_endpoints import run_precheck
        need = {m["alias"] for m in selected_models} | {user_sim_model["alias"]}
        passed = run_precheck(ROOT, cfg["paths"]["model_config"], aliases=sorted(need))
        bad = [a for a in need if not passed.get(a, False)]
        if bad:
            raise SystemExit(f"Endpoint precheck failed for {bad} — aborting (plan §20). "
                             f"See reports/MODEL_ENDPOINT_CHECK.md.")
    tasks = task_spec["mini_stage2_v1"]
    if args.tasks:
        tasks = [t for t in tasks if t["task_id"] in args.tasks]

    matrix = build_matrix(tasks, condition_order, exp["neutral_repeats"], exp["perturbation_repeats"])
    random.Random(exp["randomization_seed"]).shuffle(matrix)

    # Preserve other models' outputs; drop the selected models' prior rows (clean re-run).
    # Each model runs as a separate process, so without this the per-process CSV write would
    # overwrite earlier models' metrics.
    metrics_rows: list[dict] = _reset_model_outputs(out_dir, {m["alias"] for m in selected_models})
    n_done = 0
    for model in selected_models:
        for cell in matrix:
            if args.max_runs is not None and n_done >= args.max_runs:
                break
            meta = {
                "run_id": f"{model['alias']}__{cell['task']['task_id']}__{cell['condition_id']}__rep{cell['repeat_id']}__temp{args.temperature}",
                "model_alias": model["alias"], "task_id": cell["task"]["task_id"],
                "source_task_id": cell["task"]["source_task_id"], "domain": cell["task"]["source_domain"],
                "condition_id": cell["condition_id"], "repeat_id": cell["repeat_id"],
                "temperature": args.temperature,
            }
            try:
                res = run_one(model, cell["task"], cell["condition_id"], cell["repeat_id"],
                              templates=templates, user_sim_model=user_sim_model,
                              temperature=args.temperature, exp=exp)
            except Exception as exc:
                # Record the failure AS A ROW (final_state_correct=NA) so denominators stay
                # correct and parser/infra failures are not silently dropped (plan §46).
                _append_jsonl(out_dir / "adapter_errors.jsonl", [{**meta, "error": f"{type(exc).__name__}: {exc}"}])
                metrics_rows.append({**meta, "final_state_correct": None, "reward": None,
                                     "invalid_run": True, "termination_reason": f"exception:{type(exc).__name__}"})
                _write_metrics_csv(out_dir / "run_metrics.csv", metrics_rows)
                n_done += 1
                print(f"[{n_done}] {meta['run_id']} INVALID ({type(exc).__name__})")
                continue
            res["metrics"]["invalid_run"] = False
            metrics_rows.append(res["metrics"])
            _append_jsonl(out_dir / "normalized_tool_events.jsonl", res["events"])
            _append_jsonl(out_dir / "raw_model_outputs.jsonl", res["raw_messages"])
            _append_jsonl(out_dir / "conversation_logs.jsonl", res["conversation"])
            _append_jsonl(out_dir / "state_deltas.jsonl", res["state_deltas"])
            _append_jsonl(out_dir / "invalid_tool_calls.jsonl", res["invalid_tool_calls"])
            _append_jsonl(out_dir / "branch_decisions.jsonl", res["branch_decisions"])
            _append_jsonl(out_dir / "parser_health.jsonl", [res["health"]])
            _append_jsonl(out_dir / "valence_injections.jsonl", res["injections"])
            _append_jsonl(out_dir / "final_environment_states.jsonl", [res["final_state"]])
            _write_metrics_csv(out_dir / "run_metrics.csv", metrics_rows)
            n_done += 1
            print(f"[{n_done}] {res['metrics']['run_id']} "
                  f"final_ok={res['metrics']['final_state_correct']} reward={res['metrics']['reward']}")

    print(f"done: {n_done} runs -> {out_dir}")


_JSONL_FILES = [
    "normalized_tool_events.jsonl", "raw_model_outputs.jsonl", "conversation_logs.jsonl",
    "state_deltas.jsonl", "invalid_tool_calls.jsonl", "branch_decisions.jsonl",
    "parser_health.jsonl", "valence_injections.jsonl", "final_environment_states.jsonl",
    "adapter_errors.jsonl",
]


def _reset_model_outputs(out_dir: Path, aliases: set[str]) -> list[dict]:
    """Drop prior rows for `aliases` from run_metrics.csv + all jsonl (so a model can be
    re-run cleanly), preserving every other model. Returns the preserved metrics rows."""
    preserved: list[dict] = []
    mp = out_dir / "run_metrics.csv"
    if mp.exists():
        with mp.open(encoding="utf-8") as f:
            preserved = [r for r in csv.DictReader(f) if r.get("model_alias") not in aliases]
    for fn in _JSONL_FILES:
        p = out_dir / fn
        if not p.exists():
            continue
        kept = [ln for ln in p.read_text(encoding="utf-8").splitlines()
                if ln.strip() and json.loads(ln).get("model_alias") not in aliases]
        p.write_text(("\n".join(kept) + "\n") if kept else "", encoding="utf-8")
    return preserved


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")


def _write_metrics_csv(path: Path, rows: list[dict]) -> None:
    fields = list({k for r in rows for k in r})
    preferred = ["run_id", "model_alias", "task_id", "domain", "condition_id", "repeat_id",
                 "temperature", "final_state_correct", "reward", "evidence_read_proportion",
                 "branch_write_proportion", "communicate_proportion", "agent_tool_calls",
                 "irreversible_actions", "state_mutated", "termination_reason"]
    ordered = [f for f in preferred if f in fields] + [f for f in fields if f not in preferred]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ordered)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
