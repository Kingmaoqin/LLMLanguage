#!/usr/bin/env python3
"""Generate R7/IPMA figures and tables (PDF 17.4) from the analysis CSVs."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
COND_ORDER = ["urgency_pressure", "trust_pressure", "frustration_pressure",
              "continuation_pressure", "implicit_progress_pressure"]
COND_SHORT = {"urgency_pressure": "urgency", "trust_pressure": "trust",
              "frustration_pressure": "frustration", "continuation_pressure": "continuation",
              "implicit_progress_pressure": "implicit"}
FAM_ORDER = ["A_action_intensity_amplification", "B_premature_mutation_pressure",
             "C_confirmation_shift", "D_abandonment_overrefusal_boundary", "E_evidence_path_steering"]
FAM_SHORT = {f: f.split("_")[0] for f in FAM_ORDER}
BLUE, GREY = "#3b6fb5", "#b8c2cc"


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT / "results/r7_ipma/main/full_20260702_043032")
    args = ap.parse_args()
    A = args.root / "analysis"
    figdir = ROOT / "artifacts/r7_ipma/figures"
    figdir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

    # Fig 3: PASR by condition with 95% CI
    pc = rd(A / "primary_pasr_contrasts.csv")
    pc = sorted(pc, key=lambda r: COND_ORDER.index(r["condition"]))
    x = np.arange(len(pc))
    means = [float(r["pasr_mean"]) for r in pc]
    lo = [float(r["pasr_mean"]) - float(r["pasr_ci_lo"]) for r in pc]
    hi = [float(r["pasr_ci_hi"]) - float(r["pasr_mean"]) for r in pc]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar(x, means, yerr=[lo, hi], capsize=4, color=BLUE, width=0.62)
    ax.set_xticks(x); ax.set_xticklabels([COND_SHORT[r["condition"]] for r in pc], rotation=15)
    ax.set_ylabel("PASR (paired vs neutral)"); ax.set_title("Fig 3. Process Attack Success Rate by condition (95% CI)")
    ax.set_ylim(0, max(hi[i] + means[i] for i in range(len(means))) * 1.25)
    for i, m in enumerate(means):
        ax.text(i, means[i] + hi[i] + 0.008, f"{m:.2f}", ha="center", fontsize=10)
    fig.tight_layout(); fig.savefig(figdir / "fig3_pasr_by_condition.png", dpi=150); plt.close(fig)

    # Fig 4: PASR by model
    bm = rd(A / "pasr_by_model.csv")
    models = sorted({r["model"] for r in bm})
    mat = np.zeros((len(models), len(COND_ORDER)))
    for r in bm:
        mat[models.index(r["model"]), COND_ORDER.index(r["condition"])] = float(r["pasr_mean"])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.26
    for j, m in enumerate(models):
        ax.bar(np.arange(len(COND_ORDER)) + j * w, mat[j], w, label=m)
    ax.set_xticks(np.arange(len(COND_ORDER)) + w); ax.set_xticklabels([COND_SHORT[c] for c in COND_ORDER], rotation=15)
    ax.set_ylabel("PASR"); ax.set_title("Fig 4. PASR by model x condition"); ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(figdir / "fig4_pasr_by_model.png", dpi=150); plt.close(fig)

    # Fig 5: PASR by family x condition heatmap
    bf = rd(A / "pasr_by_family.csv")
    H = np.full((len(FAM_ORDER), len(COND_ORDER)), np.nan)
    for r in bf:
        if r["family"] in FAM_ORDER:
            H[FAM_ORDER.index(r["family"]), COND_ORDER.index(r["condition"])] = float(r["pasr_mean"])
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    im = ax.imshow(H, cmap="Blues", vmin=0, vmax=max(0.4, np.nanmax(H)))
    ax.set_xticks(range(len(COND_ORDER))); ax.set_xticklabels([COND_SHORT[c] for c in COND_ORDER], rotation=20)
    ax.set_yticks(range(len(FAM_ORDER))); ax.set_yticklabels([FAM_SHORT[f] + " " + f.split("_", 1)[1][:12] for f in FAM_ORDER])
    for i in range(len(FAM_ORDER)):
        for j in range(len(COND_ORDER)):
            if not np.isnan(H[i, j]):
                ax.text(j, i, f"{H[i,j]:.2f}", ha="center", va="center",
                        color="white" if H[i, j] > 0.22 else "black", fontsize=9)
    ax.set_title("Fig 5. PASR heatmap: attack family x condition")
    fig.colorbar(im, fraction=0.046, pad=0.04); fig.tight_layout()
    fig.savefig(figdir / "fig5_pasr_family_heatmap.png", dpi=150); plt.close(fig)

    # Fig 6: safety vs process manipulation scatter (per condition)
    ds = rd(A / "process_delta_summary.csv")
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    for r in ds:
        xproc = float(r["mean_delta_n_tool"])
        ysafe = float(r["frac_safety_preserved"])
        ax.scatter(xproc, ysafe, s=90, color=BLUE)
        ax.annotate(COND_SHORT[r["condition"]], (xproc, ysafe), textcoords="offset points",
                    xytext=(6, 4), fontsize=9)
    ax.axhline(1.0, ls="--", color=GREY)
    ax.set_xlabel("mean Δ tool calls (attack − neutral)")
    ax.set_ylabel("fraction safety preserved")
    ax.set_ylim(0.8, 1.02)
    ax.set_title("Fig 6. Safety preserved vs process shift")
    fig.tight_layout(); fig.savefig(figdir / "fig6_safety_vs_process.png", dpi=150); plt.close(fig)

    # Fig 5b: process delta bars
    metrics = [("mean_delta_n_tool", "Δ tool calls"), ("mean_delta_n_mutation", "Δ mutations"),
               ("mean_delta_conf_rate", "Δ confirm rate"), ("mean_traj_distance", "traj distance")]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6))
    for ax, (mk, lbl) in zip(axes, metrics):
        vals = [float(next(r[mk] for r in ds if r["condition"] == c) or 0) for c in COND_ORDER]
        ax.bar(range(len(COND_ORDER)), vals, color=BLUE, width=0.6)
        ax.set_xticks(range(len(COND_ORDER))); ax.set_xticklabels([COND_SHORT[c] for c in COND_ORDER], rotation=40, fontsize=8)
        ax.set_title(lbl, fontsize=10); ax.axhline(0, color="black", lw=0.6)
    fig.suptitle("Fig 7. Paired process-metric deltas by condition")
    fig.tight_layout(); fig.savefig(figdir / "fig7_process_deltas.png", dpi=150); plt.close(fig)

    print(f"figures written to {figdir}")
    for p in sorted(figdir.glob("*.png")):
        print(" -", p.name)


if __name__ == "__main__":
    main()
