"""R6 experiment runner (round-6 §7.3).

Resolves the experiment matrix (models x tasks x conditions x seeds) from a phase config and
the R6 task/template/model data, then dispatches each cell to a per-domain executor. The
matrix planning and ``--dry-run`` are fully offline and require no model.

Execution boundary (honest): smoke/preflight may execute through the R6 minimal
deterministic environment. This validates controlled-user rendering, tool/state traces,
field-level diffs, and metric extraction without any model call. Retail/airline cells are
tagged as ``tau2_r6_controlled_user`` because their R6 user adapter is available for a
future live tau2 executor, but live tau2/model execution is intentionally out of scope here.
Pilot/full execution remains blocked by default so deterministic smoke traces are not
mistaken for model experiment results.

    python scripts/r6/run_r6_experiment.py --phase smoke  --config configs/r6/r6_preflight.yaml --dry-run
    python scripts/r6/run_r6_experiment.py --phase pilot  --config configs/r6/r6_pilot.yaml --dry-run
    python scripts/r6/run_r6_experiment.py --phase full   --config configs/r6/r6_full_main.yaml --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.r6.minimal_env import R6MinimalDeterministicEnvironment, R6RunCell, write_trace  # noqa: E402

TAU2_DOMAINS = {"retail", "airline"}
DEFAULT_TEMPLATES = Path("data/r6/r6_social_style_templates.yaml")
DEFAULT_USER_POLICIES = Path("data/r6/r6_task_user_policies.yaml")
DEFAULT_ANNOTATIONS = Path("data/r6/r6_task_policy_annotations.yaml")
DEFAULT_SEED_STATES = Path("data/r6/r6_environment_seed_states/seed_states.yaml")


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load((ROOT / path if not path.is_absolute() else path).read_text(encoding="utf-8"))


def load_tasks(tasks_path: Path) -> list[dict[str, Any]]:
    data = load_yaml(tasks_path)
    tasks = data.get("tasks") if isinstance(data, dict) and "tasks" in data else data
    return list(tasks.values()) if isinstance(tasks, dict) else list(tasks)


def resolve_task_ids(config: dict[str, Any], all_tasks: list[dict[str, Any]]) -> list[str]:
    spec = config.get("tasks", "all")
    by_id = {t["task_id"]: t for t in all_tasks}
    if spec == "all":
        return [t["task_id"] for t in all_tasks]
    missing = [tid for tid in spec if tid not in by_id]
    if missing:
        raise SystemExit(f"config references unknown task_ids: {missing}")
    return list(spec)


def domain_of(task: dict[str, Any]) -> str:
    return str(task.get("domain") or "")


def executor_for(domain: str) -> str:
    return "tau2_r6_controlled_user" if domain in TAU2_DOMAINS else "r6_minimal_env"


def build_matrix(config: dict[str, Any], all_tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {t["task_id"]: t for t in all_tasks}
    task_ids = resolve_task_ids(config, all_tasks)
    models = config["models"]
    conditions = config["conditions"]
    seeds = config["seeds"]
    temperature = config.get("temperature", 0.0)
    cells = []
    for model in models:
        for tid in task_ids:
            task = by_id[tid]
            domain = domain_of(task)
            executor = executor_for(domain)
            for cond in conditions:
                for seed in seeds:
                    cells.append({
                        "run_id": f"{model}__{tid}__{cond}__seed{seed}__temp{temperature}",
                        "model_alias": model, "task_id": tid, "domain": domain,
                        "layer": str(task.get("layer") or ""), "condition_id": cond,
                        "seed": seed, "temperature": temperature, "executor": executor,
                    })
    return cells


def write_plan(out_dir: Path, cells: list[dict[str, Any]]) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = ["run_id", "model_alias", "task_id", "domain", "layer", "condition_id",
              "seed", "temperature", "executor"]
    with (out_dir / "run_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(cells)
    from collections import Counter
    by_executor = Counter(c["executor"] for c in cells)
    summary = {
        "total_cells": len(cells),
        "planned_tau2_cells": by_executor.get("tau2_r6_controlled_user", 0),
        "deterministic_minimal_env_cells": len(cells),
        "live_tau2_executor_available": False,
        "live_model_executor_available": False,
        "needs_live_tau2_executor": by_executor.get("tau2_r6_controlled_user", 0) > 0,
        "needs_environment": 0,
        "by_executor": dict(by_executor),
        "by_domain": dict(Counter(c["domain"] for c in cells)),
        "models": sorted({c["model_alias"] for c in cells}),
        "conditions": sorted({c["condition_id"] for c in cells}),
        "n_tasks": len({c["task_id"] for c in cells}),
    }
    (out_dir / "run_plan_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _config_path(config: dict[str, Any], primary: str, fallback: Path, *aliases: str) -> Path:
    value = config.get(primary)
    if value is None and isinstance(config.get("data"), dict):
        for key in (primary, *aliases):
            value = config["data"].get(key)
            if value is not None:
                break
    return Path(value or fallback)


def resolve_runtime_paths(config: dict[str, Any], tasks_data: str | Path) -> dict[str, Path]:
    return {
        "tasks_path": Path(tasks_data or config.get("task_file") or "data/r6/r6_tasks.yaml"),
        "templates_path": _config_path(config, "template_file", DEFAULT_TEMPLATES, "templates"),
        "user_policies_path": _config_path(config, "user_policies", DEFAULT_USER_POLICIES),
        "annotations_path": _config_path(config, "policy_annotations", DEFAULT_ANNOTATIONS),
        "seed_states_path": _config_path(config, "seed_states", DEFAULT_SEED_STATES, "environment_seed_states"),
    }


def _abs(path: Path) -> Path:
    return ROOT / path if not path.is_absolute() else path


def run_deterministic_smoke(
    *,
    out_root: Path,
    cells: list[dict[str, Any]],
    config: dict[str, Any],
    tasks_data: str | Path,
) -> dict[str, Any]:
    paths = {key: _abs(path) for key, path in resolve_runtime_paths(config, tasks_data).items()}
    env = R6MinimalDeterministicEnvironment(**paths)
    trace_paths = []
    for cell in cells:
        trace = env.run_cell(
            R6RunCell(
                run_id=str(cell["run_id"]),
                model_alias=str(cell["model_alias"]),
                task_id=str(cell["task_id"]),
                domain=str(cell["domain"]),
                layer=str(cell["layer"]),
                condition_id=str(cell["condition_id"]),
                seed=int(cell["seed"]),
                temperature=float(cell["temperature"]),
                executor=str(cell["executor"]),
            )
        )
        trace_paths.append(write_trace(out_root, trace))
    summary = {
        "executor_mode": "deterministic_env_smoke",
        "model_call_performed": False,
        "traces_written": len(trace_paths),
        "trace_dir": str(out_root / "traces"),
        "live_tau2_executor_available": False,
        "live_model_executor_available": False,
        "warning": "These are no-model deterministic smoke traces, not live tau2/model experiment results.",
        "runtime_paths": {key: str(path) for key, path in paths.items()},
    }
    (out_root / "deterministic_smoke_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=["smoke", "pilot", "full", "preflight"], required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--tasks-data", default="data/r6/r6_tasks.yaml")
    p.add_argument("--output-root", default=None)
    p.add_argument("--dry-run", action="store_true", help="plan only; no model calls")
    p.add_argument(
        "--allow-deterministic-pilot-full",
        action="store_true",
        help="allow pilot/full to run through the no-model deterministic executor; default blocks them",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    config = load_yaml(Path(args.config))
    all_tasks = load_tasks(Path(args.tasks_data))
    cells = build_matrix(config, all_tasks)

    out_root = Path(args.output_root or config.get("output_root") or f"results/r6_sensitivity/{args.phase}")
    out_root = ROOT / out_root if not out_root.is_absolute() else out_root
    summary = write_plan(out_root, cells)
    print(json.dumps({"phase": args.phase, "output_root": str(out_root), **summary}, indent=2))

    if args.dry_run:
        print("[r6-runner] dry-run: matrix planned, no model calls.")
        return 0

    if args.phase in {"pilot", "full"} and not args.allow_deterministic_pilot_full:
        raise SystemExit(
            "[r6-runner] EXECUTION BLOCKED: "
            f"{args.phase} is a model-experiment phase, but only the no-model deterministic "
            "smoke executor is wired here. Re-run with --dry-run for planning, or pass "
            "--allow-deterministic-pilot-full only when intentionally validating pipeline scale."
        )

    deterministic_summary = run_deterministic_smoke(
        out_root=out_root,
        cells=cells,
        config=config,
        tasks_data=args.tasks_data,
    )
    print(json.dumps(deterministic_summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
