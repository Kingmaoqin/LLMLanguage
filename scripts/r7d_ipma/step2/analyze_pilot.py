#!/usr/bin/env python3
"""R7-D Step 2 minimal-pilot analysis + empirical gates.

Reads per_suffix_metrics.csv and produces, per the frozen analysis plan:
  - S0 snapshot fidelity from the N0 exact-repeat branch
  - positive-control check from P vs N1
  - primary A-N1 per stratum (T1: n_tool_events, increase; T2: first_mutation_step, decrease)
  - secondary contrasts S-N1, A-S, P-N1, N1-N0
  - endpoint preservation (A vs N1 reward)
  - concentration / leave-one-out
  - paired task-cluster bootstrap CIs + branch-label permutation test

Everything is labelled preliminary: the minimal pilot yields NO S2 decision.

Outputs into results/r7d_ipma/step2/analysis/.
"""
from __future__ import annotations

import collections
import csv
import itertools
import json
import math
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
IN = ROOT / "results/r7d_ipma/step2/metrics/per_suffix_metrics.csv"
OUTD = ROOT / "results/r7d_ipma/step2/analysis"
RNG = random.Random(20260711)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load():
    # merge the main pilot CSV with any side files (e.g. gemma re-run into gemma_blocks.csv)
    files = [IN]
    side = IN.parent / "gemma_blocks.csv"
    if side.exists():
        files.append(side)
    rows = []
    for f in files:
        rows += [r for r in csv.DictReader(f.open()) if r.get("branch") in ("N0", "N1", "S", "A", "P")]
    for r in rows:
        for k in ("n_tool_events", "n_reads", "n_duplicate_reads", "n_mutations",
                  "first_mutation_step", "evidence_before_first_mutation",
                  "endpoint_reward", "suffix_len_turns", "replicate"):
            r[k] = fnum(r.get(k))
    return rows


def paired_cells(rows, metric, br_a, br_b):
    """Return list of (task_uid, model, replicate, a_val, b_val) present in both branches."""
    idx = {}
    for r in rows:
        idx[(r["block_id"], r["branch"])] = r.get(metric)
    blocks = sorted({r["block_id"] for r in rows})
    meta = {r["block_id"]: r for r in rows}
    out = []
    for b in blocks:
        a, bb = idx.get((b, br_a)), idx.get((b, br_b))
        if a is not None and bb is not None:
            out.append((meta[b]["task_uid"], meta[b]["model"], b, a, bb))
    return out


def task_cluster_bootstrap(pairs, nboot=10000):
    """pairs: list of (task_uid, model, block, a, b). Resample TASKS with replacement."""
    if not pairs:
        return (float("nan"), float("nan"), float("nan"))
    by_task = collections.defaultdict(list)
    for tu, model, blk, a, b in pairs:
        by_task[tu].append(a - b)
    tasks = list(by_task)
    point = statistics.mean([d for tu in tasks for d in by_task[tu]])
    boots = []
    for _ in range(nboot):
        picked = [RNG.choice(tasks) for _ in tasks]
        vals = [d for tu in picked for d in by_task[tu]]
        boots.append(statistics.mean(vals))
    boots.sort()
    return point, boots[int(0.025 * nboot)], boots[int(0.975 * nboot)]


def permutation_test(pairs, nperm=10000):
    """Sign-flip permutation on the paired differences (branch-label swap)."""
    diffs = [a - b for _, _, _, a, b in pairs]
    if not diffs:
        return float("nan")
    obs = abs(statistics.mean(diffs))
    cnt = 0
    for _ in range(nperm):
        s = sum(d if RNG.random() < 0.5 else -d for d in diffs) / len(diffs)
        if abs(s) >= obs:
            cnt += 1
    return (cnt + 1) / (nperm + 1)


def contrast(rows, metric, br_a, br_b, label):
    pairs = paired_cells(rows, metric, br_a, br_b)
    point, lo, hi = task_cluster_bootstrap(pairs)
    p = permutation_test(pairs)
    # leave-one-task-out
    by_task = collections.defaultdict(list)
    for tu, model, blk, a, b in pairs:
        by_task[tu].append(a - b)
    loo = {}
    tasks = list(by_task)
    for t in tasks:
        rest = [d for tt in tasks if tt != t for d in by_task[tt]]
        loo[t] = statistics.mean(rest) if rest else float("nan")
    return dict(contrast=label, metric=metric, n_pairs=len(pairs),
                mean_diff=round(point, 4), ci_low=round(lo, 4), ci_high=round(hi, 4),
                perm_p=round(p, 4),
                per_task_mean={t: round(statistics.mean(v), 3) for t, v in by_task.items()},
                leave_one_task_out={t: round(v, 4) for t, v in loo.items()})


