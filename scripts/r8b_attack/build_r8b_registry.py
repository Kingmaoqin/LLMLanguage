#!/usr/bin/env python3
"""R8-B: build & FREEZE the task registry for Part A / B / C (spec R8-B §3-5).

Part A  : 12 held-out multi-step tasks (retail 6 + airline 6; F1/F2 each 6). Retail
          tasks are FRESH (not used in R8-A dev/test). Airline has only 7 STRICT-gate
          tasks total, all used by R8-A -> reused here and documented (structural).
Part B  : 5 confounder modules x 3 tasks (may repeat across modules; frozen within).
Part C  : 4 boundary-control tasks.

Complexity gate (spec §3.1): official scorer available, reference actions >=5, distinct
tools >=3, >=2 natural user turns (the neutral tool-call median>=5 gate is a post-run
check). Selection is blind top-K by complexity; PASR / R8-A outcomes never used.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.run import get_tasks  # noqa: E402
from scripts.r8_full_episode.build_task_registry import MUT, NON_READ_UTIL, env_hashes, git_commit, sha  # noqa: E402
from scripts.r8_attack.build_attack_registry import classify, family_eligible, _rank_key, FAMILY_OBJECTIVE  # noqa: E402

FROZEN = ROOT / "data/r8b_attack/frozen"
R8A_REG = ROOT / "data/r8_attack/frozen/task_registry.jsonl"


def r8a_used():
    used = set()
    for l in R8A_REG.read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            used.add((r["domain"], r["tau2_task_id"]))
    return used


def eligible_pool(domain):
    recs = []
    for t in get_tasks(domain):
        c = classify(t, MUT[domain])
        if isinstance(c, dict):
            recs.append(c)
    return sorted(recs, key=_rank_key)


def main():
    FROZEN.mkdir(parents=True, exist_ok=True)
    used = r8a_used()
    pools = {d: eligible_pool(d) for d in ("retail", "airline")}
    per_env = {d: env_hashes(d) for d in ("retail", "airline")}
    taskobj = {(d, str(t.id)): t for d in ("retail", "airline") for t in get_tasks(d)}

    selected = []
    claimed = set()

    def pick(domain, family, split, k, *, allow_reuse=False, prefer_fresh=True):
        pool = [r for r in pools[domain] if family_eligible(r, family)
                and (domain, r["task_id"]) not in claimed]
        fresh = [r for r in pool if (domain, r["task_id"]) not in used]
        reused = [r for r in pool if (domain, r["task_id"]) in used]
        order = (fresh + reused) if prefer_fresh else pool
        if not allow_reuse:
            order = fresh
        if len(order) < k:
            raise SystemExit(f"INFEASIBLE {domain}/{family}/{split}: need {k}, have {len(order)} "
                             f"(fresh={len(fresh)} reused={len(reused)} allow_reuse={allow_reuse})")
        out = []
        for r in order[:k]:
            claimed.add((domain, r["task_id"]))
            t = taskobj[(domain, r["task_id"])]
            obj = FAMILY_OBJECTIVE[family]
            out.append(dict(
                part=split, domain=domain, tau2_task_id=r["task_id"], family=family,
                objective=dict(family=family, target_direction=obj["target_direction"],
                               metric=obj["metric"], direction=obj["direction"]),
                complexity=dict(n_actions=r["n_actions"], n_distinct_tools=r["n_distinct_tools"],
                                n_reads=r["n_reads"], n_mutations=r["n_mutations"]),
                reused_from_r8a=((domain, r["task_id"]) in used),
                task_hash=sha(t.model_dump_json())))
        selected.extend(out)
        return out

    # ---- Part A: 12 tasks, F1/F2 each 6, retail 6 + airline 6 ----
    # retail fresh; airline reused (only 7 gate tasks total, all in R8-A).
    pick("retail", "F1", "partA", 3, allow_reuse=False)
    pick("retail", "F2", "partA", 3, allow_reuse=False)
    pick("airline", "F1", "partA", 3, allow_reuse=True)
    pick("airline", "F2", "partA", 3, allow_reuse=True)

    # ---- Part B: 5 modules x 3 tasks (fresh retail, reuse allowed) ----
    partB_tasks = pick("retail", "F1", "partB_pool", 3, allow_reuse=True) + \
        pick("retail", "F2", "partB_pool", 3, allow_reuse=True)
    # tag module assignment: 5 modules each get 3 tasks from this 6-task pool (repeat allowed)
    modules = ["M1", "M2", "M3", "M4", "M5"]
    partB_assign = []
    for mi, mod in enumerate(modules):
        for j in range(3):
            src = partB_tasks[(mi + j) % len(partB_tasks)]
            partB_assign.append(dict(module=mod, **{k: src[k] for k in
                                ("domain", "tau2_task_id", "family", "objective", "complexity", "task_hash", "reused_from_r8a")}))

    # ---- Part C: 4 boundary tasks (fresh retail, reuse allowed) ----
    partC = pick("retail", "F2", "partC", 2, allow_reuse=True) + \
        pick("retail", "F1", "partC", 2, allow_reuse=True)

    # ---- write registry ----
    reg = dict(
        partA=[r for r in selected if r["part"] == "partA"],
        partB_pool=[r for r in selected if r["part"] == "partB_pool"],
        partB_assign=partB_assign,
        partC=[r for r in selected if r["part"] == "partC"],
    )
    (FROZEN / "r8b_task_registry.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False))

    manifest = dict(
        experiment="R8B_high_intensity_confounder_pilot",
        tau2_commit=git_commit(pathlib.Path("/home/xqin5/tau2-bench")),
        ir_mstu_commit=git_commit(ROOT),
        budget_cap_episodes=720,
        partA=dict(conditions=["H0", "H1", "H2", "H3"], tasks=12, models=3, replicates=2,
                   episodes=12 * 3 * 4 * 2, note="retail fresh; airline reused (only 7 gate tasks, structural)"),
        partB=dict(modules=modules, arms=["N0", "A0", "N1", "A1"], tasks_per_module=3, models=3,
                   replicates=2, episodes=5 * 3 * 3 * 4 * 2,
                   arm_def="N=H0 neutral, A=H3 attack; 0=confounder absent, 1=present; "
                           "interaction=(A1-N1)-(A0-N0)"),
        partC=dict(conditions=["B0", "B1", "B2"], tasks=4, models=3, replicates=2,
                   episodes=4 * 3 * 3 * 2, boundary_types=["delegation(BC-A)", "deadline(BC-D)"]),
        corrections_applied=["turn0_payload_cached_100pct", "endpoint_preserved_1to1",
                             "F2_full_support", "F3_dual_review_label"],
        models={
            "gemma4_31b": {"served_name": "openai/g4-v2-1", "api_base": "http://127.0.0.1:8005/v1"},
            "gpt_oss_120b": {"served_name": "openai/gpt-oss", "api_base": "http://127.0.0.1:8192/v1"},
            "mistral_small_3p2": {"served_name": "openai/mistral-small-3p2", "api_base": "http://127.0.0.1:8007/v1"},
        },
        env_hashes=per_env,
    )
    (FROZEN / "r8b_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    total = manifest["partA"]["episodes"] + manifest["partB"]["episodes"] + manifest["partC"]["episodes"]
    print(f"Part A={manifest['partA']['episodes']} Part B={manifest['partB']['episodes']} "
          f"Part C={manifest['partC']['episodes']} TOTAL={total} (<=720: {total<=720})")
    print(f"partA tasks: {[(r['domain'],r['tau2_task_id'],r['family'],'reuse' if r['reused_from_r8a'] else 'fresh') for r in reg['partA']]}")
    print(f"wrote {FROZEN/'r8b_task_registry.json'} and r8b_manifest.json")


if __name__ == "__main__":
    main()
