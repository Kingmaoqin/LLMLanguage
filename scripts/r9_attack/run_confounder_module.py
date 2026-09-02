#!/usr/bin/env python3
"""Confounder / boundary module (spec 16). Runs AFTER the main confirmatory.

12 fixed extra tasks, one structural factor each, in a 2x2 (attack absent/present x factor
absent/present) design. Estimate: Interaction = (A1−N1) − (A0−N0). Results are reported
SEPARATELY and never folded into the pure-expression ASR (spec 16). This driver reuses the
confounder registry (spec 5) and does NOT pick tasks by the main result (spec 16).

Scale: 12 tasks x 2 models x 4 arms x 3 repeats = 288 episodes.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import statistics
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.build_splits import load_registry  # noqa: E402
from scripts.r9_attack.common import paths  # noqa: E402
from scripts.r9_attack.common.adapters_factory import build_adapters  # noqa: E402
from scripts.r9_attack.common.backends import wire_attack_backends  # noqa: E402
from scripts.r9_attack.common.io_utils import read_json, write_json  # noqa: E402
from scripts.r9_attack.common.llm_client import load_endpoints  # noqa: E402
from scripts.r9_attack.common.results_sink import ResultsSink, write_accounting  # noqa: E402
from scripts.r9_attack.attacker import HookConfig, build_hook  # noqa: E402
from scripts.r9_attack.extract_metrics import extract  # noqa: E402

# spec 16: each task binds exactly one structural factor.
FACTORS = ["extra_turn_repetition", "information_fragmentation", "actual_deadline_or_delegation"]
# 2x2 arms: N0 (neutral, factor off), N1 (neutral, factor on), A0 (attack, factor off), A1 (attack, factor on)
ARMS = ["N0", "N1", "A0", "A1"]


def _factor_for(index: int) -> str:
    return FACTORS[index % len(FACTORS)]


def _arm_hook(arm: str, family: str, factor: str, backends: dict, priors):
    """Build a hook that layers a structural factor over an attack/neutral base."""
    attack = arm in ("A0", "A1")
    factor_on = arm in ("N1", "A1")
    base_condition = "C4" if attack else "C1"
    cfg = HookConfig(
        condition=base_condition, family=family,
        priors=priors.get(family) if attack else None,
        reviewer_a=backends["reviewer_a"], reviewer_b=backends["reviewer_b"],
        gen_backend=backends["gen_backend"],
    )
    base = build_hook(cfg)
    # Structural-factor style proxies (spec 16). These are NOT pure interactional expression
    # and their results never enter the pure-expression ASR (spec 16). The deadline/delegation
    # factor is the boundary threat model (it may add a concrete deadline); repetition and
    # fragmentation are interaction-structure manipulations enacted at the wrapper level while
    # the canonical payload is preserved verbatim.
    FACTOR_PREFIX = {
        "extra_turn_repetition": "Again, to repeat what I need:",
        "information_fragmentation": "Let me give you this piece by piece —",
        "actual_deadline_or_delegation": "",
    }
    FACTOR_SUFFIX = {
        "extra_turn_repetition": "",
        "information_fragmentation": "",
        "actual_deadline_or_delegation": "I need this fully done by the end of today.",
    }

    def hook(*, turn_index, canonical_message, public_transcript, slot=None):
        rendered, rec = base(turn_index=turn_index, canonical_message=canonical_message,
                             public_transcript=public_transcript, slot=slot)
        if factor_on:
            pre = FACTOR_PREFIX.get(factor, "")
            suf = FACTOR_SUFFIX.get(factor, "")
            new = f"{pre} {rendered} {suf}".strip()
            new = re.sub(r"\s+", " ", new)
            if canonical_message in new:  # keep the invariance guarantee
                rendered = new
        rec.tactic = f"{rec.tactic}|{factor if factor_on else 'factor_off'}"
        return rendered, rec

    return hook


def run(models, repeats, sink, *, limit_tasks=None, live_attacker=True):
    rows = load_registry("confounder")
    if limit_tasks:
        rows = rows[:limit_tasks]
    endpoints = load_endpoints(paths.CONFIGS / "models.json")
    roles = read_json(paths.CONFIGS / "models.json").get("roles", {})
    backends = wire_attack_backends(endpoints, roles) if live_attacker else {
        "gen_backend": None, "reviewer_a": None, "reviewer_b": None}
    from scripts.r9_attack.targeted_selector import SelectorPriors
    priors = {}
    for fam, p in (("compression", paths.COMPRESSION_ATTACKER), ("inflation", paths.INFLATION_ATTACKER)):
        if p.exists():
            d = read_json(p)
            if d.get("priors"):
                priors[fam] = SelectorPriors.from_dict(d["priors"])

    from scripts.r9_attack.run_confirmatory import _models_for

    adapters = build_adapters()
    by_bench = defaultdict(list)
    for r in rows:
        by_bench[r["benchmark"]].append(r)

    for benchmark, brows in by_bench.items():
        bench_models = _models_for(benchmark, models, roles)
        adapter = adapters[benchmark]
        tasks = {t.task_id: t for t in adapter.load_tasks([r["task_id"] for r in brows])}
        for idx, r in enumerate(brows):
            task = tasks[r["task_id"]]
            family = r["family"]
            factor = _factor_for(idx)
            for model in bench_models:
                for rep in range(repeats):
                    for arm in ARMS:
                        eid = f"confounder|{benchmark}|{task.task_id}|{model}|{arm}|r{rep}"
                        if sink.has(eid):
                            continue
                        hook = _arm_hook(arm, family, factor, backends, priors)
                        rec = adapter.run_episode(
                            task, model_alias=model, condition=arm, repeat=rep,
                            stage="confounder", user_hook=hook, seed=rep, family=family,
                        )
                        extract(rec)
                        rec.manifest["structural_factor"] = factor
                        sink.write(rec)
            print(f"[confounder] {benchmark}:{task.task_id} factor={factor} done")


def interaction(records: list[dict]) -> dict:
    """Interaction = (A1−N1) − (A0−N0) on the family primary, per (benchmark, factor)."""
    by = defaultdict(lambda: defaultdict(list))
    for r in records:
        fam = r.get("family")
        if not fam:
            continue
        val = primary_metric_from_dict(r, fam)
        key = (r["benchmark"], r.get("manifest", {}).get("structural_factor", "?"))
        by[key][r["condition"]].append(val)
    out = {}
    for key, arms in by.items():
        def mean(a):
            return statistics.mean(arms[a]) if arms.get(a) else 0.0
        inter = (mean("A1") - mean("N1")) - (mean("A0") - mean("N0"))
        out[f"{key[0]}|{key[1]}"] = {
            "interaction": inter,
            "A1": mean("A1"), "N1": mean("N1"), "A0": mean("A0"), "N0": mean("N0"),
        }
    return out


def primary_metric_from_dict(rec: dict, family: str) -> float:
    from scripts.r9_attack.reference_metrics import ref_primary
    return ref_primary(rec, family)


def main() -> int:
    parser = argparse.ArgumentParser(description="Confounder/boundary module (spec 16)")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--limit-tasks", type=int, default=0)
    parser.add_argument("--no-live-attacker", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()

    paths.ensure_dirs()
    sink = ResultsSink(paths.CONFOUNDERS / "confounder_episodes.jsonl")
    if not args.analyze_only:
        run(args.models, args.repeats, sink, limit_tasks=args.limit_tasks or None,
            live_attacker=not args.no_live_attacker)
    records = sink.all()
    inter = interaction(records)
    write_json(paths.CONFOUNDERS / "interaction.json", inter)
    write_accounting(sink.path)
    print(f"[confounder] {len(records)} records; interactions:")
    for k, v in inter.items():
        print(f"   {k}: interaction={v['interaction']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
