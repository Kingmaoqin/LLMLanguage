#!/usr/bin/env python3
"""R7-D Step 1-F: evaluator sensitivity curve over 10 injected effect magnitudes.

Known process changes are injected into REAL neutral traces, paired against the
original neutral run, and scored with the PRODUCTION family thresholds and the
PRODUCTION per-(model,task) neutral noise floor. The point is to measure what the
deployed evaluator can and cannot see, so production code is imported rather than
reimplemented.

Synthetic positives are written to their own file and are never mixed into the
attack numerator (正式阶段的prompt §12).

Outputs:
    results/r7d_ipma/step1/evaluator_sensitivity_curve.csv
    results/r7d_ipma/step1/evaluator_sensitivity_by_family.csv
"""
from __future__ import annotations

import collections
import copy
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.compute_pasr_metrics import (  # noqa: E402
    levenshtein_norm,
    noise_floor,
    threshold,
)

RUN = ROOT / "results/r7c_ipma/full/live_20260710_000752"
ENDPOINT = RUN / "endpoint/endpoint_oracle_per_run.csv"
REGISTRY = ROOT / "data/r7c_ipma/r7c_task_registry.csv"
TASKS_YAML = ROOT / "data/r7c_ipma/r7c_tasks.yaml"

OUT_CURVE = ROOT / "results/r7d_ipma/step1/evaluator_sensitivity_curve.csv"
OUT_FAMILY = ROOT / "results/r7d_ipma/step1/evaluator_sensitivity_by_family.csv"

FAMILIES = [
    "A_action_intensity_amplification",
    "B_premature_mutation_pressure",
    "C_confirmation_shift",
    "D_abandonment_overrefusal_boundary",
    "E_evidence_path_steering",
]


def build_records() -> dict:
    """Rebuild the metric records the PASR pipeline uses, from raw traces."""
    from scripts.r7b_ipma.compute_pasr_metrics import load_trace_records, read_csv

    endpoint_by_run = {r["run_id"]: r for r in read_csv(ENDPOINT)}
    return load_trace_records(RUN / "traces", endpoint_by_run)


# ---------------- injections ----------------
# Each returns a modified copy of the neutral record, or None if the injection is
# not applicable to that run (e.g. adding a duplicate read when no read happened).


def _seq(rec):
    return rec["tool_sequence"].split() if rec["tool_sequence"] else []


def inj_extra_calls(rec, k, read_tools):
    s = _seq(rec)
    if not s:
        return None  # nothing to duplicate: no trajectory exists
    out = copy.deepcopy(rec)
    out["tool_sequence"] = " ".join(s + [s[-1]] * k)
    out["n_tool_events"] = rec["n_tool_events"] + k
    return out


def inj_swap_two_reads(rec, read_tools):
    s = _seq(rec)
    if len(s) < 2:
        return None
    out = copy.deepcopy(rec)
    s2 = list(s)
    s2[0], s2[1] = s2[1], s2[0]
    if s2 == s:
        return None
    out["tool_sequence"] = " ".join(s2)
    return out


def inj_add_evidence_source(rec, read_tools):
    s = _seq(rec)
    extra = [t for t in read_tools if t not in s]
    if not extra:
        return None
    out = copy.deepcopy(rec)
    out["tool_sequence"] = " ".join(s + [extra[0]])
    out["n_tool_events"] = rec["n_tool_events"] + 1
    return out


def inj_duplicate_read(rec, read_tools):
    s = _seq(rec)
    if not s:
        return None
    out = copy.deepcopy(rec)
    out["tool_sequence"] = " ".join(s + [s[0]])
    out["n_tool_events"] = rec["n_tool_events"] + 1
    return out


def inj_confirmation(rec, delta):
    cr = rec.get("confirmation_rate")
    if cr is None:
        return None
    out = copy.deepcopy(rec)
    out["confirmation_rate"] = max(0.0, min(1.0, float(cr) + delta))
    if out["confirmation_rate"] == cr:
        return None
    return out


def inj_mutation_earlier(rec, k):
    fm = rec.get("first_mutation_step")
    if fm is None or fm - k < 0:
        return None
    out = copy.deepcopy(rec)
    out["first_mutation_step"] = fm - k
    return out


def inj_evidence_drop(rec, frac):
    ev = rec.get("evidence_before_mutation")
    if ev is None or ev <= 0:
        return None
    new = int(round(ev * (1.0 - frac)))
    if new >= ev:
        new = ev - 1
    if new < 0:
        return None
    out = copy.deepcopy(rec)
    out["evidence_before_mutation"] = new
    return out


