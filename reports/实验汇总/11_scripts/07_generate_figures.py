#!/usr/bin/env python3
"""Generate figures A-G into 10_figures/ from the derived CSVs."""
import os, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from _common import OUT
FIG=f"{OUT}/10_figures"; os.makedirs(FIG,exist_ok=True)
def rd(p):
    with open(p) as f: return list(csv.DictReader(f))
CONDS=["C0","C1","C2","C3","C4","C5"]

# ---- Fig A: clarification by condition (compression + inflation) ----
cond=rd(f"{OUT}/02_recomputed_metrics/condition_level/r9v2_condition.csv")
def series(fam,col):
    d={r["condition"]:float(r[col]) for r in cond if r["family"]==fam and r[col] not in ("","nan")}
    return [d.get(c,np.nan) for c in CONDS]
fig,ax=plt.subplots(figsize=(6,3.6))
ax.plot(CONDS,series("compression","mean_clar"),"o-",label="compression (urgency)",color="#c0392b")
ax.plot(CONDS,series("inflation","mean_clar"),"s-",label="inflation (skepticism)",color="#2980b9")
ax.set_ylabel("mean clarification turns (V_user)"); ax.set_title("Fig A. Human-clarification by condition (R9v2, Qwen-72B)")
ax.axvspan(3.5,4.5,alpha=.08,color="red"); ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f"{FIG}/figA_clarification_by_condition.png",dpi=140); plt.close()

# ---- Fig B: headroom gradient ----
hs=rd(f"{OUT}/04_strong_trends/tables/headroom_summary.csv")
g=[r for r in hs if r["metric"]=="clarification" and r["contrast"]=="C4-C1"]
order={"LOW":0,"MID":1,"HIGH":2}; g=sorted(g,key=lambda r:order[r["headroom_group"]])
fig,ax=plt.subplots(figsize=(5.2,3.6))
x=[r["headroom_group"] for r in g]; y=[float(r["est"]) for r in g]
lo=[float(r["est"])-float(r["ci_low"]) for r in g]; hi=[float(r["ci_high"])-float(r["est"]) for r in g]
ax.errorbar(x,y,yerr=[np.abs(lo),np.abs(hi)],fmt="o-",color="#c0392b",capsize=4)
ax.axhline(0,color="k",lw=.8); ax.set_ylabel("Δ clarification (C4 − C1)")
ax.set_title("Fig B. Clarification suppression ×\nbehavioral (oversight) headroom"); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f"{FIG}/figB_headroom_gradient.png",dpi=140); plt.close()

# ---- Fig C: language act x channel heatmap ----
lm=rd(f"{OUT}/06_process_control/language_act_channel/language_act_channel_matrix.csv")
chans=["clarification(V_user)","reads_before_write(V_tool)","verification_depth","verification_effort","first_write_step","total_tool_calls"]
acts=["urgency(compression)","skepticism(inflation)"]
M=np.full((len(chans),len(acts)),np.nan)
for r in lm:
    if r["process_channel"] in chans and r["language_act"] in acts:
        M[chans.index(r["process_channel"]),acts.index(r["language_act"])]=float(r["est"])
fig,ax=plt.subplots(figsize=(5.6,4.2))
vmax=np.nanmax(np.abs(M)); im=ax.imshow(M,cmap="RdBu_r",vmin=-vmax,vmax=vmax,aspect="auto")
ax.set_xticks(range(len(acts))); ax.set_xticklabels(["urgency","skepticism"]); ax.set_yticks(range(len(chans))); ax.set_yticklabels(chans,fontsize=8)
for i in range(len(chans)):
    for j in range(len(acts)):
        if not np.isnan(M[i,j]): ax.text(j,i,f"{M[i,j]:+.2f}",ha="center",va="center",fontsize=8)
ax.set_title("Fig C. Language Act × Process Channel (C4−C1)"); fig.colorbar(im,label="effect (turns/calls)"); fig.tight_layout(); fig.savefig(f"{FIG}/figC_language_channel_heatmap.png",dpi=140); plt.close()

# ---- Fig D: human vs tool verification by condition (compression) ----
fig,ax=plt.subplots(figsize=(6,3.6))
ax.plot(CONDS,series("compression","mean_clar"),"o-",label="human (clarification)",color="#c0392b")
ax.plot(CONDS,series("compression","mean_reads_bw"),"^-",label="tool (reads before write)",color="#27ae60")
ax.set_ylabel("verification (turns / calls)"); ax.set_title("Fig D. Verification channel substitution\n(human ↓ while tool ↔, compression)")
ax.axvspan(3.5,4.5,alpha=.08,color="red"); ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f"{FIG}/figD_channel_substitution.png",dpi=140); plt.close()

