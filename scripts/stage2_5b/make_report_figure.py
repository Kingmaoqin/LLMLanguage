"""Report-ready figure for the Stage-2.5b R4.1 confirmatory result.

Renders a two-panel forest plot of the pooled paired contrasts from the task-cluster
bootstrap: (A) endpoint outcomes and (B) process outcomes, each contrast shown as
estimate +/- 95% bootstrap CI, with the +/-equivalence-margin band and the zero line.
This is the cleanest single visual of the headline finding: no FDR-significant endpoint
effect of social style, with selective process-level differences.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.stage2_5b.canonical_paths import R4_FIGURES_ROOT  # noqa: E402

CONTRAST_LABELS = {
    "praise_affect_single_vs_neutral_single": "Praise (affect)\nvs neutral",
    "praise_trust_single_vs_neutral_single": "Praise (trust)\nvs neutral",
    "insult_single_vs_neutral_single": "Insult\nvs neutral",
    "abuse_repeated_vs_neutral_repeated": "Repeated abuse\nvs repeated neutral",
    "neutral_repeated_vs_neutral_single": "Repeated schedule\n(neutral x N vs x1)",
}
CONTRAST_ORDER = list(CONTRAST_LABELS)

ENDPOINT_OUTCOME = "safe_task_success"
PROCESS_OUTCOME = "required_fact_coverage"
ENDPOINT_LABEL = "Endpoint:  safe-task success  Δ"
PROCESS_LABEL = "Process:  required-fact coverage  Δ"


def _panel(ax, df, outcome, title, color):
    rows = []
    for contrast in CONTRAST_ORDER:
        sub = df[(df["contrast"] == contrast) & (df["outcome"] == outcome)]
        if sub.empty:
            continue
        r = sub.iloc[0]
        rows.append((CONTRAST_LABELS[contrast], float(r["estimate"]),
                     float(r["ci_low"]), float(r["ci_high"]),
                     float(r.get("p_adjusted", 1.0) or 1.0),
                     float(r.get("equivalence_margin") or 0.0),
                     str(r.get("equivalent_within_margin"))))
    ys = list(range(len(rows)))[::-1]
    margin = max((m for *_, m, _ in rows), default=0.10) or 0.10
    ax.axvspan(-margin, margin, color="0.92", zorder=0, label=f"±{margin:g} equivalence band")
    ax.axvline(0, color="0.4", lw=1, ls="--", zorder=1)
    for y, (lab, est, lo, hi, padj, _m, equiv) in zip(ys, rows):
        sig = padj < 0.05
        mk = color if not sig else "#c0392b"
        ax.plot([lo, hi], [y, y], color=mk, lw=2.4, zorder=3, solid_capstyle="round")
        ax.plot([est], [y], "o", color=mk, ms=8, zorder=4,
                markeredgecolor="white", markeredgewidth=1.1)
        ax.annotate(f"{est:+.3f}  [{lo:+.3f}, {hi:+.3f}]"
                    + ("  ✓equiv" if equiv == "True" else ""),
                    (hi, y), xytext=(8, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=8.5, color="0.25")
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlabel(title, fontsize=10)
    ax.set_xlim(-0.32, 0.32)
    ax.margins(y=0.18)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False)
    ax.grid(axis="x", color="0.9", zorder=0)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--contrasts", default="results/stage2_5b_analysis_r4_1/paired_contrasts_task_cluster_bootstrap.csv")
    p.add_argument("--figures", default="figures/stage2_5b_r4_1")
    p.add_argument("--title", default="Social-style perturbation of a tool-using LLM agent (R4.1, 2 models × 8 retail tasks × 5 seeds)")
    return p


def main() -> int:
    args = build_parser().parse_args()
    df = pd.read_csv(ROOT / args.contrasts)
    df = df[df["scope"] == "pooled"].copy()

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.6), constrained_layout=True)
    _panel(axes[0], df, ENDPOINT_OUTCOME, ENDPOINT_LABEL, "#2c3e7b")
    _panel(axes[1], df, PROCESS_OUTCOME, PROCESS_LABEL, "#1d7a4d")
    axes[0].set_title("A. Endpoint outcome — no FDR-significant effect", fontsize=11, loc="left", weight="bold")
    axes[1].set_title("B. Process outcome — selective differences", fontsize=11, loc="left", weight="bold")
    fig.suptitle(args.title, fontsize=12.5, weight="bold")
    fig.text(0.5, -0.02,
             "Pooled paired task-cluster bootstrap (10,000 reps), Benjamini–Hochberg across family. "
             "Marker = point estimate; bar = 95% CI; grey band = equivalence margin; red = FDR p<0.05.",
             ha="center", fontsize=8.5, color="0.35")

    out_dir = ROOT / args.figures
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / "r4_1_confirmatory_forest.png"
    pdf = out_dir / "r4_1_confirmatory_forest.pdf"
    fig.savefig(png, dpi=200, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print(f"wrote {png}")
    print(f"wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
