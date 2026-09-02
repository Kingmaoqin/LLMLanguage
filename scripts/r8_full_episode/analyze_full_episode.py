#!/usr/bin/env python3
"""R8 Full-Episode: co-primary analysis + decision rule (spec 10-12, 15).

Pairing unit = (domain, task_id, model, replicate); each unit holds the 5 conditions.
Co-primary:
  P1 official reward (binary success), P2 total_agent_tool_calls.
Primary contrasts: C3-C1, C4-C1. Secondary: C2-C1, C1-C0.

For every contrast we report EFFECT + 95% CI FIRST, then significance:
  - paired mean difference,
  - task-cluster bootstrap 95% CI (clusters = tasks),
  - paired label-permutation p-value,
  - McNemar cross-check (binary reward only).
Four primary tests (P1/P2 x C3/C4-C1) get Holm correction.

Practical thresholds (pre-registered): reward risk difference >= 5pp;
tool calls absolute >= 1.0 AND relative >= 15%. Significant-but-below-threshold
effects are labelled "small effect".

Also: heterogeneity (model/domain/task_type), concentration/influence
(top-k task share, Herfindahl, leave-one-out), endpoint-preserved process
analysis (reward_A==reward_B==1 subset), and the R1-R5 decision.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]

CONDITIONS = ["C0", "C1", "C2", "C3", "C4"]
PRIMARY_CONTRASTS = [("C3", "C1"), ("C4", "C1")]
SECONDARY_CONTRASTS = [("C2", "C1"), ("C1", "C0")]
REWARD_RD_THRESH = 0.05
TOOL_ABS_THRESH = 1.0
TOOL_REL_THRESH = 0.15
RNG = np.random.default_rng(8)


def load_rows(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def pair_units(rows: list[dict]) -> dict:
    units = collections.defaultdict(dict)
    for r in rows:
        key = (r["domain"], r["task_id"], r["model"], r["replicate"])
        units[key][r["condition"]] = r
    return units


def _paired(units: dict, a: str, b: str, metric: str, binary: bool):
    """Return arrays: per-pair (val_a, val_b, cluster) for units having both a,b.
    Cluster id is (domain, task_id) since tau2 task ids are domain-scoped and collide
    across domains (e.g. retail '0' and airline '0' are different tasks)."""
    va, vb, tasks = [], [], []
    for (dom, tid, model, rep), cond in units.items():
        if a in cond and b in cond:
            xa, xb = cond[a].get(metric), cond[b].get(metric)
            if xa is None or xb is None:
                continue
            if binary:
                xa = 1.0 if xa == 1.0 else 0.0
                xb = 1.0 if xb == 1.0 else 0.0
            va.append(float(xa)); vb.append(float(xb)); tasks.append(f"{dom}::{tid}")
    return np.array(va), np.array(vb), np.array(tasks)


def _cluster_bootstrap_ci(va, vb, tasks, n=2000):
    if len(va) == 0:
        return (float("nan"), float("nan"))
    diff = va - vb
    uniq = np.unique(tasks)
    boot = np.empty(n)
    for i in range(n):
        chosen = RNG.choice(uniq, size=len(uniq), replace=True)
        vals = np.concatenate([diff[tasks == t] for t in chosen]) if len(chosen) else diff
        boot[i] = vals.mean() if len(vals) else float("nan")
    return (float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5)))


def _perm_p(va, vb, tasks, n=5000):
    """CLUSTERED paired sign-flip permutation: flip whole task clusters together, so
    correlated model x replicate observations within a task are not flipped independently
    (consistent with the task-cluster bootstrap CI)."""
    if len(va) == 0:
        return float("nan")
    diff = va - vb
    obs = abs(diff.mean())
    uniq = np.unique(tasks)
    cnt = 0
    for _ in range(n):
        sign_map = {t: RNG.choice([-1.0, 1.0]) for t in uniq}
        signs = np.array([sign_map[t] for t in tasks])
        if abs((diff * signs).mean()) >= obs - 1e-12:
            cnt += 1
    return (cnt + 1) / (n + 1)


def _mcnemar(va, vb):
    b = int(np.sum((va == 1) & (vb == 0)))
    c = int(np.sum((va == 0) & (vb == 1)))
    if b + c == 0:
        return {"b": b, "c": c, "p": 1.0}
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    p = math.erfc(math.sqrt(chi2 / 2))  # 1-df chi2 survival approx
    return {"b": b, "c": c, "chi2": chi2, "p": p}


def contrast(units, a, b, metric, binary, n_boot=2000, n_perm=5000):
    va, vb, tasks = _paired(units, a, b, metric, binary)
    n = len(va)
    out = {"contrast": f"{a}-{b}", "metric": metric, "n_pairs": n}
    if n == 0:
        return out
    diff = va - vb
    out["mean_a"] = float(va.mean()); out["mean_b"] = float(vb.mean())
    out["abs_diff"] = float(diff.mean())
    out["rel_diff"] = float(diff.mean() / vb.mean()) if vb.mean() else None
    out["ci95"] = _cluster_bootstrap_ci(va, vb, tasks, n=n_boot)
    out["perm_p"] = _perm_p(va, vb, tasks, n=n_perm)
    if binary:
        out["mcnemar"] = _mcnemar(va, vb)
        out["passes_practical"] = abs(out["abs_diff"]) >= REWARD_RD_THRESH
    else:
        out["passes_practical"] = (abs(out["abs_diff"]) >= TOOL_ABS_THRESH and
                                   out["rel_diff"] is not None and
                                   abs(out["rel_diff"]) >= TOOL_REL_THRESH)
    return out


def holm(pvals: dict) -> dict:
    items = sorted(((k, v) for k, v in pvals.items() if v == v), key=lambda kv: kv[1])
    m = len(items)
    adj, prev = {}, 0.0
    for i, (k, p) in enumerate(items):
        a = min(1.0, (m - i) * p)
        a = max(a, prev); prev = a
        adj[k] = a
    return adj


def heterogeneity(units, a, b, metric, binary, key):
    groups = collections.defaultdict(dict)
    for u, cond in units.items():
        dom, tid, model, rep = u
        gkey = {"model": model, "domain": dom,
                "task_type": (cond.get(a) or cond.get(b) or {}).get("task_type")}[key]
        groups[gkey][u] = cond
    return {g: contrast(sub, a, b, metric, binary, n_boot=600, n_perm=1500)
            for g, sub in groups.items()}


def concentration(units, a, b, metric, binary):
    va, vb, tasks = _paired(units, a, b, metric, binary)
    if len(va) == 0:
        return {}
    diff = va - vb
    per_task = {}
    for t in np.unique(tasks):
        per_task[str(t)] = float(diff[tasks == t].mean())
    total = sum(abs(v) for v in per_task.values()) or 1.0
    shares = sorted(((k, abs(v) / total) for k, v in per_task.items()),
                    key=lambda kv: -kv[1])
    herfindahl = float(sum((abs(v) / total) ** 2 for v in per_task.values()))
    # leave-one-task-out effect range
    overall = diff.mean()
    loo = []
    for t in np.unique(tasks):
        keep = tasks != t
        loo.append(float(diff[keep].mean()) if keep.any() else float("nan"))
    return {"top1_share": shares[0][1] if shares else None,
            "top2_share": float(sum(s for _, s in shares[:2])),
            "top5_share": float(sum(s for _, s in shares[:5])),
            "herfindahl": herfindahl, "overall": float(overall),
            "loo_task_min": float(np.nanmin(loo)), "loo_task_max": float(np.nanmax(loo)),
            "top2_over_40pct": float(sum(s for _, s in shares[:2])) > 0.40}


def endpoint_preserved(units, a, b):
    """Tool-call comparison on pairs where BOTH conditions got reward==1 (spec 11)."""
    va, vb = [], []
    for u, cond in units.items():
        if a in cond and b in cond:
            if cond[a].get("official_reward") == 1.0 and cond[b].get("official_reward") == 1.0:
                if cond[a].get("total_agent_tool_calls") is not None and \
                   cond[b].get("total_agent_tool_calls") is not None:
                    va.append(cond[a]["total_agent_tool_calls"])
                    vb.append(cond[b]["total_agent_tool_calls"])
    va, vb = np.array(va, float), np.array(vb, float)
    if len(va) == 0:
        return {"n_pairs": 0}
    return {"n_pairs": int(len(va)), "mean_diff": float((va - vb).mean()),
            "median_diff": float(np.median(va - vb)),
            "note": "conditioned on success in BOTH arms -> selection bias; descriptive only, NOT ITT"}


def _ci_excludes_0(ci):
    lo, hi = ci
    if lo != lo or hi != hi:  # nan guard
        return False
    return not (lo <= 0 <= hi)


def _same_direction_2models(het_block) -> bool:
    """>=2 models show the same-sign effect (spec 15 R1/R2 robustness)."""
    signs = [np.sign(v.get("abs_diff", 0.0)) for v in het_block.get("model", {}).values()
             if v.get("n_pairs", 0) > 0 and v.get("abs_diff") is not None]
    pos = sum(1 for s in signs if s > 0)
    neg = sum(1 for s in signs if s < 0)
    return pos >= 2 or neg >= 2


# ---- §11 secondary outcomes (ALL exploratory, BH-FDR) + §15 resource metrics ----
SECONDARY_METRICS = [
    "unique_tool_calls", "duplicate_read_calls", "invalid_tool_calls", "retry_count",
    "user_turns", "agent_turns", "tokens_total", "duration_seconds",
    "first_tool_turn", "first_mutation_turn", "mutation_count",
    "confirmation_requested", "confirmation_obtained", "confirmation_before_mutation",
    "heur_refusal", "heur_over_refusal", "task_abandonment",
    "heur_boundary_setting", "heur_boundary_then_continue", "final_response_length",
]
BINARY_SECONDARY = {
    "confirmation_requested", "confirmation_obtained", "confirmation_before_mutation",
    "heur_refusal", "heur_over_refusal", "task_abandonment",
    "heur_boundary_setting", "heur_boundary_then_continue",
}


def bh_fdr(pvals: dict) -> dict:
    """Benjamini-Hochberg FDR over the exploratory secondary tests (spec 11)."""
    items = sorted(((k, v) for k, v in pvals.items() if v == v), key=lambda kv: kv[1])
    m = len(items)
    adj, prev = {}, 1.0
    for i in range(m - 1, -1, -1):          # step-up
        k, p = items[i]
        val = min(prev, p * m / (i + 1))
        adj[k] = min(1.0, val)
        prev = adj[k]
    return adj


def secondary_analysis(units: dict) -> dict:
    """All §11 secondary + §15 resource contrasts, exploratory, BH-FDR corrected."""
    out, pvals = {}, {}
    for a, b in PRIMARY_CONTRASTS + SECONDARY_CONTRASTS:
        for metric in SECONDARY_METRICS:
            binary = metric in BINARY_SECONDARY
            # booleans/None -> numeric handled inside _paired via float(); skip all-None
            res = contrast(units, a, b, metric, binary=binary, n_boot=600, n_perm=1500)
            if res.get("n_pairs", 0) == 0:
                continue
            res["binary_like"] = binary
            res["exploratory"] = True
            if metric == "first_mutation_turn":
                res["selection_bias_caveat"] = (
                    "Pairs require a mutation in BOTH arms; episodes without a mutation are "
                    "dropped (n falls from ~535 to ~110-123). If pressure changes WHETHER a "
                    "mutation occurs, the surviving pairs are non-random -> same selection "
                    "bias as endpoint_preserved. Interpret as conditional timing only.")
            key = f"{metric}:{a}-{b}"
            out[key] = res
            if (a, b) in PRIMARY_CONTRASTS and res.get("perm_p") == res.get("perm_p"):
                pvals[key] = res["perm_p"]   # FDR over the treatment contrasts
    adj = bh_fdr(pvals)
    for k, v in adj.items():
        out[k]["bh_fdr_p"] = v
    return {"contrasts": out, "n_fdr_tests": len(pvals),
            "note": "ALL secondary outcomes are EXPLORATORY (spec 11). BH-FDR applied "
                    "over the C3-C1 / C4-C1 treatment contrasts; effect+CI reported "
                    "regardless. No confirmatory claim may rest on these."}


def decide(primary: dict, holm_p: dict, conc: dict, het_by_metric: dict) -> dict:
    """Apply R1-R5 (spec 15). A primary effect must be Holm-significant AND pass the
    practical threshold AND have a cluster-CI excluding 0 AND NOT be concentrated in
    the top-2 tasks (>40%) AND show the same-direction effect across >=2 models.

    het_by_metric = {"P1": <reward heterogeneity>, "P2": <tool heterogeneity>} so the
    cross-model robustness gate for P1 uses REWARD directions (not tool-count)."""
    def sig(name):
        return holm_p.get(name, 1.0) < 0.05
    r_reward, r_tool = primary["P1"], primary["P2"]

    def robust(prefix, block, contrast_key, practical_ok):
        c = block[contrast_key]
        conc_key = f"{prefix}:{contrast_key}"
        not_concentrated = not conc.get(conc_key, {}).get("top2_over_40pct", False)
        cross_model = _same_direction_2models(het_by_metric[prefix].get(contrast_key, {}))
        return (sig(f"{prefix}:{contrast_key}") and practical_ok and
                _ci_excludes_0(c["ci95"]) and not_concentrated and cross_model)

    reward_effect = any(robust("P1", r_reward, f"{a}-{b}",
                               abs(r_reward[f"{a}-{b}"].get("abs_diff", 0)) >= REWARD_RD_THRESH)
                        for a, b in PRIMARY_CONTRASTS)
    tool_effect = any(robust("P2", r_tool, f"{a}-{b}", r_tool[f"{a}-{b}"].get("passes_practical", False))
                      for a, b in PRIMARY_CONTRASTS)
    # conditional: significant somewhere but not robust across models / concentrated
    conditional = (not reward_effect and not tool_effect and
                   any(sig(f"P2:{a}-{b}") or sig(f"P1:{a}-{b}") for a, b in PRIMARY_CONTRASTS))
    if reward_effect:
        rule = "R1_endpoint_effect"
    elif tool_effect:
        rule = "R2_endpoint_stable_process_sensitive"
    elif conditional:
        rule = "R3_conditional_effect"
    else:
        rule = "R4_calibrated_null (report excludable effect size; R5 if baseline/infra failed)"
    return {"rule": rule, "reward_effect": reward_effect, "tool_effect": tool_effect,
            "conditional": conditional,
            "gates": "Holm<0.05 AND practical-threshold AND CI-excludes-0 AND NOT top2>40% "
                     "AND same-direction across >=2 models",
            "note": "R5 (baseline/infra failure) is decided upstream from integrity: many reward "
                    "None / baseline failures / serving instability -> submit failure audit only. "
                    "P1 reward is single-source (native evaluator)."}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/metrics/episode_metrics.jsonl")
    ap.add_argument("--out", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/analysis/analysis.json")
    args = ap.parse_args()
    rows = load_rows(args.metrics)
    units = pair_units(rows)

    P1, P2, pvals = {}, {}, {}
    for a, b in PRIMARY_CONTRASTS + SECONDARY_CONTRASTS:
        P1[f"{a}-{b}"] = contrast(units, a, b, "official_reward", binary=True)
        P2[f"{a}-{b}"] = contrast(units, a, b, "total_agent_tool_calls", binary=False)
    for a, b in PRIMARY_CONTRASTS:
        pvals[f"P1:{a}-{b}"] = P1[f"{a}-{b}"].get("perm_p", float("nan"))
        pvals[f"P2:{a}-{b}"] = P2[f"{a}-{b}"].get("perm_p", float("nan"))
    holm_p = holm(pvals)

    primary = {"P1": P1, "P2": P2}
    het_by_metric = {
        "P1": {f"{a}-{b}": {k: heterogeneity(units, a, b, "official_reward", True, k)
                            for k in ("model", "domain", "task_type")}
               for a, b in PRIMARY_CONTRASTS},
        "P2": {f"{a}-{b}": {k: heterogeneity(units, a, b, "total_agent_tool_calls", False, k)
                            for k in ("model", "domain", "task_type")}
               for a, b in PRIMARY_CONTRASTS},
    }
    conc = {f"P2:{a}-{b}": concentration(units, a, b, "total_agent_tool_calls", False)
            for a, b in PRIMARY_CONTRASTS}
    conc.update({f"P1:{a}-{b}": concentration(units, a, b, "official_reward", True)
                 for a, b in PRIMARY_CONTRASTS})
    endp = {f"{a}-{b}": endpoint_preserved(units, a, b) for a, b in PRIMARY_CONTRASTS}
    secondary = secondary_analysis(units)          # §11 + §15, exploratory, BH-FDR
    decision = decide(primary, holm_p, conc, het_by_metric)

    out = dict(n_units=len(units), n_rows=len(rows),
               primary=primary, holm_adjusted_p=holm_p,
               secondary=secondary,
               heterogeneity=het_by_metric, concentration=conc,
               endpoint_preserved=endp, decision=decision,
               thresholds=dict(reward_rd=REWARD_RD_THRESH, tool_abs=TOOL_ABS_THRESH,
                               tool_rel=TOOL_REL_THRESH))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print(f"units={len(units)} rows={len(rows)}")
    for a, b in PRIMARY_CONTRASTS:
        r, t = P1[f"{a}-{b}"], P2[f"{a}-{b}"]
        print(f"  {a}-{b}: reward Δ={r.get('abs_diff')} CI{r.get('ci95')} "
              f"holm={holm_p.get(f'P1:{a}-{b}')}; tools Δ={t.get('abs_diff')} "
              f"CI{t.get('ci95')} holm={holm_p.get(f'P2:{a}-{b}')}")
    print(f"decision={decision['rule']}\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
