"""Task-cluster bootstrap utilities for Stage-2.5b paired contrasts."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np


def task_cluster_bootstrap(
    rows: Iterable[dict[str, object]],
    *,
    value_key: str = "delta",
    task_key: str = "task_id",
    n_boot: int = 10_000,
    seed: int = 20260618,
) -> dict[str, float | int]:
    """Bootstrap the mean paired delta by resampling task clusters with replacement."""
    by_task: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = row.get(value_key)
        if value is None:
            continue
        by_task[str(row[task_key])].append(float(value))
    tasks = sorted(by_task)
    values = {task: np.asarray(by_task[task], dtype=float) for task in tasks}
    observed_values = np.concatenate([values[task] for task in tasks]) if tasks else np.asarray([])
    observed = float(observed_values.mean()) if observed_values.size else float("nan")
    if not tasks:
        return {
            "estimate": observed,
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "p_value": float("nan"),
            "n_pairs": 0,
            "n_tasks": 0,
            "n_boot": n_boot,
        }

    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot, dtype=float)
    for index in range(n_boot):
        sampled = rng.choice(tasks, size=len(tasks), replace=True)
        boot[index] = np.concatenate([values[task] for task in sampled]).mean()
    ci_low, ci_high = np.quantile(boot, [0.025, 0.975])
    p_value = min(
        1.0,
        2.0 * min(
            (np.count_nonzero(boot <= 0.0) + 1) / (n_boot + 1),
            (np.count_nonzero(boot >= 0.0) + 1) / (n_boot + 1),
        ),
    )
    return {
        "estimate": observed,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "p_value": float(p_value),
        "n_pairs": int(observed_values.size),
        "n_tasks": len(tasks),
        "n_boot": n_boot,
    }


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Return Benjamini-Hochberg adjusted p-values in original order."""
    count = len(p_values)
    if not count:
        return []
    order = np.argsort(np.asarray(p_values, dtype=float))
    adjusted = np.empty(count, dtype=float)
    running = 1.0
    for rank_index in range(count - 1, -1, -1):
        original_index = int(order[rank_index])
        rank = rank_index + 1
        running = min(running, float(p_values[original_index]) * count / rank)
        adjusted[original_index] = min(1.0, running)
    return adjusted.tolist()