def main() -> int:
    OUTD.mkdir(parents=True, exist_ok=True)
    rows = load()
    strata = {r["block_id"]: r["stratum"] for r in rows}
    print(f"loaded {len(rows)} suffix rows across {len({r['block_id'] for r in rows})} blocks")

    # ---- S0 snapshot fidelity: N0 exact repeats across the 2 replicates ----
    n0 = collections.defaultdict(dict)  # (task,model) -> {rep: n0_row}
    for r in rows:
        if r["branch"] == "N0":
            n0[(r["task_uid"], r["model"])][r["replicate"]] = r
    s0 = []
    for (tu, model), reps in n0.items():
        seqs = {rep: rr["tool_sequence"] for rep, rr in reps.items()}
        tools = {rep: rr["n_tool_events"] for rep, rr in reps.items()}
        s0.append(dict(task_uid=tu, model=model, n_replicates=len(reps),
                       n0_tool_sequences=list(seqs.values()),
                       identical_across_replicates=len(set(seqs.values())) == 1,
                       n_tool_range=[min(tools.values()), max(tools.values())] if tools else None))
    (OUTD / "snapshot_fidelity_s0.json").write_text(json.dumps(s0, indent=2, ensure_ascii=False))
    ident = sum(1 for x in s0 if x["identical_across_replicates"])
    print(f"S0: {ident}/{len(s0)} (task,model) have identical N0 exact-repeat tool sequences")

    # ---- primary per stratum ----
    results = []
    t1_rows = [r for r in rows if r["stratum"] == "T1"]
    t2_rows = [r for r in rows if r["stratum"] == "T2"]
    results.append(("T1_primary", contrast(t1_rows, "n_tool_events", "A", "N1", "A-N1 (T1 tool intensity)")))
    results.append(("T2_primary", contrast(t2_rows, "first_mutation_step", "A", "N1", "A-N1 (T2 mutation timing)")))

    # ---- secondary contrasts (both strata pooled where sensible) ----
    sec = []
    for (br_a, br_b, lab) in [("S", "N1", "S-N1"), ("A", "S", "A-S"), ("P", "N1", "P-N1"), ("N1", "N0", "N1-N0")]:
        sec.append(contrast(t1_rows, "n_tool_events", br_a, br_b, f"{lab} (T1 tools)"))
        sec.append(contrast(t2_rows, "first_mutation_step", br_a, br_b, f"{lab} (T2 mut-step)"))

    # ---- positive control gate: P vs N1 in the intended direction ----
    p_t1 = contrast(t1_rows, "n_tool_events", "P", "N1", "P-N1 T1")   # expect P>=N1 tools (extra recheck)
    p_t2 = contrast(t2_rows, "evidence_before_first_mutation", "P", "N1", "P-N1 T2 evidence")  # expect P>=N1 evidence
    pos_gate = dict(
        T1_P_minus_N1_tools=p_t1["mean_diff"],
        T2_P_minus_N1_evidence=p_t2["mean_diff"],
        note="positive control P asks for an extra recheck (T1) / evidence summary (T2); "
             "a positive mean_diff means P moved the process as intended.",
    )

    # ---- endpoint preservation ----
    # The official evaluate_simulation returned None here (SimulationRun construction
    # from our controllable loop needs work -> a disclosed measurement gap for the full
    # pilot). As a proxy we compare the MUTATION OUTCOME distribution: if A and N1
    # produce the same rate of completed mutations, the endpoint behaviour is preserved.
    ep = contrast(rows, "n_mutations", "A", "N1", "A-N1 mutation-count (endpoint proxy)")
    ep["note"] = ("official endpoint reward was None in this pilot; this is a mutation-count "
                  "proxy for endpoint preservation, not the official reward.")

    out = dict(
        scale="MINIMAL methodology-validation pilot (NOT an S2 decision)",
        n_blocks=len({r["block_id"] for r in rows}),
        primary={k: v for k, v in results},
        positive_control_gate=pos_gate,
        endpoint_preservation=ep,
        secondary=sec,
    )
    (OUTD / "pilot_analysis.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    # also a flat CSV of the headline contrasts
    with (OUTD / "headline_contrasts.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["contrast", "metric", "n_pairs", "mean_diff", "ci_low", "ci_high", "perm_p"])
        w.writeheader()
        for _, v in results:
            w.writerow({k: v[k] for k in w.fieldnames})
        for v in sec + [ep]:
            w.writerow({k: v[k] for k in w.fieldnames})

    print("\n=== PRIMARY (A - N1), preliminary ===")
    for k, v in results:
        print(f"  {k}: {v['contrast']}  mean_diff={v['mean_diff']}  95%CI[{v['ci_low']},{v['ci_high']}]  perm_p={v['perm_p']}  n={v['n_pairs']}")
    print(f"\n=== positive control (P should move process) ===")
    print(f"  T1 P-N1 tools = {pos_gate['T1_P_minus_N1_tools']}   T2 P-N1 evidence = {pos_gate['T2_P_minus_N1_evidence']}")
    print(f"\n=== endpoint preservation A-N1 reward = {ep['mean_diff']} (CI [{ep['ci_low']},{ep['ci_high']}]) ===")
    print(f"\nwrote {OUTD/'pilot_analysis.json'} and headline_contrasts.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
