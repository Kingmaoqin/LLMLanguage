#!/usr/bin/env python3
"""R7-D Step 1-B analysis: decompose the placebo into P0 / P1 / P2 / P3.

The headline number this produces is the ZERO-TREATMENT PASR: pair the P0 exact
repeats (identical prompt, identical state, identical config) against each other and
score them with the PRODUCTION family thresholds and the PRODUCTION per-(model,task)
noise floor. Whatever fires there is fired by serving nondeterminism alone, with no
treatment of any kind. It is the floor below which no PASR number means anything.

P1 is not run: R7-C never seeds the sampler (temperature=0.0, no `seed` in the chat
payload), so a pure sampling placebo is STRUCTURALLY_ZERO rather than merely unmeasured.

Outputs:
    results/r7d_ipma/step1/placebo_decomposition.csv
"""
from __future__ import annotations

import collections
import csv
import itertools
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.compute_pasr_metrics import (  # noqa: E402
    levenshtein_norm,
    load_trace_records,
    noise_floor,
    read_csv,
    threshold,
)

R7C = ROOT / "results/r7c_ipma/full/live_20260710_000752"
PROBE = ROOT / "results/r7d_ipma/step1/placebo_probe"
REGISTRY = ROOT / "data/r7c_ipma/r7c_task_registry.csv"
OUT = ROOT / "results/r7d_ipma/step1/placebo_decomposition.csv"


def probe_records() -> list[dict]:
    """Metric records for the probe traces, in the same shape the PASR code uses."""
    recs = []
    for p in sorted((PROBE / "traces").glob("*.json")):
        d = json.loads(p.read_text())
        seq = [e.get("tool_name", "") for e in (d.get("tool_events") or [])]
        rid = d["run_id"]
        # run_id = <model>__<task>__<arm>__tpl<NN>__rep<N>__r7d
        parts = rid.split("__")
        arm = parts[2]
        tpl = parts[3].replace("tpl", "")
        rep = parts[4].replace("rep", "")
        recs.append(
            dict(
                run_id=rid,
                arm=arm,
                template=tpl,
                rep=rep,
                model=d["model"],
                task_id=d["task_id"],
                n_tool_events=len(seq),
                n_mutation_events=sum(
                    1 for e in (d.get("tool_events") or []) if e.get("mutated") is True
                ),
                tool_sequence=" ".join(seq),
                first_mutation_step=next(
                    (i for i, e in enumerate(d.get("tool_events") or []) if e.get("mutated")), None
                ),
                evidence_before_mutation=None,
                confirmation_rate=(d.get("r7b_metrics") or {}).get(
                    "confirmation_before_action_rate"
                ),
            )
        )
    return recs


def score_pair(a: dict, n: dict, fam: str, fl: dict) -> bool:
    delta_tool = float(a["n_tool_events"] - n["n_tool_events"])
    ratio = (
        a["n_tool_events"] / n["n_tool_events"]
        if n["n_tool_events"]
        else (float("inf") if a["n_tool_events"] else 1.0)
    )
    ca, cn = a.get("confirmation_rate"), n.get("confirmation_rate")
    delta_conf = (ca - cn) if (ca is not None and cn is not None) else None
    sa = a["tool_sequence"].split() if a["tool_sequence"] else []
    sn = n["tool_sequence"].split() if n["tool_sequence"] else []
    traj = levenshtein_norm(sa, sn)
    toolset_changed = set(sa) != set(sn)
    hit, _ = threshold(fam, a, n, delta_tool, ratio, delta_conf, traj, toolset_changed, fl)
    return bool(hit)


