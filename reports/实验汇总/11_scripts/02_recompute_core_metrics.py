#!/usr/bin/env python3
"""Recompute episode/condition/task/model-level metrics from raw episodes (EPISODE_LEVEL).
Outputs under 02_recomputed_metrics/. Numbers are recomputed from source, not copied from old md."""
import csv, os
from collections import defaultdict
from _common import (OUT, load, ttype, mean, comp, infl, succ, clar, reads_bw, first_write,
                     vd, ve, tools, sel_score, sel_tokens)

B02=f"{OUT}/02_recomputed_metrics"
CONDS=["C0","C1","C2","C3","C4","C5"]

for batch in ["r9v2","r9v1_clean"]:
    recs=load(batch)
    # keep only BFCL for r9v1 (ToolSandbox schema differs); r9v2 all BFCL
    # ---- episode level ----
    ep_cols=["episode_id","batch","benchmark","model","task_id","task_type","family","condition","repeat",
             "success","outcome_class","infra_failure","clarification_turns","zero_clarification",
             "reads_before_write","first_write_step","verification_depth","verification_effort","total_tool_calls",
             "min_prereq","no_state_change","selector_score","selector_tokens"]
    with open(f"{B02}/episode_level/{batch}_episodes.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=ep_cols); w.writeheader()
        for r in recs:
            c=comp(r)
            cl=clar(r)
            w.writerow(dict(episode_id=r.get("episode_id"),batch=batch,benchmark=r.get("benchmark"),model=r.get("model"),
                task_id=r.get("task_id"),task_type=ttype(r.get("task_id")),family=r.get("family"),
                condition=r.get("condition"),repeat=r.get("repeat"),success=succ(r),outcome_class=r.get("outcome_class"),
                infra_failure=int(bool(r.get("infra_failure"))),clarification_turns=cl,
                zero_clarification=(1 if cl==0 else 0) if cl is not None else "",
                reads_before_write=reads_bw(r),first_write_step=first_write(r),verification_depth=vd(r),
                verification_effort=ve(r),total_tool_calls=tools(r),min_prereq=r.get("min_prereq_verification_calls"),
                no_state_change=(1 if c.get("no_state_change") else 0) if c else "",
                selector_score=sel_score(r),selector_tokens=sel_tokens(r)))
    # ---- condition level ----
    grp=defaultdict(lambda: defaultdict(list))
    for r in recs:
        if r.get("infra_failure"): continue
        k=(r.get("model"),r.get("family"),r.get("condition"))
        g=grp[k]
        g["success"].append(succ(r)); g["clar"].append(clar(r)); g["zeroclar"].append(1 if clar(r)==0 else (0 if clar(r) is not None else None))
        g["reads_bw"].append(reads_bw(r)); g["first_write"].append(first_write(r)); g["tools"].append(tools(r))
        if r.get("family")=="compression": g["vd"].append(vd(r))
        if r.get("family")=="inflation": g["ve"].append(ve(r))
    with open(f"{B02}/condition_level/{batch}_condition.csv","w",newline="") as f:
        cols=["model","family","condition","n","success_rate","zero_clar_rate","mean_clar","mean_reads_bw",
              "mean_first_write","mean_tools","mean_vd","mean_ve"]
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for (m,fam,c),g in sorted(grp.items()):
            w.writerow(dict(model=m,family=fam,condition=c,n=len(g["success"]),
                success_rate=round(mean(g["success"]),4),zero_clar_rate=round(mean(g["zeroclar"]),4),
                mean_clar=round(mean(g["clar"]),4),mean_reads_bw=round(mean(g["reads_bw"]),4),
                mean_first_write=round(mean(g["first_write"]),4),mean_tools=round(mean(g["tools"]),4),
                mean_vd=round(mean(g["vd"]),4) if g["vd"] else "",mean_ve=round(mean(g["ve"]),4) if g["ve"] else ""))
    # ---- task level (C1 baseline + per condition means, for headroom/paired) ----
    tk=defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # task -> cond -> metric -> list
    for r in recs:
        if r.get("infra_failure"): continue
        t=r["task_id"]; c=r["condition"]
        tk[t][c]["clar"].append(clar(r)); tk[t][c]["vd"].append(vd(r) if r.get("family")=="compression" else None)
        tk[t][c]["ve"].append(ve(r) if r.get("family")=="inflation" else None); tk[t][c]["reads_bw"].append(reads_bw(r))
        tk[t][c]["first_write"].append(first_write(r)); tk[t][c]["tools"].append(tools(r)); tk[t][c]["success"].append(succ(r))
    with open(f"{B02}/task_level/{batch}_task.csv","w",newline="") as f:
        cols=["task_id","task_type"]+[f"{m}_{c}" for m in ["clar","vd","ve","success"] for c in CONDS]
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for t,cd in sorted(tk.items()):
            row=dict(task_id=t,task_type=ttype(t))
            for m in ["clar","vd","ve","success"]:
                for c in CONDS:
                    vals=[x for x in cd.get(c,{}).get(m,[]) if x is not None]
                    row[f"{m}_{c}"]=round(mean(vals),4) if vals else ""
            w.writerow(row)
    print(f"[{batch}] episode/condition/task CSVs written ({len(recs)} episodes)")
print("02 done ->", B02)
