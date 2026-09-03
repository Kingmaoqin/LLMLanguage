#!/usr/bin/env python3
"""Language Act x Process Channel matrix (C4-C1) + surrogate misalignment by regime.
Outputs under 06_process_control/language_act_channel/ and 07_adaptive_static/surrogate_analysis/."""
import csv, os
from collections import defaultdict
from _common import (OUT, load, mean, comp, clar, reads_bw, first_write, vd, ve, tools,
                     paired_task, pearson, sel_score, sel_tokens)

recs=[r for r in load("r9v2") if not r.get("infra_failure")]

CHAN={
 "clarification(V_user)":      ("both", clar),
 "reads_before_write(V_tool)": ("both", reads_bw),
 "verification_depth":         ("compression", vd),
 "verification_effort":        ("inflation", ve),
 "first_write_step":           ("both", first_write),
 "total_tool_calls":           ("both", tools),
}
os.makedirs(f"{OUT}/06_process_control/language_act_channel",exist_ok=True)
rows=[]
for ch,(fam_scope,m) in CHAN.items():
    for act,fam in [("urgency(compression)","compression"),("skepticism(inflation)","inflation")]:
        if fam_scope!="both" and fam_scope!=fam: continue
        s=paired_task(recs,fam,m,"C4")
        if s: rows.append(dict(process_channel=ch,language_act=act,contrast="C4-C1",**s))
with open(f"{OUT}/06_process_control/language_act_channel/language_act_channel_matrix.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# Process-Control Action Space (assembled) -> written by 06; here also emit explicit C5 channel effects
rowsC5=[]
for ch,(fam_scope,m) in CHAN.items():
    for act,fam in [("explicit-verify-less(compression)","compression"),("explicit-verify-more(inflation)","inflation")]:
        if fam_scope!="both" and fam_scope!=fam: continue
        s=paired_task(recs,fam,m,"C5")
        if s: rowsC5.append(dict(process_channel=ch,language_act=act,contrast="C5-C1",**s))
with open(f"{OUT}/06_process_control/language_act_channel/explicit_channel_effects.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rowsC5[0].keys())); w.writeheader(); w.writerows(rowsC5)

# --- surrogate misalignment overall + by headroom regime ---
c1vd=defaultdict(list)
for r in recs:
    if r.get("family")=="compression" and r["condition"]=="C1" and vd(r) is not None:
        c1vd[r["task_id"]].append(vd(r))
bvd={t:mean(v) for t,v in c1vd.items() if v}
def regime(pred):
    sc=[];dv=[];tk=[]
    for r in recs:
        if r["condition"]!="C4" or r.get("family")!="compression": continue
        if not pred(r): continue
        s=sel_score(r); v=vd(r); b=bvd.get(r["task_id"])
        if s is None or v is None or b is None: continue
        sc.append(s); dv.append(v-b); tk.append(sel_tokens(r))
    cor,nn=pearson(list(zip(sc,dv)))
    cortok,_=pearson(list(zip(sc,tk)))
    cortok_vd,_=pearson(list(zip(tk,dv)))
    return dict(corr_selector_dVD=cor,corr_selector_tokens=cortok,corr_tokens_dVD=cortok_vd,n=nn)
os.makedirs(f"{OUT}/07_adaptive_static/surrogate_analysis",exist_ok=True)
sur=[]
sur.append(dict(regime="ALL",**regime(lambda r:True)))
sur.append(dict(regime="min_prereq=1(low headroom)",**regime(lambda r:r.get("min_prereq_verification_calls")==1)))
sur.append(dict(regime="min_prereq>=2(high headroom)",**regime(lambda r:(r.get("min_prereq_verification_calls") or 0)>=2)))
with open(f"{OUT}/07_adaptive_static/surrogate_analysis/surrogate_misalignment_by_regime.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(sur[0].keys())); w.writeheader(); w.writerows(sur)
print("=== Language Act x Channel (C4-C1) ==="); [print(f"  {r['process_channel']:28s} {r['language_act']:22s} est={r['est']:+.3f} CI[{r['ci_low']:+.2f},{r['ci_high']:+.2f}]") for r in rows]
print("=== surrogate ==="); [print(" ",s) for s in sur]
print("04 done")
