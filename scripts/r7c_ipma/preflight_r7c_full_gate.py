#!/usr/bin/env python3
"""Fail-closed preflight gate for R7-C smoke/full execution.

This script is intentionally non-executing: it does not call model endpoints and
does not write traces. It verifies whether the frozen task/config state is large
enough to begin R7-C smoke/full runs under the proposal constraints.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import CONDITIONS, read_jsonl, write_md


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def template_coverage(templates_path: Path, task_ids: list[str], conditions: list[str]) -> tuple[int, list[str]]:
    rows = read_jsonl(templates_path)
    by_key: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        by_key[(str(row.get("task_id")), str(row.get("condition")))] += 1
    missing = [
        f"{task_id}::{condition}"
        for task_id in task_ids
        for condition in conditions
        if by_key[(task_id, condition)] == 0
    ]
    return len(rows), missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=ROOT / "data/r7c_ipma/r7c_task_registry.csv")
    ap.add_argument("--config", type=Path, default=ROOT / "configs/r7b_ipma/r7b_full.yaml")
    ap.add_argument("--templates", type=Path, default=ROOT / "data/r7b_ipma/frozen/r7b_frozen_templates.jsonl")
    ap.add_argument("--min-tasks", type=int, default=48)
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7c_ipma/R7C_FULL_PREFLIGHT_GATE_CN.md")
    ap.add_argument("--out-json", type=Path, default=ROOT / "results/r7c_ipma/r7c_full_preflight_gate.json")
    args = ap.parse_args()

    config = load_yaml(args.config)
    registry = read_csv(args.registry)
    task_split = config.get("task_split", "test")
    models = list(config.get("models") or [])
    seeds = [int(s) for s in config.get("seeds") or []]
    conditions = list(config.get("conditions") or [])
    selected = [
        row
        for row in registry
        if row.get("endpoint_oracle_supported") == "True"
        and (not task_split or row.get("dev_or_test") == task_split)
    ]
    task_ids = [row["task_id"] for row in selected]
    n_templates, missing_templates = template_coverage(args.templates, task_ids, conditions)
    n_cells = len(task_ids) * len(conditions) * len(seeds) * len(models)
    expected_min_cells = args.min_tasks * len(conditions) * len(seeds) * len(models)
    failures = []
    if len(task_ids) < args.min_tasks:
        failures.append(f"endpoint_supported_{task_split}_tasks={len(task_ids)} < {args.min_tasks}")
    if conditions != CONDITIONS:
        failures.append(f"conditions_mismatch: {conditions} != {CONDITIONS}")
    if len(models) != 3:
        failures.append(f"model_count={len(models)} != 3")
    if len(seeds) != 3:
        failures.append(f"seed_count={len(seeds)} != 3")
    if missing_templates:
        failures.append(f"missing_template_cells={len(missing_templates)}")

    result = {
        "gate_pass": not failures,
        "failures": failures,
        "registry": str(args.registry),
        "config": str(args.config),
        "templates": str(args.templates),
        "task_split": task_split,
        "n_endpoint_supported_tasks": len(task_ids),
        "min_tasks_required": args.min_tasks,
        "models": models,
        "conditions": conditions,
        "seeds": seeds,
        "planned_cells": n_cells,
        "minimum_cells_required": expected_min_cells,
        "domain_counts": dict(Counter(row.get("domain", "") for row in selected)),
        "family_counts": dict(Counter(row.get("task_family_primary", "") for row in selected)),
        "n_templates": n_templates,
        "missing_template_cells": missing_templates[:50],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(
        args.report,
        f"""# R7-C full preflight gate

- gate_pass: {result['gate_pass']}
- failures: {failures or '[]'}
- endpoint-supported {task_split} tasks: {len(task_ids)}
- minimum required tasks: {args.min_tasks}
- planned cells: {n_cells}
- minimum required cells: {expected_min_cells}
- models: {models}
- seeds: {seeds}
- conditions: {conditions}
- missing template cells: {len(missing_templates)}

结论：{"可以进入 R7-C full/smoke 前置阶段。" if result['gate_pass'] else "不得启动 R7-C full rerun；当前配置不满足 proposal-consistent 最低规模。"}

## task expansion dependency

新增 endpoint-supported task 不能只追加 registry 行。当前 live runner 还要求以下资产同步存在并冻结：

- `data/r6/r6_tasks.yaml` 中的 runnable task spec；
- `data/r6/r6_task_policy_annotations.yaml` 中的 expected field diffs、confirmation/refusal/privacy/unsafe annotations；
- `data/r6/r6_task_user_policies.yaml` 中的 deterministic user policy；
- seed state family / initial-state hash；
- R7-C condition templates 与 per-condition template coverage；
- task family、PASR threshold、endpoint evaluator hash 与 freeze manifest。

`data/stage2_5b/candidate_tasks.csv` 是结构候选清单，不是 runnable frozen task registry。不得把 candidate row 直接标为 `endpoint_oracle_supported=True` 进入 full run。

机器表：`{args.out_json}`
""",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
