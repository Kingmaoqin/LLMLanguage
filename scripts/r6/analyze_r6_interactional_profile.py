"""R6 interactional-robustness profile (round-6 §2, §6).

Builds the multidimensional profile report from the per-run metrics and the primary/secondary
contrasts: endpoint, tool trajectory, state transition, policy adherence, confirmation,
privacy/refusal/unsafe, efficiency, conversation management, plus model/task/layer/domain
dependence. The headline is never a single score; robustness is only asserted when no
PRIMARY contrast is FDR-significant in any family.

Outputs reports/r6_sensitivity/R6_INTERACTIONAL_ROBUSTNESS_PROFILE.md.
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
sys.path.insert(0, str(ROOT / "scripts" / "r6"))

from r6_contrasts import (  # noqa: E402
    PRIMARY_METRICS,
    SECONDARY_METRICS,
    add_tool_distance_to_neutral,
    analyze_contrasts,
    to_float,
)

DIMENSIONS = {
    "task_execution": ["final_state_correct"],
    "policy_adherence": ["policy_failure_any", "prohibited_tool_call_count"],
    "confirmation": ["confirmation_before_action_rate", "confirmation_obtained"],
    "privacy_refusal_unsafe": ["unsafe_compliance_or_privacy_violation", "privacy_violation",
                               "unsafe_compliance", "correct_refusal", "over_refusal"],
    "tool_trajectory": ["tool_sequence_norm_distance_to_neutral", "n_tool_events", "n_mutation_events"],
    "conversation": ["agent_side_abandonment", "continued_task_after_boundary"],
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default="results/r6_sensitivity/full_main")
    p.add_argument("--report", default="reports/r6_sensitivity/R6_INTERACTIONAL_ROBUSTNESS_PROFILE.md")
    p.add_argument(
        "--allow-deterministic-smoke",
        action="store_true",
        help="allow analysis of no-model deterministic smoke metrics; default refuses them",
    )
    return p


def _mean(rows, metric):
    vals = [to_float(r.get(metric)) for r in rows]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _is_false(value: Any) -> bool:
    return str(value).strip().lower() in {"false", "0", "no"}


def _is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def main() -> int:
    args = build_parser().parse_args()
    root = ROOT / args.root if not Path(args.root).is_absolute() else Path(args.root)
    metrics_csv = root / "interactional_metrics" / "per_run_metrics.csv"
    if not metrics_csv.exists():
        raise SystemExit(f"missing {metrics_csv}; run extract_r6_metrics.py first")
    rows = list(csv.DictReader(metrics_csv.open(encoding="utf-8")))
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
    sig = [r for r in primary if r["fdr_significant"]]
    sig_by_family = defaultdict(list)
    for r in sig:
        sig_by_family[r["family"]].append(r)

    # layer / domain / model coverage
    layers = sorted({r.get("layer") for r in rows if r.get("layer")})
    domains = sorted({r.get("domain") for r in rows if r.get("domain")})
    models = sorted({r.get("model_alias") for r in rows if r.get("model_alias")})
    conditions = sorted({r.get("condition_id") for r in rows if r.get("condition_id")})

    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# R6 Interactional Robustness Profile (round-6 §6)",
        "",
        f"Source: `{args.root}` ({len(rows)} runs). Models: {len(models)} ({', '.join(models)}). "
        f"Conditions: {len(conditions)}. Layers: {layers}. Domains: {domains}.",
        "",
        "## Headline",
        "",
        f"- PRIMARY FDR-significant contrasts: **{len(sig)}** across pure_valence / "
        "pressure_factorial / mechanism families.",
        ("- No PRIMARY contrast is FDR-significant: endpoint stability is accompanied by "
         "stability across policy, confirmation, privacy/refusal, trajectory, and conversation."
         if not sig else
         "- At least one PRIMARY contrast differs (see families below); endpoint stability alone "
         "does NOT establish interactional robustness (round-6 §15)."),
        "",
        "## PRIMARY significance by family",
        "",
        "| family | # FDR-significant |",
        "|---|---|",
        *[f"| {fam} | {len(sig_by_family.get(fam, []))} |"
          for fam in ("pure_valence", "pressure_factorial", "mechanism")],
        "",
        "## Dimension means by condition",
        "",
    ]
    by_cond = defaultdict(list)
    for r in rows:
        by_cond[r.get("condition_id")].append(r)
    for dim, metrics in DIMENSIONS.items():
        lines += [f"### {dim}", "", "| condition | " + " | ".join(metrics) + " |",
                  "|" + "---|" * (len(metrics) + 1)]
        for cond in conditions:
            cells = []
            for m in metrics:
                v = _mean(by_cond.get(cond, []), m)
                cells.append("n/a" if v is None else f"{v:.3f}")
            lines.append(f"| {cond} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += [
        "## Layer-C safety focus",
        "",
        "Layer C is where refusal/privacy/unsafe sensitivity is most likely. Rows below are "
        "Layer-C runs only.",
        "",
    ]
    layer_c = [r for r in rows if str(r.get("layer")) == "C"]
    for m in ["unsafe_compliance_or_privacy_violation", "correct_refusal", "over_refusal", "privacy_violation"]:
        per_cond = {cond: _mean([r for r in layer_c if r.get("condition_id") == cond], m) for cond in conditions}
        rendered = ", ".join(f"{c}={'n/a' if v is None else f'{v:.2f}'}" for c, v in per_cond.items())
        lines.append(f"- `{m}`: {rendered}")
    lines += [
        "",
        "Full contrasts: `analysis/primary_contrasts.csv`, `analysis/secondary_contrasts.csv`; "
        "noise floor: `analysis/noise_floor.csv`.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"R6 profile: {len(rows)} runs, {len(sig)} primary FDR-significant; report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
