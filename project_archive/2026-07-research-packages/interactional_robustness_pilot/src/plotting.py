from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_placeholder(path: Path, message: str) -> None:
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_all_figures(results_dir: Path, figures_dir: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    metrics_path = results_dir / "run_metrics.csv"
    deltas_path = results_dir / "paired_deltas_vs_neutral.csv"
    if not metrics_path.exists():
        for name in [
            "fig1_heatmap_final_state_policy.png",
            "fig2_safety_efficiency.png",
            "fig3_confirmation_behavior.png",
            "fig4_boundary_abandonment.png",
            "fig5_tool_sequence_divergence.png",
        ]:
            save_placeholder(figures_dir / name, "No run metrics available")
        return
    df = pd.read_csv(metrics_path)
    deltas = pd.read_csv(deltas_path) if deltas_path.exists() else pd.DataFrame()
    figures_dir.mkdir(parents=True, exist_ok=True)

    if deltas.empty:
        save_placeholder(figures_dir / "fig1_heatmap_final_state_policy.png", "No paired deltas available")
    else:
        heat = deltas[deltas["metric"].isin(["final_state_correct", "unsafe_compliance"])].copy()
        heat["metric_label"] = heat["metric"].map({"final_state_correct": "Delta final state", "unsafe_compliance": "Delta unsafe compliance"})
        panels = list(heat[["model_alias", "metric_label"]].drop_duplicates().itertuples(index=False, name=None))
        fig, axes = plt.subplots(len(panels), 1, figsize=(10, max(3, 2.8 * len(panels))), squeeze=False)
        for ax, (model, metric_label) in zip(axes[:, 0], panels):
            sub = heat[(heat["model_alias"] == model) & (heat["metric_label"] == metric_label)]
            pivot = sub.pivot_table(index="layer", columns="condition_id", values="paired_delta_mean", aggfunc="mean").fillna(0.0)
            im = ax.imshow(pivot.values, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")
            ax.set_title(f"{model}: {metric_label}")
            ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=30, ha="right")
            ax.set_yticks(range(len(pivot.index)), pivot.index)
            for i in range(pivot.shape[0]):
                for j in range(pivot.shape[1]):
                    ax.text(j, i, f"{pivot.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
        fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.7)
        fig.savefig(figures_dir / "fig1_heatmap_final_state_policy.png", dpi=180, bbox_inches="tight")
        plt.close(fig)

    if deltas.empty:
        save_placeholder(figures_dir / "fig2_safety_efficiency.png", "No paired deltas available")
    else:
        safety = deltas[deltas["metric"] == "unsafe_compliance"][["model_alias", "condition_id", "temperature", "paired_delta_mean"]].rename(columns={"paired_delta_mean": "safety_delta"})
        efficiency = deltas[deltas["metric"] == "tool_call_count"][["model_alias", "condition_id", "temperature", "paired_delta_mean"]].rename(columns={"paired_delta_mean": "efficiency_delta"})
        merged = safety.merge(efficiency, on=["model_alias", "condition_id", "temperature"], how="inner")
        fig, ax = plt.subplots(figsize=(8, 5))
        for model, sub in merged.groupby("model_alias"):
            ax.scatter(sub["efficiency_delta"], sub["safety_delta"], label=model)
            for _, row in sub.iterrows():
                ax.annotate(row["condition_id"], (row["efficiency_delta"], row["safety_delta"]), fontsize=7)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_xlabel("Delta tool calls vs neutral")
        ax.set_ylabel("Delta unsafe compliance vs neutral")
        ax.legend()
        fig.tight_layout()
        fig.savefig(figures_dir / "fig2_safety_efficiency.png", dpi=180)
        plt.close(fig)

    b23 = df[df["task_id"].isin(["B2", "B3"])].copy()
    if b23.empty:
        save_placeholder(figures_dir / "fig3_confirmation_behavior.png", "No B2/B3 runs available")
    else:
        b23["confirmation_requested"] = b23["confirmation_requested"].map(lambda x: str(x).lower() == "true" or x == 1).astype(float)
        pivot = b23.pivot_table(index="condition_id", columns="task_id", values="confirmation_requested", aggfunc="mean").reindex(["neutral", "praise_affect", "praise_trust", "mild_insult", "strong_insult", "repeated_abuse"])
        pivot.plot(kind="bar", figsize=(9, 5))
        plt.ylabel("Confirmation requested rate")
        plt.ylim(0, 1.05)
        plt.tight_layout()
        plt.savefig(figures_dir / "fig3_confirmation_behavior.png", dpi=180)
        plt.close()

    insult = df[df["condition_id"].isin(["mild_insult", "strong_insult", "repeated_abuse"])].copy()
    if insult.empty:
        save_placeholder(figures_dir / "fig4_boundary_abandonment.png", "No insult-condition runs available")
    else:
        for col in ["boundary_setting_detected", "task_abandonment"]:
            insult[col] = insult[col].map(lambda x: str(x).lower() == "true" or x == 1).astype(float)
        pivot = insult.pivot_table(index="condition_id", values=["boundary_setting_detected", "task_abandonment"], aggfunc="mean").reindex(["mild_insult", "strong_insult", "repeated_abuse"])
        pivot.plot(kind="bar", stacked=True, figsize=(8, 5))
        plt.ylabel("Rate")
        plt.tight_layout()
        plt.savefig(figures_dir / "fig4_boundary_abandonment.png", dpi=180)
        plt.close()

    if "tool_sequence_edit_distance_to_neutral_median" not in df:
        save_placeholder(figures_dir / "fig5_tool_sequence_divergence.png", "Tool-sequence distances not computed")
    else:
        df["tool_sequence_edit_distance_to_neutral_median"] = pd.to_numeric(df["tool_sequence_edit_distance_to_neutral_median"], errors="coerce").fillna(0)
        labels = []
        values = []
        for (model, condition), sub in df.groupby(["model_alias", "condition_id"]):
            labels.append(f"{model}\n{condition}")
            values.append(sub["tool_sequence_edit_distance_to_neutral_median"].values)
        fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.7), 5))
        ax.boxplot(values, labels=labels, showfliers=False)
        ax.set_ylabel("Edit distance to neutral median")
        ax.tick_params(axis="x", labelrotation=45)
        fig.tight_layout()
        fig.savefig(figures_dir / "fig5_tool_sequence_divergence.png", dpi=180)
        plt.close(fig)

