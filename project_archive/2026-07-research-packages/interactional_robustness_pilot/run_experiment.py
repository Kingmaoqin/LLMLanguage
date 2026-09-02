from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

from src.agent_loop import run_agent
from src.manipulation_checks import CONDITIONS, run_checks
from src.utils import append_jsonl, load_json, load_yaml, package_versions, read_csv, write_csv, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--temperature", type=float, required=True)
    parser.add_argument("--subset", nargs="*", default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    config = load_yaml(root / args.config)
    model_config = load_yaml(root / "model_config.yaml")
    reports_dir = root / "reports"
    results_dir = root / "results"

    base_tasks = load_json(root / "data" / "base_tasks.json")
    condition_scripts = load_json(root / "data" / "condition_scripts.json")
    checks_passed, _, _ = run_checks(base_tasks, condition_scripts, reports_dir)
    if not checks_passed:
        write_blocked_report(reports_dir, "Invariant/manipulation checks failed.")
        raise SystemExit(1)
    if not model_config.get("models") or not all(model.get("preflight_passed") for model in model_config["models"]):
        write_blocked_report(reports_dir, "Model preflight has not passed for all configured models.")
        raise SystemExit(1)

    task_by_id = {task["task_id"]: task for task in base_tasks}
    script_by_key = {(script["task_id"], script["condition_id"]): script for script in condition_scripts["scripts"]}
    selected_task_ids = args.subset if args.subset else [task["task_id"] for task in base_tasks]
    combos = build_run_order(config, selected_task_ids, args.temperature)
    random.Random(config["experiment"]["randomization_seed"]).shuffle(combos)
    write_json(results_dir / f"run_order_temp_{args.temperature}.json", combos)
    write_json(
        reports_dir / "run_manifest.json",
        {
            "argv": sys.argv,
            "temperature": args.temperature,
            "subset": args.subset,
            "randomization_seed": config["experiment"]["randomization_seed"],
            "package_versions": package_versions(),
        },
    )

    if args.temperature == float(config["experiment"].get("main_temperature", 0.0)) and not args.subset:
        for path in ["tool_logs.jsonl", "conversation_logs.jsonl", "final_environment_states.jsonl"]:
            (results_dir / path).write_text("", encoding="utf-8")
        existing_metrics: List[Dict[str, Any]] = []
    else:
        existing_metrics = read_csv(results_dir / "run_metrics.csv")

    new_metrics: List[Dict[str, Any]] = []
    seeds = list(config["experiment"].get("seeds", [11, 13, 17, 19, 23]))
    for model_entry in model_config["models"]:
        for combo in combos:
            task = task_by_id[combo["task_id"]]
            script = script_by_key[(combo["task_id"], combo["condition_id"])]
            seed = seeds[combo["repeat_id"] % len(seeds)] if seeds else None
            run_id = f"{model_entry['model_alias']}_t{str(args.temperature).replace('.', 'p')}_{combo['task_id']}_{combo['condition_id']}_r{combo['repeat_id']}"
            run_meta = {
                "run_id": run_id,
                "model_alias": model_entry["model_alias"],
                "model_id": model_entry["model_id"],
                "task_id": combo["task_id"],
                "condition_id": combo["condition_id"],
                "repeat_id": combo["repeat_id"],
                "temperature": args.temperature,
                "seed": seed if model_entry.get("supports_seed") is True else "seed_not_supported",
                "tool_protocol": model_entry.get("tool_protocol"),
            }
            result = run_agent(config, model_entry, task, script, run_meta, args.temperature, seed)
            new_metrics.append(result["metrics"])
            append_jsonl(results_dir / "tool_logs.jsonl", result["tool_logs"])
            append_jsonl(results_dir / "conversation_logs.jsonl", [result["conversation"]])
            append_jsonl(results_dir / "final_environment_states.jsonl", [result["final_environment_state"]])
            write_csv(results_dir / "run_metrics.csv", existing_metrics + new_metrics)


def build_run_order(config: Dict[str, Any], task_ids: List[str], temperature: float) -> List[Dict[str, Any]]:
    neutral_repeats = int(config["experiment"].get("neutral_repeats", 5))
    perturbation_repeats = int(config["experiment"].get("perturbation_repeats", 3))
    combos = []
    for task_id in task_ids:
        for condition in CONDITIONS:
            repeats = neutral_repeats if condition == "neutral" else perturbation_repeats
            for repeat_id in range(repeats):
                combos.append({"task_id": task_id, "condition_id": condition, "repeat_id": repeat_id, "temperature": temperature})
    return combos


def write_blocked_report(reports_dir: Path, reason: str) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "RUN_BLOCKED_REPORT.md").write_text(
        "# Run Blocked\n\n"
        f"{reason}\n\n"
        "Per pass/fail checklist, the main experiment was not run and no scientific claims should be made.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

