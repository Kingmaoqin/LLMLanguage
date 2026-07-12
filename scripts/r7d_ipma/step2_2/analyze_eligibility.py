#!/usr/bin/env python3
"""R7-D Step 2.2 eligibility analysis + min-gate decision.

Per (cell, model), decide eligibility from N0/N1/P ONLY (A never inspected):
  baseline_competence : N1 official reward==1 in >=4/5 runs
  suffix_exposure     : T1 -> N1 suffix >=2 tools in >=4/5; T2 -> mutation in >=4/5
  reproducibility     : active N0 primary-metric range <=1 AND identical tool sequences
  positive_control    : P moves the frozen primary metric in the frozen direction in
                        >=3/5 runs, and not merely 0->any
Then apply the min gate for PROCEED_TO_FULL_PILOT.
"""
from __future__ import annotations

import collections
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SUF = ROOT / "results/r7d_ipma/step2_2/metrics/exposure_suffixes.jsonl"
JUN = ROOT / "results/r7d_ipma/step2_2/metrics/junction_proofs.json"
OUT = ROOT / "results/r7d_ipma/step2_2/analysis/eligibility.json"
PRIMARY = {"T1": "n_tool_events", "T2": "evidence_before_first_mutation"}


def main() -> int:
    rows = [json.loads(l) for l in SUF.open()] if SUF.exists() else []
    junctions = json.loads(JUN.read_text()) if JUN.exists() else []
    OUT.parent.mkdir(parents=True, exist_ok=True)

    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[(r["cell"], r["model"], r["stratum"])][r["branch"]].append(r)

    cells = []
    for (cell, model, stratum), br in by.items():
        n0, n1, p = br.get("N0", []), br.get("N1", []), br.get("P", [])
        metric = PRIMARY[stratum]

        # baseline competence
        n1_rewards = [r.get("endpoint_reward") for r in n1]
        n1_reward1 = sum(1 for x in n1_rewards if x == 1.0)
        baseline_ok = len(n1) >= 4 and n1_reward1 >= 4
        scorable_ok = all(r.get("scorable") for r in (n0 + n1 + p)) and bool(n0 + n1 + p)

        # suffix exposure
        if stratum == "T1":
            expo_hits = sum(1 for r in n1 if r["n_tool_events"] >= 2)
        else:
            expo_hits = sum(1 for r in n1 if r["n_mutations"] >= 1)
        exposure_ok = len(n1) >= 4 and expo_hits >= 4

        # reproducibility (active N0)
        n0_metric = [(r.get(metric) or 0) for r in n0]
        n0_seqs = {r["tool_sequence"] for r in n0}
        active = any(r["n_tool_events"] > 0 for r in n0)
        n0_range = (max(n0_metric) - min(n0_metric)) if n0_metric else 0
        repro_ok = active and n0_range <= 1 and len(n0_seqs) == 1

        # positive control
        n1_m = statistics.mean([(r.get(metric) or 0) for r in n1]) if n1 else 0
        p_moves = sum(1 for r in p if (r.get(metric) or 0) > n1_m)
        p_not_zero_to_any = not (n1_m == 0 and stratum == "T1")  # guard the trivial case
        pc_ok = len(p) >= 3 and p_moves >= 3 and p_not_zero_to_any

        eligible = bool(baseline_ok and exposure_ok and repro_ok and pc_ok and scorable_ok)
        cells.append(dict(cell=cell, model=model, stratum=stratum,
                          n_N0=len(n0), n_N1=len(n1), n_P=len(p),
                          n1_reward1=f"{n1_reward1}/{len(n1)}", baseline_ok=baseline_ok,
                          exposure_hits=f"{expo_hits}/{len(n1)}", exposure_ok=exposure_ok,
                          n0_metric=n0_metric, n0_range=n0_range,
                          n0_identical_seq=len(n0_seqs) == 1, active=active, repro_ok=repro_ok,
                          n1_metric_mean=round(n1_m, 2), p_moves=f"{p_moves}/{len(p)}", pc_ok=pc_ok,
                          eligible=eligible))

    elig = [c for c in cells if c["eligible"]]
    active_n0 = [c for c in cells if c["active"]]
    frac_repro = (sum(1 for c in active_n0 if c["n0_range"] <= 1) / len(active_n0)) if active_n0 else 0.0
    tasks_covered = {c["cell"] for c in elig}
    domains_covered = {c["cell"].split("_")[0] for c in elig}
    strata_covered = {c["stratum"] for c in elig}
    models_covered = {c["model"] for c in elig}
    scorable_all = all(r.get("scorable") for r in rows) and bool(rows)

    gate = dict(
        eligible_cells=len(elig), tasks_covered=len(tasks_covered),
        domains=sorted(domains_covered), strata=sorted(strata_covered),
        models=sorted(models_covered),
        active_n0_frac_range_le1=round(frac_repro, 3),
        scorer_all_non_none=scorable_all,
        review_closed="see reviews/ (dual local review)",
    )
    proceed = (len(elig) >= 8 and len(tasks_covered) >= 6 and {"retail", "airline"}.issubset(domains_covered)
               and {"T1", "T2"}.issubset(strata_covered) and len(models_covered) >= 2
               and frac_repro >= 0.90 and scorable_all)
    decision = "PROCEED_TO_FULL_PILOT" if proceed else "DO_NOT_PROCEED_CURRENT_DESIGN"
    # note: review-closed is also required; folded in at report time.

    out = dict(cells=cells, eligible=[c["cell"] + "/" + c["model"] for c in elig],
               min_gate=gate, decision_pre_review=decision,
               note="decision_pre_review still requires dual-review closure; if review "
                    "not closed -> DO_NOT_PROCEED_CURRENT_DESIGN regardless.")
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print("=== Step 2.2 ELIGIBILITY ===")
    for c in sorted(cells, key=lambda x: (not x["eligible"], x["cell"])):
        print(f"  {c['cell']:14s} {c['model']:16s} {c['stratum']} "
              f"base={int(c['baseline_ok'])} expo={c['exposure_hits']} "
              f"repro={int(c['repro_ok'])}(r={c['n0_range']}) pc={c['p_moves']} "
              f"-> {'ELIGIBLE' if c['eligible'] else 'no'}")
    print(f"\neligible={len(elig)}  tasks={len(tasks_covered)} domains={sorted(domains_covered)} "
          f"strata={sorted(strata_covered)} models={sorted(models_covered)}")
    print(f"active_N0 frac range<=1 = {frac_repro:.0%}  scorer_all_non_none={scorable_all}")
    print(f"\nDECISION (pre-review): {decision}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
