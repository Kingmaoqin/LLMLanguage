#!/usr/bin/env python3
"""KEY: re-mine L1->L2 via JOINT / CONDITIONAL indicators (not just pooled correlation).
Builds oversight+autonomy+joint indicators per episode, then rates by condition and subgroup.
Outputs under 05_attack_chain/. Data: R9v2 (Qwen-72B, BFCL-deep)."""
import csv, os
from collections import defaultdict
from _common import OUT, load, ttype, mean, comp, succ, clar, first_write, tools

A="r9v2"; recs=[r for r in load(A) if not r.get("infra_failure")]
CONDS=["C0","C1","C2","C3","C4","C5"]
B05=f"{OUT}/05_attack_chain"

# --- per-task C1 baselines (for headroom terciles + early-write reference) ---
c1clar=defaultdict(list); c1fw=defaultdict(list)
for r in recs:
    if r["condition"]=="C1":
        if clar(r) is not None: c1clar[r["task_id"]].append(clar(r))
        if first_write(r) is not None: c1fw[r["task_id"]].append(first_write(r))
base_clar={t:mean(v) for t,v in c1clar.items() if v}
base_fw={t:mean(v) for t,v in c1fw.items() if v}
# headroom tercile by baseline clarification
rows=sorted(base_clar.items(),key=lambda x:x[1]); n=len(rows)
terc={t:("LOW" if i<n//3 else "HIGH" if i>=2*n//3 else "MID") for i,(t,_) in enumerate(rows)}

# --- per-episode joint indicators ---
def indicators(r):
    cl=clar(r); fw=first_write(r); t=r["task_id"]
    asked = None if cl is None else int(cl>0)
    zero  = None if cl is None else int(cl==0)
    wrote = int(fw is not None)                      # a state-changing write happened
    early = None
    if fw is not None and t in base_fw:
        early = int(fw < base_fw[t])                 # earlier than this task's neutral baseline
    s = succ(r)
    return dict(asked=asked, zero_clar=zero, wrote=wrote, early_write=early, success=s,
                zero_and_write=(None if zero is None else zero*wrote),
                zero_and_early=(None if (zero is None or early is None) else zero*early),
                zero_and_success=(None if (zero is None or s is None) else zero*s),
                zero_and_fail=(None if (zero is None or s is None) else zero*(1-s)))

# --- A. per-condition rates (pooled + by family) ---
def rate_table(subset=None, tag="ALL"):
    grp=defaultdict(lambda: defaultdict(list))
    for r in recs:
        if subset and not subset(r): continue
        ind=indicators(r); grp[r["condition"]]  # touch
        for k,v in ind.items(): grp[r["condition"]][k].append(v)
    out=[]
    for c in CONDS:
        g=grp.get(c)
        if not g: continue
        row=dict(subset=tag,condition=c,n=len(g["wrote"]))
        for k in ["zero_clar","asked","wrote","early_write","zero_and_write","zero_and_early","zero_and_success","success"]:
            row[k]=round(mean(g[k]),4)
        out.append(row)
    return out

os.makedirs(f"{B05}/joint_analysis",exist_ok=True)
allrows=[]
allrows+=rate_table(tag="ALL")
allrows+=rate_table(lambda r:r.get("family")=="compression", "compression(urgency)")
allrows+=rate_table(lambda r:r.get("family")=="inflation", "inflation(skepticism)")
allrows+=rate_table(lambda r:ttype(r["task_id"])=="miss_param", "miss_param")
allrows+=rate_table(lambda r:ttype(r["task_id"])=="base", "base")
for lvl in ["LOW","MID","HIGH"]:
    allrows+=rate_table(lambda r,l=lvl:terc.get(r["task_id"])==l, f"headroom_{lvl}")
with open(f"{B05}/joint_analysis/condition_rates.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(allrows[0].keys())); w.writeheader(); w.writerows(allrows)

# --- B. conditional: P(success | zero_clar) vs P(success | asked), by condition ---
condB=[]
for c in CONDS:
    zs=[]; az=[]
    for r in recs:
        if r["condition"]!=c: continue
        ind=indicators(r)
        if ind["success"] is None or ind["zero_clar"] is None: continue
        (zs if ind["zero_clar"]==1 else az).append(ind["success"])
    condB.append(dict(condition=c,n_zero=len(zs),P_success_given_zeroclar=round(mean(zs),4) if zs else "",
                      n_asked=len(az),P_success_given_asked=round(mean(az),4) if az else ""))
with open(f"{B05}/joint_analysis/success_conditional_on_clarification.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(condB[0].keys())); w.writeheader(); w.writerows(condB)

# --- C. attack effect on JOINT events: C4-C1 and C5-C1 for zero_clar / zero_and_early, by subgroup ---
def paired_rate(metric_key, treat, subset=None):
    tb=defaultdict(list); tt=defaultdict(list)
    for r in recs:
        if subset and not subset(r): continue
        v=indicators(r)[metric_key]
        if v is None: continue
        if r["condition"]==treat: tt[r["task_id"]].append(v)
        elif r["condition"]=="C1": tb[r["task_id"]].append(v)
    tasks=[t for t in tb if t in tt and tb[t] and tt[t]]
    if len(tasks)<5: return None
    diffs=[mean(tt[t])-mean(tb[t]) for t in tasks]
    return round(mean(diffs),4), len(tasks)
rowsC=[]
for key in ["zero_clar","zero_and_early","early_write"]:
    for sub_tag,sub in [("ALL",None),("miss_param",lambda r:ttype(r["task_id"])=="miss_param"),
                        ("headroom_HIGH",lambda r:terc.get(r["task_id"])=="HIGH"),
                        ("headroom_LOW",lambda r:terc.get(r["task_id"])=="LOW")]:
        for treat in ["C4","C5"]:
            res=paired_rate(key,treat,sub)
            if res: rowsC.append(dict(indicator=key,subset=sub_tag,contrast=f"{treat}-C1",delta=res[0],n_tasks=res[1]))
with open(f"{B05}/joint_analysis/attack_effect_on_joint_events.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rowsC[0].keys())); w.writeheader(); w.writerows(rowsC)

# --- print key numbers ---
print("=== zero-clarification rate by condition (compression) ===")
for row in allrows:
    if row["subset"]=="compression(urgency)": print(f"  {row['condition']}: zero_clar={row['zero_clar']}  early_write={row['early_write']}  zero&early={row['zero_and_early']}  success={row['success']}")
print("=== attack effect (C4-C1) on joint events, by subgroup ===")
for r in rowsC:
    if r["contrast"]=="C4-C1": print(f"  {r['indicator']:16s} {r['subset']:14s} Δ={r['delta']:+.4f} (n={r['n_tasks']})")
print("05 done ->",B05)