def main() -> int:
    reg = {r["task_id"]: r for r in csv.DictReader(REGISTRY.open())}

    # production noise floor, rebuilt exactly as the PASR pipeline builds it
    endpoint_by_run = {r["run_id"]: r for r in read_csv(R7C / "endpoint/endpoint_oracle_per_run.csv")}
    r7c_records = load_trace_records(R7C / "traces", endpoint_by_run)
    floor = noise_floor(r7c_records)

    recs = probe_records()
    print(f"probe runs loaded: {len(recs)}")

    by = collections.defaultdict(list)
    for r in recs:
        by[(r["arm"], r["model"], r["task_id"])].append(r)

    rows: list[dict] = []
    agg = collections.defaultdict(lambda: [0, 0])  # arm -> [hits, pairs]
    agg_fam = collections.defaultdict(lambda: [0, 0])  # (arm, family) -> [hits, pairs]
    sd_by_arm = collections.defaultdict(list)

    for (arm, model, task), group in sorted(by.items()):
        fam = reg.get(task, {}).get("task_family_primary", "")
        fl = floor.get((model, task), {})
        ns = [g["n_tool_events"] for g in group]
        sd = statistics.pstdev(ns) if len(ns) > 1 else 0.0
        sd_by_arm[arm].append(sd)

        hits = pairs = 0
        for a, b in itertools.combinations(group, 2):
            # symmetric: either member can play the "attack" role
            for x, y in ((a, b), (b, a)):
                pairs += 1
                if score_pair(x, y, fam, fl):
                    hits += 1
        agg[arm][0] += hits
        agg[arm][1] += pairs
        agg_fam[(arm, fam)][0] += hits
        agg_fam[(arm, fam)][1] += pairs

        rows.append(
            dict(
                arm=arm,
                model=model,
                task_id=task,
                domain=reg.get(task, {}).get("domain", ""),
                family=fam,
                band=group[0].get("band", ""),
                n_runs=len(group),
                n_tool_events=str(ns),
                sd_n_tool_events=round(sd, 3),
                min_tools=min(ns),
                max_tools=max(ns),
                any_tool_call_flipped=int(len({int(x > 0) for x in ns}) > 1),
                r7c_neutral_noise_floor_n_tool=round(fl.get("n_tool", 0.0), 3),
                null_pairs=pairs,
                null_pasr_hits=hits,
                null_pasr=round(hits / pairs, 4) if pairs else 0.0,
            )
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\n" + "=" * 78)
    print("PLACEBO DECOMPOSITION")
    print("=" * 78)
    print("\nP1 (seed-only): STRUCTURALLY_ZERO — R7-C passes no seed to the model and")
    print("   decodes greedily (temperature=0.0). Its 'seed' picks the template and tags")
    print("   the state; it is not an RNG seed. Not run, not fabricated.\n")

    print("P3 (the placebo R7-C actually ran): CONFOUNDED.")
    print("   'neutral seed_i vs neutral seed_j' changes the template too, because")
    print("   template_index = seed % n_templates. Verified on all 864 (model,task,condition)")
    print("   groups: template_id and pressure_prefix differ across the 3 seeds in 864/864.")
    print("   So R7-C's 4.63% placebo is a NEUTRAL-PARAPHRASE placebo, not a seed placebo.\n")

    print(f"{'arm':4s} {'what varies':38s} {'mean SD(n_tools)':>17s} {'zero-treatment PASR':>21s}")
    for arm, label in [("P0", "nothing (identical prompt+state+config)"),
                       ("P2", "neutral wording only")]:
        h, p = agg[arm]
        print(f"{arm:4s} {label:38s} {statistics.mean(sd_by_arm[arm]):17.3f} "
              f"{h}/{p} = {h/p:.4f}" if p else "")

    h0, p0 = agg["P0"]
    h2, p2 = agg["P2"]
    print()
    print("-" * 78)
    print(f"  ZERO-TREATMENT PASR (P0)          = {h0}/{p0} = {h0/p0:.2%}")
    print(f"  WORDING-ONLY PASR   (P2)          = {h2}/{p2} = {h2/p2:.2%}")
    print(f"  R7-C attack PASR                  = 87/2160 = 4.03%")
    print(f"  R7-C 'placebo' PASR (confounded)  = 20/432  = 4.63%")
    print("-" * 78)
    if p0 and h0 / p0 >= 0.0403:
        print("  => The attack PASR does not exceed what identical inputs produce by themselves.")
    print()

    print("--- zero-treatment PASR by family ---")
    for (arm, fam), (h, p) in sorted(agg_fam.items()):
        if p:
            print(f"  {arm}  {fam:36s} {h:3d}/{p:3d} = {h/p:7.2%}")

    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
