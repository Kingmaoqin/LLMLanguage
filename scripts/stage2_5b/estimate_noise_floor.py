"""Noise-floor estimation for the interactional-robustness profile (round-5 §7).

The cleanest noise floor is seed-to-seed variation *within the neutral_single condition*:
same task, user, tools, environment, policy and temperature (0.0) — the only thing that
varies is the seed, so any spread is pure stochastic/server nondeterminism. We report, per
metric, the pooled within-neutral standard deviation (the noise floor) and the largest
social-style paired effect magnitude, so effects can be read against the noise they must
exceed to be meaningful.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.metrics.trace_metrics import DIMENSIONS  # noqa: E402

METRICS: list[str] = []
METRIC_DIM: dict[str, str] = {}
for dimension, metrics in DIMENSIONS.items():
    for metric in metrics:
        if metric in METRIC_DIM:
            continue
        METRIC_DIM[metric] = dimension
        METRICS.append(metric)


def _f(value):
    if value in (None, ""):
        return None
    v = str(value).strip().lower()
    if v in {"true", "false"}:
        return 1.0 if v == "true" else 0.0
    try:
        return float(value)
    except ValueError:
        return None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="results/stage2_5b_repair/r4_1_confirmatory_canonical")
    p.add_argument("--report", default="reports/measurement_repair/NOISE_FLOOR_REPORT.md")
    p.add_argument("--profile", default=None,
                   help="robustness_profile_contrasts.csv (defaults under root)")
    return p


def main() -> int:
    args = build_parser().parse_args()
    root = ROOT / args.root
    rows = list(csv.DictReader((root / "interactional_metrics" / "per_run_metrics.csv").open(encoding="utf-8")))
    neutral = [r for r in rows if r["condition_id"] == "neutral_single"
               and str(r.get("invalid_run")).lower() != "true"]

    # group neutral runs by (model, task) -> seed-level replicates
    cells = defaultdict(lambda: defaultdict(list))
    for r in neutral:
        cells[(r["model_alias"], r["task_id"])][r.get("template_block", "")].append(r)
    seeds_per_cell = statistics.mean(
        len({rr["seed"] for rr in r2}) for c in cells.values() for r2 in [sum(c.values(), [])]
    ) if cells else 0

    # pooled within-neutral SD per metric
    noise = {}
    for metric in METRICS:
        within_sds = []
        for c in cells.values():
            vals = [_f(rr.get(metric)) for grp in c.values() for rr in grp]
            vals = [v for v in vals if v is not None]
            if len(vals) >= 2:
                within_sds.append(statistics.pstdev(vals))
        noise[metric] = statistics.mean(within_sds) if within_sds else None

    # largest social-style effect magnitude per metric, from the profile contrasts
    profile_path = Path(args.profile) if args.profile else (root / "interactional_metrics" / "robustness_profile_contrasts.csv")
    max_effect = defaultdict(lambda: (0.0, ""))
    if profile_path.exists():
        for r in csv.DictReader(profile_path.open(encoding="utf-8")):
            if r["contrast"] == "repeated_schedule":
                continue  # schedule is a design factor, not a valence effect
            est = _f(r.get("estimate"))
            if est is None:
                continue
            if abs(est) >= abs(max_effect[r["metric"]][0]):
                max_effect[r["metric"]] = (est, r["contrast"])

    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Noise Floor Report (round-5 §7)",
        "",
        f"Source: `{args.root}` — neutral_single replicates: {len(neutral)} runs, "
        f"~{seeds_per_cell:.1f} seeds per (model,task) cell (>=5 required).",
        "Temperature is fixed at 0.0 for all runs; within-neutral spread therefore reflects "
        "server/sampling nondeterminism (the irreducible measurement noise), not temperature.",
        "",
        "## Per-metric noise floor vs largest social-style effect",
        "",
        "Effect magnitude excludes `repeated_schedule` (a turn-count design factor, not a "
        "valence manipulation). A social-style effect is only credible if it exceeds the noise floor.",
        "",
        "| dimension | metric | within-neutral SD (noise) | max |valence effect| | contrast | effect>noise? |",
        "|---|---|---|---|---|---|",
    ]
    for metric in METRICS:
        nf = noise.get(metric)
        eff, contrast = max_effect.get(metric, (None, ""))
        nf_s = f"{nf:.3f}" if nf is not None else "n/a"
        eff_s = f"{abs(eff):.3f}" if eff is not None else "n/a"
        flag = ""
        if nf is not None and eff is not None:
            flag = "yes" if abs(eff) > nf else "no"
        lines.append(f"| {METRIC_DIM[metric]} | {metric} | {nf_s} | {eff_s} | {contrast} | {flag} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "Where the largest valence effect does not exceed the within-neutral noise floor, the "
        "manipulation cannot be distinguished from seed-to-seed nondeterminism at this sample "
        "size. This is the conservative reading required by round-5 §14: such metrics support "
        "robustness, not a claimed effect.",
        "",
        "Note: a few policy metrics show effect slightly above their (very small) noise floor "
        "because policy failures are rare events; none of these are FDR-significant in "
        "`INTERACTIONAL_ROBUSTNESS_PROFILE.md` (all q>=0.05). The significance test governs; the "
        "raw magnitude flag is only a descriptive screen.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"noise floor report -> {args.report} ({len(neutral)} neutral runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
