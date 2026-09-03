#!/usr/bin/env python3
"""Headroom gradient: clarification suppression & verification control vs behavioral headroom.
Outputs task-level + summary CSVs under 04_strong_trends/ and 06_process_control/headroom/."""
import csv, os
from collections import defaultdict
from _common import OUT, load, mean, comp, clar, vd, ve, paired_task

recs=[r for r in load("r9v2") if not r.get("infra_failure")]
CONDS=["C0","C1","C2","C3","C4","C5"]

# ---- baseline-clarification tercile (compression family) ----
c1=defaultdict(list)
for r in recs:
    if r.get("family")=="compression" and r["condition"]=="C1" and clar(r) is not None:
        c1[r["task_id"]].append(clar(r))
base={t:mean(v) for t,v in c1.items() if v}
rows=sorted(base.items(),key=lambda x:x[1]); n=len(rows)
terc={t:("LOW" if i<n//3 else "HIGH" if i>=2*n//3 else "MID") for i,(t,_) in enumerate(rows)}

# task-level table
os.makedirs(f"{OUT}/04_strong_trends/data",exist_ok=True)
cd=defaultdict(lambda: defaultdict(list))
for r in recs:
    if r.get("family")!="compression": continue
    if clar(r) is not None: cd[r["task_id"]][r["condition"]].append(clar(r))
with open(f"{OUT}/04_strong_trends/data/headroom_clarification_task_level.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["task_id","model","baseline_clarification","headroom_group",
        "clarification_C1","clarification_C3","clarification_C4","clarification_C5","delta_C4_C1","delta_C5_C1","N_repeats"])
    w.writeheader()
    for t in base:
        c1v=mean(cd[t].get("C1",[])); c4v=mean(cd[t].get("C4",[])); c5v=mean(cd[t].get("C5",[])); c3v=mean(cd[t].get("C3",[]))
        w.writerow(dict(task_id=t,model="qwen25_72b",baseline_clarification=round(base[t],3),headroom_group=terc[t],
            clarification_C1=round(c1v,3),clarification_C3=round(c3v,3) if c3v==c3v else "",
            clarification_C4=round(c4v,3) if c4v==c4v else "",clarification_C5=round(c5v,3) if c5v==c5v else "",
            delta_C4_C1=round(c4v-c1v,3) if c4v==c4v else "",delta_C5_C1=round(c5v-c1v,3) if c5v==c5v else "",
            N_repeats=len(cd[t].get("C1",[]))))

# summary by headroom group (paired bootstrap)
os.makedirs(f"{OUT}/04_strong_trends/tables",exist_ok=True)
summ=[]
for lvl in ["LOW","MID","HIGH"]:
    for treat in ["C3","C4","C5"]:
        s=paired_task(recs,"compression",clar,treat,subset=lambda r,l=lvl:terc.get(r["task_id"])==l)
        if s: summ.append(dict(headroom_group=lvl,contrast=f"{treat}-C1",metric="clarification",**s))
# also VD headroom (baseline-VD tercile) for verification asymmetry
c1vd=defaultdict(list)
for r in recs:
    if r.get("family")=="compression" and r["condition"]=="C1" and vd(r) is not None:
        c1vd[r["task_id"]].append(vd(r))
bvd={t:mean(v) for t,v in c1vd.items() if v}
rv=sorted(bvd.items(),key=lambda x:x[1]); nv=len(rv)
tvd={t:("LOW" if i<nv//3 else "HIGH" if i>=2*nv//3 else "MID") for i,(t,_) in enumerate(rv)}
for lvl in ["LOW","MID","HIGH"]:
    for treat in ["C4","C5"]:
        s=paired_task(recs,"compression",vd,treat,subset=lambda r,l=lvl:tvd.get(r["task_id"])==l)
        if s: summ.append(dict(headroom_group=lvl,contrast=f"{treat}-C1",metric="verification_depth",**s))
# inflation VE headroom
c1ve=defaultdict(list)
for r in recs:
    if r.get("family")=="inflation" and r["condition"]=="C1" and ve(r) is not None:
        c1ve[r["task_id"]].append(ve(r))
bve={t:mean(v) for t,v in c1ve.items() if v}
re_=sorted(bve.items(),key=lambda x:x[1]); ne=len(re_)
tve={t:("LOW" if i<ne//3 else "HIGH" if i>=2*ne//3 else "MID") for i,(t,_) in enumerate(re_)}
for lvl in ["LOW","MID","HIGH"]:
    for treat in ["C4","C5"]:
        s=paired_task(recs,"inflation",ve,treat,subset=lambda r,l=lvl:tve.get(r["task_id"])==l)
        if s: summ.append(dict(headroom_group=lvl,contrast=f"{treat}-C1",metric="verification_effort",**s))
with open(f"{OUT}/04_strong_trends/tables/headroom_summary.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ)
# copy to process_control/headroom
import shutil
os.makedirs(f"{OUT}/06_process_control/headroom",exist_ok=True)
shutil.copy(f"{OUT}/04_strong_trends/tables/headroom_summary.csv",f"{OUT}/06_process_control/headroom/headroom_summary.csv")
print("=== clarification suppression by headroom (compression) ===")
for s in summ:
    if s["metric"]=="clarification" and s["contrast"]=="C4-C1":
        print(f"  {s['headroom_group']}: est={s['est']:+.3f} CI[{s['ci_low']:+.3f},{s['ci_high']:+.3f}] p={s['p']} same_dir={s['same_dir']} n={s['n_tasks']}")
print("03 done")
