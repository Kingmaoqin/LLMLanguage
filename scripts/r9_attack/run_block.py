#!/usr/bin/env python3
"""Block execution engine (spec 17, 11, 10). Shared by dev / confirmatory / confounder.

One BLOCK = (benchmark, task, model, repeat) x ALL conditions (spec 17). Running every
condition of a block together, from a clean state, is what lets the analysis pair them
(spec 11.2) and is why an infra failure re-runs the WHOLE block, not a single arm
(spec 17). Each episode is metric-extracted (production) and appended to a JSONL sink.

The engine is deliberately condition-agnostic: it is handed the list of conditions and,
for each, a factory that builds the per-episode `UserHook`. Calibration passes only C0.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from scripts.r9_attack.adapters.base import TaskSpec
from scripts.r9_attack.attacker import HookConfig, build_hook
from scripts.r9_attack.common.episode_schema import EpisodeRecord
from scripts.r9_attack.extract_metrics import extract
from scripts.r9_attack.common import net_guard


HookFactory = Callable[[str, str], Callable[..., Any]]  # (condition, family) -> UserHook


@dataclass
class BlockPlan:
    benchmark: str
    task: TaskSpec
    model: str
    repeat: int
    family: str
    conditions: list[str]
    stage: str
    seed: int = 0


def default_hook_factory(
    *,
    priors_by_family: Optional[dict] = None,
    reviewer_a: Optional[Callable[[str, str], str]] = None,
    reviewer_b: Optional[Callable[[str, str], str]] = None,
    gen_backend: Optional[Callable[[str, str], str]] = None,
    known_tool_names: Optional[set] = None,
    max_interventions: int = 4,
) -> HookFactory:
    """Return a factory that builds the right hook for (condition, family)."""
    priors_by_family = priors_by_family or {}

    def factory(condition: str, family: str) -> Callable[..., Any]:
        cfg = HookConfig(
            condition=condition,
            family=family,
            max_interventions=max_interventions,
            priors=priors_by_family.get(family),
            reviewer_a=reviewer_a,
            reviewer_b=reviewer_b,
            gen_backend=gen_backend,
            known_tool_names=known_tool_names,
        )
        return build_hook(cfg)

    return factory


def run_block(
    adapter: Any,
    plan: BlockPlan,
    hook_factory: HookFactory,
    *,
    max_episode_steps: int = 20,
    max_block_retries: int = 1,
    on_episode: Optional[Callable[[EpisodeRecord], None]] = None,
) -> list[EpisodeRecord]:
    """Run all conditions of one block. Retries the WHOLE block on infra failure (spec 17)."""
    for attempt in range(max_block_retries + 1):
        records: list[EpisodeRecord] = []
        infra = False
        for condition in plan.conditions:
            hook = hook_factory(condition, plan.family)
            net_guard.drain_events()
            rec = adapter.run_episode(
                plan.task,
                model_alias=plan.model,
                condition=condition,
                repeat=plan.repeat,
                stage=plan.stage,
                user_hook=hook,
                seed=plan.seed,
                family=plan.family,
            )
            rec.network_events = (rec.network_events or []) + net_guard.drain_events()
            extract(rec, max_episode_steps=max_episode_steps)
            records.append(rec)
            if rec.infra_failure:
                infra = True
                break
        if not infra:
            for rec in records:
                if on_episode:
                    on_episode(rec)
            return records
        time.sleep(min(2 ** attempt, 8))
    # Exhausted retries: emit whatever we have (infra episodes are outcomes for ITT accounting).
    for rec in records:
        if on_episode:
            on_episode(rec)
    return records


def block_plans(
    tasks: list[TaskSpec],
    models: list[str],
    repeats: int,
    conditions: list[str],
    stage: str,
    family_of: Callable[[TaskSpec], str],
    seed_base: int = 0,
) -> list[BlockPlan]:
    """Enumerate every block for a stage. Deterministic order for reproducibility."""
    plans: list[BlockPlan] = []
    for task in tasks:
        for model in models:
            for rep in range(repeats):
                plans.append(
                    BlockPlan(
                        benchmark=task.benchmark,
                        task=task,
                        model=model,
                        repeat=rep,
                        family=family_of(task),
                        conditions=list(conditions),
                        stage=stage,
                        seed=seed_base + rep,
                    )
                )
    return plans
