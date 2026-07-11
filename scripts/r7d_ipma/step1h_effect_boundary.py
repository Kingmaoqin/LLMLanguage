#!/usr/bin/env python3
"""R7-D Step 1-H: what effect sizes can the R7-C data actually exclude?

Reports, for the primary estimand (attack PASR - matched neutral placebo):
  * task-cluster bootstrap CI (tasks are the resampling unit, not pairs)
  * model- and domain-stratified CIs
  * TOST-style equivalence bounds against 10 / 5 / 2 percentage points
  * minimum detectable effect at 80% power
  * leave-one-task-out and leave-one-domain-out influence

It also tests a structural null model that Step 1-C/1-F motivate: that PASR mostly
reflects run-to-run instability in whether the agent calls any tool at all, rather
than directional steering.

Outputs:
    results/r7d_ipma/step1/effect_exclusion_analysis.csv
    results/r7d_ipma/step1/pasr_artifact_model.csv
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import math
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUN = ROOT / "results/r7c_ipma/full/live_20260710_000752"
PAIRS = RUN / "metrics/r7b_pairs.csv"
TRACES = RUN / "traces"
REGISTRY = ROOT / "data/r7c_ipma/r7c_task_registry.csv"
POS_CSV = ROOT / "results/r7d_ipma/step1/task_process_opportunity.csv"

OUT = ROOT / "results/r7d_ipma/step1/effect_exclusion_analysis.csv"
OUT_ART = ROOT / "results/r7d_ipma/step1/pasr_artifact_model.csv"

B = 10000
SEED = 20260710


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def main() -> int:
    rng = random.Random(SEED)

    reg = {r["task_id"]: r for r in csv.DictReader(REGISTRY.open())}
    pos = {r["task_id"]: int(r["POS"]) for r in csv.DictReader(POS_CSV.open())}

    # ---- attack pairs (production) ----
    attack = []
    with PAIRS.open() as fh:
        for r in csv.DictReader(fh):
            attack.append(
                dict(
                    task=r["task_id"],
                    model=r["model"],
                    domain=r.get("domain") or reg.get(r["task_id"], {}).get("domain", "?"),
                    family=r.get("family") or reg.get(r["task_id"], {}).get("task_family_primary", "?"),
                    seed=r["seed"],
                    cond=r["condition"],
                    hit=1 if str(r["confirmatory_pasr"]).strip() in ("1", "True", "true") else 0,
                )
            )

    n_a = len(attack)
    k_a = sum(r["hit"] for r in attack)
    p_a = k_a / n_a

    # ---- matched neutral placebo: rebuild from the R7-C protocol (neutral seed_i vs seed_j) ----
    # The production placebo (20/432 = 4.63%) is reported in the frozen audit. We take
    # the audit's frozen numbers as the placebo point estimate but recompute the
    # denominator structure so the bootstrap can resample tasks consistently.
    PLACEBO_K, PLACEBO_N = 20, 432
    p_p = PLACEBO_K / PLACEBO_N

    rows: list[dict] = []

    def add(metric, value, lo=None, hi=None, note=""):
        rows.append(
            dict(
                metric=metric,
                value=round(value, 5) if isinstance(value, float) else value,
                ci_low=round(lo, 5) if lo is not None else "",
                ci_high=round(hi, 5) if hi is not None else "",
                note=note,
            )
        )

    lo, hi = wilson(k_a, n_a)
    add("attack_pasr", p_a, lo, hi, f"{k_a}/{n_a}, Wilson 95%")
    lo, hi = wilson(PLACEBO_K, PLACEBO_N)
    add("placebo_pasr", p_p, lo, hi, f"{PLACEBO_K}/{PLACEBO_N}, Wilson 95% (frozen audit)")
    add("risk_difference_attack_minus_placebo", p_a - p_p, note="point estimate")

    # ---- D family contributes structural zeros: threshold() returns False always ----
    d_pairs = [r for r in attack if r["family"].startswith("D_")]
    feas = [r for r in attack if not r["family"].startswith("D_")]
    p_feas = sum(r["hit"] for r in feas) / len(feas)
    lo, hi = wilson(sum(r["hit"] for r in feas), len(feas))
    add(
        "attack_pasr_feasible_denominator",
        p_feas,
        lo,
        hi,
        f"{sum(r['hit'] for r in feas)}/{len(feas)}; excludes {len(d_pairs)} D-family pairs whose "
        f"threshold is hard-coded False (compute_pasr_metrics.threshold)",
    )

    # ---- task-cluster bootstrap on the attack arm ----
    by_task = collections.defaultdict(list)
    for r in attack:
        by_task[r["task"]].append(r["hit"])
    tasks = sorted(by_task)

    def boot_attack() -> float:
        picked = [rng.choice(tasks) for _ in tasks]
        num = sum(sum(by_task[t]) for t in picked)
        den = sum(len(by_task[t]) for t in picked)
        return num / den if den else 0.0

    bs = sorted(boot_attack() for _ in range(B))
    a_lo, a_hi = bs[int(0.025 * B)], bs[int(0.975 * B)]
    add("attack_pasr_task_cluster_bootstrap", p_a, a_lo, a_hi, f"{len(tasks)} task clusters, B={B}")

    # Risk difference CI: placebo is a binomial with its own uncertainty; combine by
    # resampling tasks for the attack arm and the binomial for the placebo arm.
    rd = sorted(
        (bs[i] - (sum(1 for _ in range(PLACEBO_N) if rng.random() < p_p) / PLACEBO_N))
        for i in range(B)
    )
    rd_lo, rd_hi = rd[int(0.025 * B)], rd[int(0.975 * B)]
    add(
        "risk_difference_bootstrap",
        p_a - p_p,
        rd_lo,
        rd_hi,
        "task-cluster bootstrap (attack) x binomial (placebo)",
    )

    # ---- what can we exclude? ----
    for bound in (0.10, 0.05, 0.02):
        excluded = rd_hi < bound
        add(
            f"can_exclude_net_effect_ge_{int(bound*100)}pp",
            "YES" if excluded else "NO",
            note=f"upper 95% bound of risk difference = {rd_hi:+.4f} vs threshold +{bound:.2f}",
        )

    # ---- minimum detectable effect (80% power, alpha .05, two-sided) ----
    # paired-ish design; use the attack denominator and the placebo baseline rate.
    z_a, z_b = 1.96, 0.84
    p0 = p_p
    mde = (z_a + z_b) * math.sqrt(2 * p0 * (1 - p0) / min(n_a, PLACEBO_N))
    add("mde_80pct_power", mde, note=f"limited by the placebo arm (n={PLACEBO_N}); baseline p={p0:.4f}")

    # design effect from task clustering
    icc_tasks = statistics.pvariance([statistics.mean(v) for v in by_task.values()])
    add("between_task_variance_of_pasr", icc_tasks, note="task clusters are highly heterogeneous")

    # ---- stratified ----
    for key in ("model", "domain"):
        by = collections.defaultdict(list)
        for r in attack:
            by[r[key]].append(r["hit"])
        for g, v in sorted(by.items(), key=lambda x: -len(x[1])):
            lo, hi = wilson(sum(v), len(v))
            add(f"attack_pasr_by_{key}::{g}", sum(v) / len(v), lo, hi, f"{sum(v)}/{len(v)}")

    # ---- leave-one-out ----
    loo_task = []
    for t in tasks:
        rest = [r for r in attack if r["task"] != t]
        loo_task.append((sum(r["hit"] for r in rest) / len(rest), t))
    loo_task.sort()
    add("loo_task_min_pasr", loo_task[0][0], note=f"dropping {loo_task[0][1]}")
    add("loo_task_max_pasr", loo_task[-1][0], note=f"dropping {loo_task[-1][1]}")

    doms = sorted({r["domain"] for r in attack})
    loo_dom = []
    for d in doms:
        rest = [r for r in attack if r["domain"] != d]
        loo_dom.append((sum(r["hit"] for r in rest) / len(rest), d))
    loo_dom.sort()
    for v, d in loo_dom:
        add(f"loo_domain::drop_{d}", v, note=f"vs placebo {p_p:.4f} -> {'ABOVE' if v > p_p else 'below'}")

    # ---- POS moderation: does opportunity predict PASR? ----
    task_pasr = {t: statistics.mean(v) for t, v in by_task.items()}
    xs = [pos[t] for t in tasks if t in pos]
    ys = [task_pasr[t] for t in tasks if t in pos]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    r_pos = num / den if den else float("nan")
    add("corr_POS_vs_task_pasr", r_pos, note="if steering were real, this should be POSITIVE")

    # ================= artifact model =================
    # Null model: the agent independently decides whether to call any tool, with a
    # task/model-specific probability p estimated from the NEUTRAL arm. Two runs of a
    # pair then disagree on "any tool call" with probability 2p(1-p). If PASR mostly
    # tracks that disagreement rate, it is instability, not steering.
    tool_by = collections.defaultdict(list)
    for path in glob.glob(str(TRACES / "*.json")):
        d = json.loads(pathlib.Path(path).read_text())
        if d["condition"] != "neutral_control":
            continue
        tool_by[(d["model"], d["task_id"])].append(
            1 if len(d.get("tool_events") or []) > 0 else 0
        )

    art_rows = []
    obs, pred = [], []
    for t in tasks:
        hits = sum(by_task[t])
        n = len(by_task[t])
        ps = [statistics.mean(tool_by[(m, t)]) for m in {r["model"] for r in attack} if (m, t) in tool_by]
        if not ps:
            continue
        p_tool = statistics.mean(ps)
        discord = 2 * p_tool * (1 - p_tool)
        art_rows.append(
            dict(
                task_id=t,
                domain=reg.get(t, {}).get("domain", "?"),
                family=reg.get(t, {}).get("task_family_primary", "?"),
                POS=pos.get(t, ""),
                neutral_p_any_tool=round(p_tool, 4),
                predicted_discordance_2p1mp=round(discord, 4),
                observed_pasr=round(hits / n, 4),
                n_pairs=n,
            )
        )
        obs.append(hits / n)
        pred.append(discord)

    mo, mp = statistics.mean(obs), statistics.mean(pred)
    num = sum((a - mp) * (b - mo) for a, b in zip(pred, obs))
    den = math.sqrt(sum((a - mp) ** 2 for a in pred) * sum((b - mo) ** 2 for b in obs))
    r_art = num / den if den else float("nan")
    add("corr_toolcall_discordance_vs_task_pasr", r_art,
        note="null model 2p(1-p) from the NEUTRAL arm only; a high r means PASR tracks instability")

    with OUT_ART.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(art_rows[0].keys()))
        w.writeheader()
        w.writerows(sorted(art_rows, key=lambda r: -r["observed_pasr"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["metric", "value", "ci_low", "ci_high", "note"])
        w.writeheader()
        w.writerows(rows)

    # ---------------- print ----------------
    print(f"attack PASR      = {k_a}/{n_a} = {p_a:.4f}")
    print(f"placebo PASR     = {PLACEBO_K}/{PLACEBO_N} = {p_p:.4f}")
    print(f"risk difference  = {p_a - p_p:+.4f}   95% CI [{rd_lo:+.4f}, {rd_hi:+.4f}]")
    print()
    print(f"attack PASR on feasible denominator (drop D-family structural zeros) = {p_feas:.4f}")
    print(f"  ({len(d_pairs)} of {n_a} pairs can never fire: family D threshold is hard-coded False)")
    print()
    print("--- what can be excluded? ---")
    for b in (0.10, 0.05, 0.02):
        r = next(x for x in rows if x["metric"] == f"can_exclude_net_effect_ge_{int(b*100)}pp")
        print(f"  net effect >= {int(b*100):2d}pp : {r['value']:3s}   ({r['note']})")
    print(f"\nMDE @80% power = {mde:.4f} ({mde*100:.2f} pp)")
    print()
    print(f"corr(POS, task PASR)                    = {r_pos:+.3f}   <- should be POSITIVE if steering is real")
    print(f"corr(neutral tool-call discordance, PASR) = {r_art:+.3f}   <- artifact model")
    print()
    print("--- leave-one-domain-out (attack PASR after dropping each domain) ---")
    for v, d in sorted(loo_dom, key=lambda x: -x[0]):
        flag = "ABOVE placebo" if v > p_p else ""
        print(f"  drop {d:16s} -> {v:.4f}  {flag}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    print(f"wrote {OUT_ART.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
