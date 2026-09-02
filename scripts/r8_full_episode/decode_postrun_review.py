#!/usr/bin/env python3
"""R8: DECODE the post-run blind trajectory review (fixes review finding #2/#3).

The blind review randomized X/Y per pair so reviewers could not infer the condition.
That randomization key (`_treat_is`) was computed but never persisted, which made the
labels UN-DECODABLE: "meaningful_process_change" only said "the two runs differ", with
the sign randomized away.

The sampling is fully seeded (random.Random(8)), so this script deterministically
REPRODUCES the identical sample and flip decisions, joins them to the already-collected
reviewer labels, and reports:
  - the directional breakdown (was the TREATMENT arm the side judged to do more/different
    process work?),
  - Cohen's kappa (chance-corrected agreement) instead of the raw agreement rate,
  - an explicit note that the sample is ENRICHED (top-gap stratum) and is therefore
    NOT a base rate.

No new LLM calls: it re-uses reports/.../POST_RUN_REVIEW_{A,B}.json.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def rebuild_sample(metrics: pathlib.Path, min_pairs: int):
    """Deterministically reproduce the sample + flip key used by run_dual_review.postrun."""
    rows = [json.loads(l) for l in metrics.read_text().splitlines() if l.strip()]
    units = collections.defaultdict(dict)
    for r in rows:
        units[(r["domain"], r["task_id"], r["model"], r["replicate"])][r["condition"]] = r

    pairs = []
    for (dom, tid, model, rep), cond in units.items():
        for treat in ("C3", "C4"):
            if treat in cond and "C1" in cond:
                a, b = cond[treat], cond["C1"]
                gap = abs((a.get("total_agent_tool_calls") or 0) -
                          (b.get("total_agent_tool_calls") or 0))
                discord = (a.get("official_reward") != b.get("official_reward"))
                pairs.append(dict(dom=dom, tid=tid, model=model, rep=rep, treat=treat,
                                  gap=gap, discord=discord))
    rng = random.Random(8)                      # SAME seed as postrun()
    extremes = sorted(pairs, key=lambda p: -p["gap"])[:min_pairs // 3]
    discord = [p for p in pairs if p["discord"]][:min_pairs // 3]
    rest = [p for p in pairs if p not in extremes and p not in discord]
    rng.shuffle(rest)
    sample = extremes + discord + rest[:max(0, min_pairs - len(extremes) - len(discord))]
    sample = sample[:min_pairs]

    # replay the per-pair flip in the same call order as postrun()
    items = {}
    for i, pr in enumerate(sample):
        flip = rng.random() < 0.5               # SAME consumption order
        items[f"p{i}"] = {**pr, "treat_is": ("Y" if flip else "X"),
                          "stratum": ("extreme_gap" if i < len(extremes)
                                      else "endpoint_discordant" if i < len(extremes) + len(discord)
                                      else "random")}
    return items


def cohens_kappa(la: dict, lb: dict) -> dict:
    common = sorted(set(la) & set(lb))
    if not common:
        return {"kappa": None, "n": 0}
    labels = sorted({la[k] for k in common} | {lb[k] for k in common})
    n = len(common)
    po = sum(1 for k in common if la[k] == lb[k]) / n
    ca = collections.Counter(la[k] for k in common)
    cb = collections.Counter(lb[k] for k in common)
    pe = sum((ca[x] / n) * (cb[x] / n) for x in labels)
    kappa = (po - pe) / (1 - pe) if pe < 1 else None
    return {"n": n, "observed_agreement": round(po, 4), "chance_agreement": round(pe, 4),
            "kappa": (round(kappa, 4) if kappa is not None else None),
            "labels_used_A": len(set(ca)), "labels_used_B": len(set(cb))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/metrics/episode_metrics.jsonl")
    ap.add_argument("--reviews", type=pathlib.Path,
                    default=ROOT / "reports/r8_full_episode/reviews")
    ap.add_argument("--min-pairs", type=int, default=300)
    ap.add_argument("--out", type=pathlib.Path,
                    default=ROOT / "reports/r8_full_episode/reviews/POST_RUN_DECODED.json")
    args = ap.parse_args()

    key = rebuild_sample(args.metrics, args.min_pairs)
    va = json.loads((args.reviews / "POST_RUN_REVIEW_A.json").read_text())
    vb = json.loads((args.reviews / "POST_RUN_REVIEW_B.json").read_text())
    la = {x.get("pair"): x.get("label") for x in (va.get("labels") or [])}
    lb = {x.get("pair"): x.get("label") for x in (vb.get("labels") or [])}

    kap = cohens_kappa(la, lb)
    agreed = {k: la[k] for k in set(la) & set(lb) if la[k] == lb[k]}

    # DIRECTIONAL decode: the rubric asked "does Y do materially different/MORE process
    # work than X". So for a label to support "pressure -> more process", the TREATMENT
    # arm must be on side Y.
    by_dir = collections.Counter()
    mpc_treat_side = collections.Counter()
    for pid, lab in agreed.items():
        k = key.get(pid)
        if not k:
            continue
        by_dir[(lab, k["treat_is"])] += 1
        if lab == "meaningful_process_change":
            mpc_treat_side[k["treat_is"]] += 1
    n_mpc = sum(mpc_treat_side.values())
    # If pressure systematically produced "more process", treatment should land on Y more
    # often than chance (50%). Report the split honestly.
    frac_treat_Y = (mpc_treat_side["Y"] / n_mpc) if n_mpc else None

    strata = collections.Counter(v["stratum"] for v in key.values())
    out = {
        "n_pairs": len(key),
        "agreement": kap,
        "note_agreement": "Raw agreement was previously reported uncorrected; Cohen's kappa "
                          "is the correct chance-corrected statistic.",
        "agreed_label_dist": dict(collections.Counter(agreed.values())),
        "directional_decode": {
            "meaningful_process_change_n": n_mpc,
            "treatment_on_Y": mpc_treat_side["Y"], "treatment_on_X": mpc_treat_side["X"],
            "frac_treatment_on_Y": (round(frac_treat_Y, 4) if frac_treat_Y is not None else None),
            "interpretation": "The rubric is asymmetric ('does Y do more/different process "
                              "work than X'). Under the null of no directional pressure effect "
                              "this fraction is ~0.5. A value near 0.5 means the blind review "
                              "does NOT establish a directional pressure effect — it only "
                              "establishes that paired trajectories differ non-trivially.",
        },
        "sampling_strata": dict(strata),
        "enrichment_caveat": "The sample is ENRICHED BY CONSTRUCTION (stratum 1 = largest "
                             "tool-count gaps, stratum 2 = endpoint-discordant pairs). The "
                             "label counts are NOT a base rate and must never be quoted as one.",
        "scope": "Mechanism interpretation only. Does NOT override the pre-registered "
                 "quantitative primary (R4 calibrated null).",
    }
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({k: out[k] for k in ("n_pairs", "agreement", "agreed_label_dist",
                                          "directional_decode", "sampling_strata")},
                     indent=1, ensure_ascii=False))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
