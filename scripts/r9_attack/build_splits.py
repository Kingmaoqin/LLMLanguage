#!/usr/bin/env python3
"""Data splitting + freezing (spec 5). Calibration / dev / held-out, non-overlapping.

Splits are decided ONLY from benchmark metadata and neutral-only complexity (spec 5) with
a fixed seed. They are FORBIDDEN to depend on PASR, R8 cases, attack results, or a model's
attack sensitivity (spec 5). Each task is assigned a family so the family split is balanced
across both benchmarks. All registries + a manifest + a hash file are frozen to disk.

Sizes (spec 6.2 / 8.1 / 9.1):
  calibration : 16 BFCL + 16 ToolSandbox = 32
  dev         :  8 BFCL +  8 ToolSandbox = 16   (compression 8, inflation 8)
  test        : 24 BFCL + 16 ToolSandbox = 40   (compression 20, inflation 20)
  confounder  : 12 tasks (spec 16)
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys
from dataclasses import dataclass
from typing import Any, Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.adapters.base import TaskSpec  # noqa: E402
from scripts.r9_attack.attack_families import COMPRESSION, INFLATION  # noqa: E402
from scripts.r9_attack.common import paths  # noqa: E402
from scripts.r9_attack.common.io_utils import (  # noqa: E402
    git_commit,
    read_jsonl,
    sha256_file,
    write_json,
    write_jsonl,
)

SPLIT_SEED = 20260722

SIZES = {
    "calibration": {"bfcl": 16, "toolsandbox": 16},
    "dev": {"bfcl": 8, "toolsandbox": 8},
    "test": {"bfcl": 24, "toolsandbox": 16},
    "confounder": {"bfcl": 6, "toolsandbox": 6},
}


@dataclass
class Split:
    calibration: list[dict]
    dev: list[dict]
    test: list[dict]
    confounder: list[dict]


def _task_row(task: TaskSpec, family: str, split: str) -> dict:
    return {
        "benchmark": task.benchmark,
        "task_id": task.task_id,
        "family": family,
        "split": split,
        "n_user_turns": task.n_user_turns,
        "n_reference_actions": task.n_reference_actions,
        "n_distinct_tools": task.n_distinct_tools,
        "n_milestones": task.n_milestones,
        "canonical_hashes": task.canonical_hashes,
        "min_prereq_verification_calls": task.min_prereq_verification_calls,
        "min_viable_total_verification_calls": task.min_viable_total_verification_calls,
    }


def is_mutating(task: TaskSpec) -> bool:
    """True iff the task's ground-truth path contains a state-changing (mutating) action.

    Decided from task METADATA (never from any experimental outcome). The Compression
    primary metric = read/check calls BEFORE the first correct state-changing action;
    it is only well-defined when a mutation exists, otherwise every episode collapses to
    the no_state_change sentinel and the metric is insensitive (this masked the C5
    positive control in the pilot). Compression tasks must therefore be mutating tasks.
    """
    m = task.meta or {}
    return bool(m.get("gt_mutating_functions") or m.get("mutating_tools"))


def _assign_families(tasks: list[TaskSpec], rng: random.Random) -> list[tuple[TaskSpec, str]]:
    """Assign families so Compression only ever lands on MUTATING tasks (P1).

    Mutating tasks are split between the two families (Compression needs them; Inflation
    can use them too); any read-only tasks go to Inflation. Balanced as evenly as the pool
    allows. Assignment uses only task metadata, not any pilot result.
    """
    mutating = sorted([t for t in tasks if is_mutating(t)], key=lambda t: t.task_id)
    readonly = sorted([t for t in tasks if not is_mutating(t)], key=lambda t: t.task_id)
    rng.shuffle(mutating)
    rng.shuffle(readonly)
    out: list[tuple[TaskSpec, str]] = []
    # Half the mutating tasks -> Compression; the rest of mutating + all read-only -> Inflation.
    n_comp = len(mutating) // 2
    for i, t in enumerate(mutating):
        out.append((t, COMPRESSION if i < n_comp else INFLATION))
    for t in readonly:
        out.append((t, INFLATION))
    rng.shuffle(out)
    return out


MIN_USER_TURNS = 3  # P3: exposure floor — enough turns for >=1 intervention after the first


def build_splits(
    bfcl_tasks: list[TaskSpec],
    ts_tasks: list[TaskSpec],
    *,
    seed: int = SPLIT_SEED,
    sizes: Optional[dict] = None,
    min_turns: int = MIN_USER_TURNS,
) -> Split:
    """Partition eligible, complexity-passing tasks into the four non-overlapping splits.

    Family assignment (compression<->mutating, P1) is done ONCE at the pool level from task
    metadata; every split then draws balanced counts per family. Tasks must also clear the
    exposure floor of `min_turns` user turns (P3) so an attack can place >=1 intervention
    after the first turn (spec 2). Both filters use metadata only, never a pilot outcome.
    """
    sizes = sizes or SIZES
    rng = random.Random(seed)

    # Spec 6.2 complexity floor + P3 exposure floor, on neutral metadata only.
    bfcl_ok = [t for t in bfcl_tasks if t.complexity_ok() and t.n_user_turns >= min_turns]
    ts_ok = [t for t in ts_tasks if t.complexity_ok() and t.n_user_turns >= min_turns]

    # Assign families once per benchmark pool (compression only on mutating tasks, P1),
    # then partition each family's pool across splits so no task repeats.
    def family_pools(pool: list[TaskSpec]) -> dict[str, list[TaskSpec]]:
        assigned = _assign_families(pool, rng)
        out: dict[str, list[TaskSpec]] = {COMPRESSION: [], INFLATION: []}
        for t, fam in assigned:
            out[fam].append(t)
        return out

    bfcl_fam = family_pools(bfcl_ok)
    ts_fam = family_pools(ts_ok)
    cursors = {("bfcl", COMPRESSION): 0, ("bfcl", INFLATION): 0,
               ("toolsandbox", COMPRESSION): 0, ("toolsandbox", INFLATION): 0}
    fam_pool = {"bfcl": bfcl_fam, "toolsandbox": ts_fam}

    result: dict[str, list[dict]] = {}
    for split in ("calibration", "dev", "test", "confounder"):
        rows: list[dict] = []
        for bench in ("bfcl", "toolsandbox"):
            n = sizes[split].get(bench, 0)
            half = n // 2
            want = {COMPRESSION: half, INFLATION: n - half}
            for fam in (COMPRESSION, INFLATION):
                pool = fam_pool[bench][fam]
                start = cursors[(bench, fam)]
                picked = pool[start:start + want[fam]]
                cursors[(bench, fam)] = start + len(picked)
                for task in picked:
                    rows.append(_task_row(task, fam, split))
        result[split] = rows

    return Split(
        calibration=result["calibration"],
        dev=result["dev"],
        test=result["test"],
        confounder=result["confounder"],
    )


def freeze(split: Split, manifest_extra: Optional[dict] = None) -> dict[str, Any]:
    paths.ensure_dirs()
    write_jsonl(paths.CALIBRATION_REGISTRY, split.calibration)
    write_jsonl(paths.DEV_REGISTRY, split.dev)
    write_jsonl(paths.TEST_REGISTRY, split.test)
    write_jsonl(paths.CONFOUNDER_REGISTRY, split.confounder)

    files = [paths.CALIBRATION_REGISTRY, paths.DEV_REGISTRY, paths.TEST_REGISTRY, paths.CONFOUNDER_REGISTRY]
    lines = [f"{sha256_file(f)}  {f.relative_to(ROOT)}" for f in files]
    from scripts.r9_attack.common.io_utils import write_atomic

    write_atomic(paths.SPLIT_HASHES, "\n".join(lines) + "\n")

    # Assert non-overlap (spec 5).
    ids: dict[str, set] = {}
    for name, rows in (("calibration", split.calibration), ("dev", split.dev),
                       ("test", split.test), ("confounder", split.confounder)):
        ids[name] = {(r["benchmark"], r["task_id"]) for r in rows}
    overlaps = {}
    names = list(ids)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            common = ids[names[i]] & ids[names[j]]
            if common:
                overlaps[f"{names[i]}∩{names[j]}"] = sorted(f"{b}:{t}" for b, t in common)

    manifest = {
        "seed": SPLIT_SEED,
        "sizes": {k: {kk: len([r for r in getattr(split, k) if r["benchmark"] == kk]) for kk in ("bfcl", "toolsandbox")}
                  for k in ("calibration", "dev", "test", "confounder")},
        "counts": {k: len(getattr(split, k)) for k in ("calibration", "dev", "test", "confounder")},
        "family_balance": {
            k: {fam: len([r for r in getattr(split, k) if r["family"] == fam]) for fam in (COMPRESSION, INFLATION)}
            for k in ("calibration", "dev", "test", "confounder")
        },
        "overlaps": overlaps,
        "non_overlapping": not overlaps,
        "git_commit": git_commit(),
        **(manifest_extra or {}),
    }
    write_json(paths.ENVIRONMENT_MANIFEST, manifest)
    return manifest


def load_registry(split: str) -> list[dict]:
    path = {
        "calibration": paths.CALIBRATION_REGISTRY,
        "dev": paths.DEV_REGISTRY,
        "test": paths.TEST_REGISTRY,
        "confounder": paths.CONFOUNDER_REGISTRY,
    }[split]
    return list(read_jsonl(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze R9 splits (spec 5)")
    parser.add_argument("--models", default=str(paths.CONFIGS / "models.json"))
    parser.add_argument("--ledgers", default=str(paths.FACT_LEDGERS))
    parser.add_argument("--bfcl-limit", type=int, default=0, help="limit BFCL tasks scanned (smoke)")
    parser.add_argument("--sizes-json", default="", help="JSON overriding per-split per-benchmark sizes")
    args = parser.parse_args()

    sizes = SIZES
    if args.sizes_json:
        import json as _json
        sizes = _json.loads(args.sizes_json)

    from scripts.r9_attack.adapters.bfcl_adapter import BfclAdapter
    from scripts.r9_attack.adapters.toolsandbox_adapter import ToolSandboxAdapter

    bfcl = BfclAdapter(endpoints={})
    bfcl_ids = None
    if args.bfcl_limit:
        bfcl_ids = [f"multi_turn_base_{i}" for i in range(args.bfcl_limit)]
    bfcl_tasks = bfcl.load_tasks(bfcl_ids)

    ts = ToolSandboxAdapter(endpoints={}, ledger_path=pathlib.Path(args.ledgers))
    # Only use ToolSandbox scenarios whose neutral pre-pass reached >0 milestone (usable).
    ts_tasks = []
    if ts._ledgers:
        usable = [name for name, led in ts._ledgers.items()
                  if led.get("prepass", {}).get("milestone_similarity", 0) > 0]
        ts_tasks = ts.load_tasks(sorted(usable))

    split = build_splits(bfcl_tasks, ts_tasks, sizes=sizes)
    manifest = freeze(split)
    print(f"[splits] counts={manifest['counts']} non_overlapping={manifest['non_overlapping']}")
    print(f"[splits] family_balance={manifest['family_balance']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
