#!/usr/bin/env python3
"""Stage 2: held-out confirmatory experiment (spec 9). Also serves dev via --stage dev.

Runs full blocks (task x model x repeat x ALL conditions) over the frozen registry. Every
frozen task enters ITT — no P-responsive per-cell filter (spec 9.3). Confirmatory uses the
six conditions C0..C5 with the frozen family attackers; dev uses the five arms N/P0..P3.

Budget (spec 9.3): 40 tasks x 2 models x 6 conditions x 5 repeats = 2400 episodes.
This script only RUNS and stores; gates + statistics live in analyze_confirmatory.py.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.build_splits import load_registry  # noqa: E402
from scripts.r9_attack.common import paths  # noqa: E402
from scripts.r9_attack.common.adapters_factory import build_adapters  # noqa: E402
from scripts.r9_attack.common.backends import wire_attack_backends  # noqa: E402
from scripts.r9_attack.common.io_utils import read_json  # noqa: E402
from scripts.r9_attack.common.llm_client import load_endpoints  # noqa: E402
from scripts.r9_attack.common.results_sink import ResultsSink, write_accounting  # noqa: E402
from scripts.r9_attack.run_block import BlockPlan, default_hook_factory, run_block  # noqa: E402
from scripts.r9_attack.targeted_selector import SelectorPriors  # noqa: E402

CONFIRMATORY_CONDITIONS = ["C0", "C1", "C2", "C3", "C4", "C5"]
DEV_CONDITIONS = ["N", "P0", "P1", "P2", "P3"]


def _load_priors() -> dict:
    priors = {}
    for fam, path in (("compression", paths.COMPRESSION_ATTACKER), ("inflation", paths.INFLATION_ATTACKER)):
        if path.exists():
            data = read_json(path)
            if data.get("priors"):
                priors[fam] = SelectorPriors.from_dict(data["priors"])
    return priors


def _models_for(benchmark: str, models: list[str], roles: dict) -> list[str]:
    """Per-benchmark target models (spec 14 reports benchmarks separately).

    ToolSandbox's agent harness rewards balanced clarify-then-act behaviour (mistral),
    while BFCL rewards raw multi-step capability (Qwen/Llama/gemma); no single local model
    clears both. Calibration's per-benchmark selection (selected_models.json) is the
    authority; the config `roles.targets_bfcl` / `roles.targets_toolsandbox` are a fallback;
    the flat `models` list is the last resort.
    """
    key = {"bfcl": "targets_bfcl", "toolsandbox": "targets_toolsandbox"}.get(benchmark)
    if key:
        if paths.SELECTED_MODELS.exists():
            sel = read_json(paths.SELECTED_MODELS)
            if sel.get(key):
                return list(sel[key])
        if roles.get(key):
            return list(roles[key])
    return models


def run(
    stage: str,
    models: list[str],
    repeats: int,
    conditions: list[str],
    sink: ResultsSink,
    *,
    limit_tasks: int | None = None,
    live_attacker: bool = True,
    max_interventions: int = 4,
    benchmarks: list[str] | None = None,
) -> None:
    registry = "test" if stage == "confirmatory" else stage
    rows = load_registry(registry)
    if benchmarks:
        rows = [r for r in rows if r["benchmark"] in benchmarks]
    if limit_tasks:
        rows = rows[:limit_tasks]

    endpoints = load_endpoints(paths.CONFIGS / "models.json")
    roles = read_json(paths.CONFIGS / "models.json").get("roles", {})
    backends = wire_attack_backends(endpoints, roles) if live_attacker else {
        "gen_backend": None, "reviewer_a": None, "reviewer_b": None,
    }
    priors = _load_priors()

    adapters = build_adapters()
    family_by_task = {(r["benchmark"], r["task_id"]): r["family"] for r in rows}

    by_bench: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        by_bench[r["benchmark"]].append(r["task_id"])

    for benchmark, task_ids in by_bench.items():
        bench_models = _models_for(benchmark, models, roles)
        adapter = adapters[benchmark]
        tasks = adapter.load_tasks(task_ids)
        for task in tasks:
            family = family_by_task[(benchmark, task.task_id)]
            known = set(task.meta.get("tool_allow_list", [])) | set(task.gt_path)
            hook_factory = default_hook_factory(
                priors_by_family=priors,
                reviewer_a=backends["reviewer_a"],
                reviewer_b=backends["reviewer_b"],
                gen_backend=backends["gen_backend"],
                known_tool_names=known,
                max_interventions=max_interventions,
            )
            for model in bench_models:
                for rep in range(repeats):
                    plan = BlockPlan(
                        benchmark=benchmark, task=task, model=model, repeat=rep,
                        family=family, conditions=conditions, stage=stage, seed=rep,
                    )
                    # Skip a fully-completed block on resume.
                    if all(sink.has(f"{stage}|{benchmark}|{task.task_id}|{model}|{c}|r{rep}") for c in conditions):
                        continue
                    run_block(adapter, plan, hook_factory, on_episode=sink.write)
                    print(f"[{stage}] block {benchmark}:{task.task_id} {model} r{rep} ({family}) done")


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1 dev / Stage 2 confirmatory runner (spec 8/9)")
    parser.add_argument("--stage", choices=["dev", "confirmatory"], default="confirmatory")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--limit-tasks", type=int, default=0)
    parser.add_argument("--conditions", nargs="*", default=None)
    parser.add_argument("--no-live-attacker", action="store_true",
                        help="run without reviewer LLMs (program-guard only; smoke)")
    parser.add_argument("--benchmarks", nargs="*", default=None,
                        help="restrict to these benchmarks (default: both)")
    args = parser.parse_args()

    paths.ensure_dirs()
    conditions = args.conditions or (DEV_CONDITIONS if args.stage == "dev" else CONFIRMATORY_CONDITIONS)
    sink = ResultsSink((paths.DEV if args.stage == "dev" else paths.CONFIRMATORY) / f"{args.stage}_episodes.jsonl")
    run(args.stage, args.models, args.repeats, conditions, sink,
        limit_tasks=args.limit_tasks or None, live_attacker=not args.no_live_attacker,
        benchmarks=args.benchmarks)
    acct = write_accounting(sink.path)
    print(f"[{args.stage}] accounting: {acct['n_records']} records, "
          f"blocks={acct['n_blocks']}, outcomes={acct['outcome_classes']}, "
          f"net_events={acct['outbound_network_events']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