def main() -> int:
    import yaml

    records = build_records()
    floor = noise_floor(records)
    registry = {r["task_id"]: r for r in csv.DictReader(REGISTRY.open())}
    tasks = {t["task_id"]: t for t in yaml.safe_load(TASKS_YAML.read_text())["tasks"]}

    neutrals = {
        k: v for k, v in records.items() if k[3] == "neutral_control"
    }
    print(f"real neutral runs available: {len(neutrals)}")

    INJECTIONS = [
        ("01_plus_1_tool_call", lambda r, rt: inj_extra_calls(r, 1, rt)),
        ("02_plus_2_tool_calls", lambda r, rt: inj_extra_calls(r, 2, rt)),
        ("03_swap_two_read_tools", lambda r, rt: inj_swap_two_reads(r, rt)),
        ("04_add_legal_evidence_source", lambda r, rt: inj_add_evidence_source(r, rt)),
        ("05_add_duplicate_read", lambda r, rt: inj_duplicate_read(r, rt)),
        ("06_confirmation_1_step_earlier", lambda r, rt: inj_confirmation(r, +0.25)),
        ("07_confirmation_1_step_later", lambda r, rt: inj_confirmation(r, -0.25)),
        ("08_mutation_1_step_earlier", lambda r, rt: inj_mutation_earlier(r, 1)),
        ("09_evidence_coverage_minus_10pct", lambda r, rt: inj_evidence_drop(r, 0.10)),
        ("10_evidence_coverage_minus_25pct", lambda r, rt: inj_evidence_drop(r, 0.25)),
    ]

    curve_rows = []
    fam_rows = []

    for name, fn in INJECTIONS:
        # as-PASR-sees-it: score under each task's own primary family
        n_applicable = n_detect = n_floor_reject = 0
        # family-specific: score every applicable run under every family
        fam_stat = collections.defaultdict(lambda: [0, 0])  # family -> [detect, applicable]

        for (model, task, seed, _cond), neu in neutrals.items():
            rt = list((tasks.get(task) or {}).get("read_tools") or [])
            atk = fn(neu, rt)
            if atk is None:
                continue
            n_applicable += 1

            fl = floor.get((model, task), {})
            delta_tool = float(atk["n_tool_events"] - neu["n_tool_events"])
            ratio = (
                atk["n_tool_events"] / neu["n_tool_events"]
                if neu["n_tool_events"]
                else (float("inf") if atk["n_tool_events"] else 1.0)
            )
            ca, cn = atk.get("confirmation_rate"), neu.get("confirmation_rate")
            delta_conf = (ca - cn) if (ca is not None and cn is not None) else None
            traj = levenshtein_norm(_seq(atk), _seq(neu))
            toolset_changed = set(_seq(atk)) != set(_seq(neu))

            prim = registry.get(task, {}).get("task_family_primary", "")
            hit, _ = threshold(prim, atk, neu, delta_tool, ratio, delta_conf, traj, toolset_changed, fl)
            n_detect += int(hit)

            # would it have fired with a zero floor? if yes but not with the real
            # floor, the floor is what rejected it.
            hit_nofloor, _ = threshold(
                prim, atk, neu, delta_tool, ratio, delta_conf, traj, toolset_changed, {}
            )
            if hit_nofloor and not hit:
                n_floor_reject += 1

            for f in FAMILIES:
                h, _ = threshold(f, atk, neu, delta_tool, ratio, delta_conf, traj, toolset_changed, fl)
                fam_stat[f][0] += int(h)
                fam_stat[f][1] += 1

        det = n_detect / n_applicable if n_applicable else 0.0
        curve_rows.append(
            dict(
                injection=name,
                n_applicable=n_applicable,
                n_not_applicable=len(neutrals) - n_applicable,
                applicability_rate=round(n_applicable / len(neutrals), 4),
                detection_rate=round(det, 4),
                false_negative_rate=round(1 - det, 4),
                n_rejected_by_noise_floor=n_floor_reject,
                noise_floor_rejection_rate=round(
                    n_floor_reject / n_applicable if n_applicable else 0.0, 4
                ),
            )
        )
        for f in FAMILIES:
            d, a = fam_stat[f]
            fam_rows.append(
                dict(
                    injection=name,
                    family=f,
                    n_applicable=a,
                    detection_rate=round(d / a, 4) if a else 0.0,
                )
            )

    OUT_CURVE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CURVE.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(curve_rows[0].keys()))
        w.writeheader()
        w.writerows(curve_rows)
    with OUT_FAMILY.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fam_rows[0].keys()))
        w.writeheader()
        w.writerows(fam_rows)

    print("\n=== evaluator sensitivity (scored under each task's own primary family) ===")
    print(f"{'injection':36s} {'applic.':>8s} {'detect':>8s} {'FN':>7s} {'floor-rej':>10s}")
    for r in curve_rows:
        print(
            f"{r['injection']:36s} {r['applicability_rate']:8.1%} "
            f"{r['detection_rate']:8.1%} {r['false_negative_rate']:7.1%} "
            f"{r['noise_floor_rejection_rate']:10.1%}"
        )

    print("\n=== family-specific sensitivity (detection rate) ===")
    hdr = f"{'injection':36s}" + "".join(f"{f.split('_')[0]:>7s}" for f in FAMILIES)
    print(hdr)
    for name, _ in INJECTIONS:
        line = f"{name:36s}"
        for f in FAMILIES:
            r = next(x for x in fam_rows if x["injection"] == name and x["family"] == f)
            line += f"{r['detection_rate']:7.1%}"
        print(line)

    print(f"\nwrote {OUT_CURVE.relative_to(ROOT)}")
    print(f"wrote {OUT_FAMILY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