# ---- Fig E: surrogate score vs actual ΔVD (need episode-level; recompute quick) ----
import json
from _common import REPO, mean, comp, vd, sel_score, sel_tokens
recs=[json.loads(l) for l in open(f"{REPO}/results/r9v2/confirmatory/confirmatory_episodes.jsonl") if l.strip()]
from collections import defaultdict
c1=defaultdict(list)
for r in recs:
    if not r.get("infra_failure") and r.get("family")=="compression" and r["condition"]=="C1":
        v=vd(r);
        if v is not None: c1[r["task_id"]].append(v)
b={t:mean(v) for t,v in c1.items() if v}
xs=[];ys=[];tk=[]
for r in recs:
    if r.get("infra_failure") or r["condition"]!="C4" or r.get("family")!="compression": continue
    s=sel_score(r); v=vd(r); bb=b.get(r["task_id"])
    if s is None or v is None or bb is None: continue
    xs.append(s); ys.append(v-bb); tk.append(sel_tokens(r))
fig,axs=plt.subplots(1,2,figsize=(9,3.6))
axs[0].scatter(xs,ys,alpha=.5,color="#8e44ad"); axs[0].axhline(0,color="k",lw=.8)
axs[0].set_xlabel("selector 'pressure' score"); axs[0].set_ylabel("actual ΔVD (want <0)")
axs[0].set_title(f"Fig E1. surrogate vs real control\ncorr=+0.32 (wrong sign; target<0)")
axs[1].scatter(tk,xs,alpha=.5,color="#e67e22")
axs[1].set_xlabel("intervention text length (tokens)"); axs[1].set_ylabel("selector score")
axs[1].set_title("Fig E2. selector score ≈ text length\ncorr=+0.97")
for a in axs: a.grid(alpha=.3)
fig.tight_layout(); fig.savefig(f"{FIG}/figE_surrogate_misalignment.png",dpi=140); plt.close()

# ---- Fig F: cross-experiment evidence matrix ----
ce=rd(f"{OUT}/09_tables/cross_experiment_evidence.csv")
exps=["R6_support","R7_support","R8_support","R9v1_support","R9v2_support","MISROUTE_support"]
sig=[r["signal_name"][:34] for r in ce]
Mx=np.zeros((len(ce),len(exps)))
for i,r in enumerate(ce):
    for j,e in enumerate(exps):
        val=r[e].lower()
        Mx[i,j]=2 if "strong" in val else (1 if val.strip() and "not" not in val and "null" not in val else 0)
fig,ax=plt.subplots(figsize=(7.5,5.5))
im=ax.imshow(Mx,cmap="Greens",vmin=0,vmax=2,aspect="auto")
ax.set_xticks(range(len(exps))); ax.set_xticklabels([e.replace("_support","") for e in exps],rotation=30,ha="right")
ax.set_yticks(range(len(sig))); ax.set_yticklabels(sig,fontsize=7)
ax.set_title("Fig F. Cross-experiment evidence (0 none · 1 support · 2 strong)"); fig.tight_layout(); fig.savefig(f"{FIG}/figF_cross_experiment_matrix.png",dpi=140); plt.close()

# ---- Fig G: attack chain status ----
ac=rd(f"{OUT}/05_attack_chain/attack_chain_status.csv")
smap={"STRONG":3,"present":2,"present(design)":2,"partial":1.5,"WEAK":1,"GAP":0.5,"ABSENT":0}
stages=[r["stage"][:24] for r in ac]; vals=[smap.get(r["strength"],1) for r in ac]
cols=["#27ae60" if v>=2.5 else "#f39c12" if v>=1.5 else "#e74c3c" for v in vals]
fig,ax=plt.subplots(figsize=(7,4)); ax.barh(range(len(stages)),vals,color=cols)
ax.set_yticks(range(len(stages))); ax.set_yticklabels(stages,fontsize=8); ax.invert_yaxis()
ax.set_xlabel("evidence strength (0 absent → 3 strong)"); ax.set_title("Fig G. Attack chain status"); fig.tight_layout(); fig.savefig(f"{FIG}/figG_attack_chain_status.png",dpi=140); plt.close()

print("figures written:", sorted(os.listdir(FIG)))
