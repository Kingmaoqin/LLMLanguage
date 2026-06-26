"""R6 statistical analysis (round-6 §9).

Reads ``<root>/interactional_metrics/per_run_metrics.csv``, computes the relative
tool-sequence distance-to-neutral, then produces paired contrasts for the pre-registered
PRIMARY metric family and (separately) the SECONDARY family, with task-cluster bootstrap
CIs, Wilcoxon cross-checks, and Benjamini-Hochberg FDR within each family. A mixed-effects
model is attempted via R/lme4 when available and otherwise marked NOT_FIT (the bootstrap is
canonical).

Outputs:
    <root>/analysis/primary_contrasts.csv
    <root>/analysis/secondary_contrasts.csv
    <root>/analysis/mixed_effects_results.csv
    reports/r6_sensitivity/R6_STATISTICAL_ANALYSIS.md
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "r6"))

from r6_contrasts import (  # noqa: E402
    PRIMARY_METRICS,
    SECONDARY_METRICS,
    add_tool_distance_to_neutral,
    analyze_contrasts,
)

CONTRAST_COLS = ["family", "contrast", "treatment", "reference", "metric", "n_pairs", "n_tasks",
                 "estimate", "ci_low", "ci_high", "bootstrap_p", "wilcoxon_p", "q_value", "fdr_significant"]


def load_metrics(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_contrasts(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CONTRAST_COLS)
        w.writeheader()
        for r in results:
            w.writerow({c: r.get(c) for c in CONTRAST_COLS})


def try_mixed_effects(metrics_csv: Path, out_csv: Path) -> dict[str, Any]:
    """Attempt an R/lme4 GLMM; record NOT_FIT if R/lme4 unavailable (bootstrap is canonical)."""
    rscript = ROOT / "scripts/r6/run_r6_glmm.R"
    if not rscript.exists() or not _has_rscript():
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        out_csv.write_text("outcome,status\nmixed_effects,NOT_FIT\n", encoding="utf-8")
        return {"status": "NOT_FIT", "reason": "Rscript or run_r6_glmm.R unavailable; bootstrap is canonical"}
    try:
        subprocess.run(["Rscript", str(rscript), str(metrics_csv), str(out_csv)], check=True,
                       cwd=str(ROOT), capture_output=True, timeout=900)
        return {"status": "FIT", "output": str(out_csv.relative_to(ROOT))}
    except Exception as exc:  # noqa: BLE001
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        out_csv.write_text(f"outcome,status\nmixed_effects,ERROR\n", encoding="utf-8")
        return {"status": "ERROR", "reason": str(exc)[:300]}


def _has_rscript() -> bool:
    try:
        subprocess.run(["Rscript", "--version"], capture_output=True, check=True)
        return True
    except Exception:  # noqa: BLE001
        return False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default="results/r6_sensitivity/full_main")
    p.add_argument("--report", default="reports/r6_sensitivity/R6_STATISTICAL_ANALYSIS.md")
    p.add_argument(
        "--allow-deterministic-smoke",
        action="store_true",
        help="allow analysis of no-model deterministic smoke metrics; default refuses them",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    root = ROOT / args.root if not Path(args.root).is_absolute() else Path(args.root)
    metrics_csv = root / "interactional_metrics" / "per_run_metrics.csv"
    if not metrics_csv.exists():
        raise SystemExit(f"missing {metrics_csv}; run extract_r6_metrics.py first")

    rows = load_metrics(metrics_csv)
    smoke_rows = [
        r for r in rows
        if _is_false(r.get("model_call_performed")) or _is_true(r.get("smoke_trace_only"))
    ]
    if smoke_rows and not args.allow_deterministic_smoke:
        raise SystemExit(
            f"refusing to analyze {len(smoke_rows)} no-model deterministic smoke rows as live R6 results; "
            "pass --allow-deterministic-smoke only for pipeline validation reports"
        )
    add_tool_distance_to_neutral(rows)

    primary = analyze_contrasts(rows, PRIMARY_METRICS)
    secondary = analyze_contrasts(rows, SECONDARY_METRICS)

    analysis_dir = root / "analysis"
    write_contrasts(analysis_dir / "primary_contrasts.csv", primary)
    write_contrasts(analysis_dir / "secondary_contrasts.csv", secondary)
    mixed = try_mixed_effects(metrics_csv, analysis_dir / "mixed_effects_results.csv")

    sig_primary = [r for r in primary if r["fdr_significant"]]
    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# R6 Statistical Analysis (round-6 §9)",
        "",
        f"Source: `{args.root}/interactional_metrics/per_run_metrics.csv` ({len(rows)} runs).",
        "Paired by (model, task, seed); task-cluster bootstrap (10k) + Wilcoxon + BH-FDR "
        "within each family. Pure-valence, pressure-factorial, and mechanism families are "
        "analysed separately (round-6 §9.2).",
        "",
        "## Pre-registered PRIMARY metrics",
        "",
        ", ".join(f"`{m}`" for m in PRIMARY_METRICS),
        "",
        f"- PRIMARY FDR-significant contrasts: **{len(sig_primary)}** / {len(primary)}",
        "",
    ]
    if sig_primary:
        lines += ["| family | contrast | metric | est | 95% CI | q |", "|---|---|---|---|---|---|"]
        for r in sorted(sig_primary, key=lambda x: (x["family"], x["contrast"], x["metric"])):
            lines.append(f"| {r['family']} | {r['contrast']} | {r['metric']} | "
                         f"{_fmt(r['estimate'])} | [{_fmt(r['ci_low'])}, {_fmt(r['ci_high'])}] | {_fmt(r['q_value'])} |")
    else:
        lines.append("_No PRIMARY contrast is FDR-significant._")
    lines += [
        "",
        "## Family breakdown (PRIMARY)",
        "",
        "| family | contrasts × metrics | FDR-significant |",
        "|---|---|---|",
    ]
    for family in ("pure_valence", "pressure_factorial", "mechanism"):
        fam = [r for r in primary if r["family"] == family]
        lines.append(f"| {family} | {len(fam)} | {sum(1 for r in fam if r['fdr_significant'])} |")
    lines += [
        "",
        f"## Mixed-effects model: {mixed['status']}",
        "",
        mixed.get("reason", mixed.get("output", "")),
        "",
        "Outputs: `analysis/primary_contrasts.csv`, `analysis/secondary_contrasts.csv`, "
        "`analysis/mixed_effects_results.csv`.",
        "",
        "Interpretation (round-6 §15): pure-valence and pressure are separate factors. A "
        "pressure-family effect with no pure-valence effect means directive pressure / "
        "authorization cues — not valence alone — drive action-level change. Secondary metrics "
        "are exploratory and not a main claim.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"R6 stats: primary={len(primary)} ({len(sig_primary)} sig), secondary={len(secondary)}, "
          f"mixed={mixed['status']}; report -> {args.report}")
    return 0


def _fmt(x: Any) -> str:
    try:
        return f"{float(x):+.3f}"
    except (TypeError, ValueError):
        return "n/a"


def _is_false(value: Any) -> bool:
    return str(value).strip().lower() in {"false", "0", "no"}


def _is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


if __name__ == "__main__":
    raise SystemExit(main())
