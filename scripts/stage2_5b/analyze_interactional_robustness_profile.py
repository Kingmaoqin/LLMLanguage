"""Multidimensional interactional-robustness profile analysis (round-5 §6, §10, §14).

Reads the per-run interactional metrics and produces, for each social-valence contrast,
the paired effect on every dimension (endpoint / tool / trajectory / policy / efficiency /
conversation). Each metric gets a mean paired delta, task-cluster bootstrap 95% CI,
Wilcoxon signed-rank p, and a Benjamini-Hochberg q within the contrast family.

The headline is deliberately NOT a single score: robustness is asserted only if no dimension
shows an FDR-significant difference; any significant trajectory/policy/state/conversation
difference counts against robustness even when the endpoint is unchanged (round-5 §14).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "stage2_5b"))

from scipy.stats import wilcoxon  # noqa: E402

from task_cluster_bootstrap import benjamini_hochberg, task_cluster_bootstrap  # noqa: E402
from src.stage2_5b.metrics.trace_metrics import DIMENSIONS  # noqa: E402

CONTRASTS = {
    "praise_affect": ("praise_affect_single", "neutral_single"),
    "praise_trust": ("praise_trust_single", "neutral_single"),
    "insult": ("insult_single", "neutral_single"),
    "repeated_abuse": ("abuse_repeated", "neutral_repeated"),
    "repeated_schedule": ("neutral_repeated", "neutral_single"),
}

# flatten unique metrics across dimensions, preserving dimension tag
METRIC_DIM = {}
for dim, metrics in DIMENSIONS.items():
    for m in metrics:
        METRIC_DIM.setdefault(m, dim)
METRICS = list(METRIC_DIM)


def _f(value: str) -> float | None:
    if value is None or value == "":
        return None
    v = str(value).strip().lower()
    if v in {"true", "false"}:
        return 1.0 if v == "true" else 0.0
    try:
        return float(value)
    except ValueError:
        return None


def load_rows(path: Path) -> list[dict[str, Any]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def pair_key(row: dict[str, Any]) -> tuple:
    return (row["model_alias"], row["task_id"], row["seed"], row.get("template_block", ""))


def build_pairs(rows, treatment, reference):
    by_cond = defaultdict(dict)
    for r in rows:
        if str(r.get("invalid_run")).lower() == "true":
            continue
        by_cond[r["condition_id"]][pair_key(r)] = r
    t_rows, r_rows = by_cond.get(treatment, {}), by_cond.get(reference, {})
    keys = sorted(set(t_rows) & set(r_rows))
    if not keys:  # fall back to seed-level pairing if template blocks don't align
        def k2(r):
            return (r["model_alias"], r["task_id"], r["seed"])
        t2, r2 = defaultdict(list), defaultdict(list)
        for r in rows:
            if str(r.get("invalid_run")).lower() == "true":
                continue
            if r["condition_id"] == treatment:
                t2[k2(r)].append(r)
            elif r["condition_id"] == reference:
                r2[k2(r)].append(r)
        return [(t2[k][0], r2[k][0]) for k in sorted(set(t2) & set(r2))]
    return [(t_rows[k], r_rows[k]) for k in keys]


def analyze(rows) -> list[dict[str, Any]]:
    results = []
    for contrast, (treatment, reference) in CONTRASTS.items():
        pairs = build_pairs(rows, treatment, reference)
        family_rows = []
        for metric in METRICS:
            deltas = []
            for t, r in pairs:
                tv, rv = _f(t.get(metric)), _f(r.get(metric))
                if tv is None or rv is None:
                    continue
                deltas.append({"task_id": t["task_id"], "delta": tv - rv})
            if not deltas:
                family_rows.append({"contrast": contrast, "dimension": METRIC_DIM[metric],
                                    "metric": metric, "n_pairs": 0, "estimate": None,
                                    "ci_low": None, "ci_high": None, "wilcoxon_p": None})
                continue
            boot = task_cluster_bootstrap(deltas, value_key="delta")
            diffs = [d["delta"] for d in deltas]
            try:
                wp = float(wilcoxon(diffs).pvalue) if any(d != 0 for d in diffs) else 1.0
            except ValueError:
                wp = 1.0
            family_rows.append({
                "contrast": contrast, "dimension": METRIC_DIM[metric], "metric": metric,
                "n_pairs": boot["n_pairs"], "n_tasks": boot["n_tasks"],
                "estimate": boot["estimate"], "ci_low": boot["ci_low"],
                "ci_high": boot["ci_high"], "wilcoxon_p": wp,
            })
        ps = [r["wilcoxon_p"] for r in family_rows if r["wilcoxon_p"] is not None]
        q = dict(zip([id(r) for r in family_rows if r["wilcoxon_p"] is not None],
                     benjamini_hochberg(ps)))
        for r in family_rows:
            r["q_value"] = q.get(id(r))
            r["fdr_significant"] = (r["q_value"] is not None and r["q_value"] < 0.05)
        results.extend(family_rows)
    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="results/stage2_5b_repair/r4_1_confirmatory_canonical")
    p.add_argument("--report", default="reports/measurement_repair/INTERACTIONAL_ROBUSTNESS_PROFILE.md")
    return p


def main() -> int:
    args = build_parser().parse_args()
    root = ROOT / args.root
    rows = load_rows(root / "interactional_metrics" / "per_run_metrics.csv")
    out_dir = root / "interactional_metrics"
    results = analyze(rows)

    cols = ["contrast", "dimension", "metric", "n_pairs", "n_tasks", "estimate",
            "ci_low", "ci_high", "wilcoxon_p", "q_value", "fdr_significant"]
    with (out_dir / "robustness_profile_contrasts.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in results:
            w.writerow({c: r.get(c) for c in cols})

    sig = [r for r in results if r["fdr_significant"]]
    by_dim_sig = defaultdict(list)
    for r in sig:
        by_dim_sig[r["dimension"]].append(r)

    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Interactional Robustness Profile (round-5 §6, §14)",
        "",
        f"Source: `{args.root}/interactional_metrics/per_run_metrics.csv` "
        f"({len(rows)} runs).",
        "Paired by (model, task, seed, template_block); task-cluster bootstrap (10k) CI + "
        "Wilcoxon signed-rank + Benjamini-Hochberg within each contrast family.",
        "",
        "## Headline",
        "",
        f"- FDR-significant dimension differences: **{len(sig)}** across all contrasts/metrics.",
        ("- No dimension shows an FDR-significant difference: endpoint stability is "
         "accompanied by trajectory/policy/state/conversation stability."
         if not sig else
         "- At least one non-endpoint dimension differs (see below): endpoint stability alone "
         "does NOT establish interactional robustness."),
        "",
        "## FDR-significant findings by dimension",
        "",
    ]
    if sig:
        lines += ["| contrast | dimension | metric | est | 95% CI | q |", "|---|---|---|---|---|---|"]
        for r in sorted(sig, key=lambda x: (x["dimension"], x["contrast"])):
            lines.append(
                f"| {r['contrast']} | {r['dimension']} | {r['metric']} | {r['estimate']:+.3f} | "
                f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | {r['q_value']:.3f} |")
    else:
        lines.append("_None._")
    lines += [
        "",
        "## Per-dimension significance count",
        "",
        "| dimension | n FDR-significant |",
        "|---|---|",
        *[f"| {dim} | {len(by_dim_sig.get(dim, []))} |" for dim in DIMENSIONS],
        "",
        "Full table: `interactional_metrics/robustness_profile_contrasts.csv`.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"profile: {len(results)} contrast×metric rows, {len(sig)} FDR-significant; report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
