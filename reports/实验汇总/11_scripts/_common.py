"""Shared loaders + stats for local evidence mining (实验汇总).
All paths are absolute so scripts run from anywhere. Never mutates source data.
"""
import json, os, statistics as st, random
from collections import defaultdict

REPO = "/home/xqin5/llmlanguage/ir_mstu_stage2"
OUT  = "/home/xqin5/llmlanguage/实验汇总"

# episode-level source files (raw, read-only)
BATCHES = {
    "r9v2":       f"{REPO}/results/r9v2/confirmatory/confirmatory_episodes.jsonl",       # Qwen2.5-72B, BFCL-deep, 1401
    "r9v1_clean": f"{REPO}/results/r9_attack/confirmatory/confirmatory_episodes.jsonl",  # gemma+mistral, BFCL+TS, 880
}

def load(batch):
    return [json.loads(l) for l in open(BATCHES[batch])]

def ttype(tid):
    return "miss_param" if "miss_param" in (tid or "") else ("base" if "multi_turn" in (tid or "") else "other")

def mean(x):
    x = [v for v in x if v is not None]
    return st.mean(x) if x else float("nan")

# ---- per-episode metric extractors (episode-level; SOURCE_LEVEL=EPISODE_LEVEL) ----
def comp(r):  return (r.get("process") or {}).get("compression") or {}
def infl(r):  return (r.get("process") or {}).get("inflation") or {}
def succ(r):  return (r.get("endpoint") or {}).get("success")

def clar(r):  return comp(r).get("clarification_turns")
def reads_bw(r): return comp(r).get("reads_before_first_mutation")
def first_write(r): return comp(r).get("first_state_changing_step")
def vd(r):
    c = comp(r)
    return None if c.get("no_state_change") else c.get("verification_depth")
def ve(r):    return infl(r).get("verification_effort")
def tools(r): return comp(r).get("total_tool_calls") or infl(r).get("total_tool_calls")

def sel_score(r):
    ivs = [iv.get("selector_score") for iv in (r.get("interventions") or [])
           if iv.get("non_neutral") and iv.get("selector_score") is not None]
    return mean(ivs) if ivs else None
def sel_tokens(r):
    tk = [iv.get("token_count") for iv in (r.get("interventions") or [])
          if iv.get("non_neutral") and iv.get("token_count") is not None]
    return mean(tk) if tk else None

# ---- paired task-level stats with bootstrap CI + sign-flip permutation ----
def paired_task(recs, family, metric, treat, base="C1", subset=None, seed=7, B=3000):
    rnd = random.Random(seed)
    tb, tt = defaultdict(list), defaultdict(list)
    for r in recs:
        if r.get("infra_failure") or r.get("family") != family: continue
        if subset and not subset(r): continue
        v = metric(r)
        if v is None: continue
        if r["condition"] == treat: tt[r["task_id"]].append(v)
        elif r["condition"] == base: tb[r["task_id"]].append(v)
    tasks = [t for t in tb if t in tt and tb[t] and tt[t]]
    if len(tasks) < 5: return None
    diffs = [mean(tt[t]) - mean(tb[t]) for t in tasks]
    est = mean(diffs)
    boots = sorted(mean([rnd.choice(diffs) for _ in diffs]) for _ in range(B))
    lo, hi = boots[int(.025*B)], boots[int(.975*B)]
    obs = abs(est); cnt = 0
    for _ in range(B):
        s = [d*(1 if rnd.random() < .5 else -1) for d in diffs]
        if abs(mean(s)) >= obs: cnt += 1
    p = (cnt+1)/(B+1)
    pos = sum(1 for d in diffs if d > 0); neg = sum(1 for d in diffs if d < 0)
    same = max(pos, neg)/len(diffs) if diffs else 0
    return dict(est=round(est,4), ci_low=round(lo,4), ci_high=round(hi,4), p=round(p,4),
                n_tasks=len(tasks), same_dir=round(same,3),
                n_ep_treat=sum(len(tt[t]) for t in tasks), n_ep_base=sum(len(tb[t]) for t in tasks))

def pearson(xy):
    xy = [(a,b) for a,b in xy if a is not None and b is not None]
    if len(xy) < 8: return None, len(xy)
    xs=[a for a,_ in xy]; ys=[b for _,b in xy]; mx=mean(xs); my=mean(ys)
    num=sum((a-mx)*(b-my) for a,b in xy); dx=sum((a-mx)**2 for a in xs)**.5; dy=sum((b-my)**2 for b in ys)**.5
    return (round(num/(dx*dy),4) if dx*dy else None), len(xy)
