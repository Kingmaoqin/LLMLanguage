#!/usr/bin/env python3
"""R7-D Step 2.1 gate analysis: G1(real suffixes) / G2 / G3 / G4 verdicts.

Reads closure_suffixes.jsonl + junction_proofs.json and emits the four gate verdicts
and a machine-readable summary. Eligibility is computed from PRE-TREATMENT liveness
only (N1 tool activity), never from any treatment outcome.
"""
from __future__ import annotations

import collections
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SUF = ROOT / "results/r7d_ipma/step2_1/metrics/closure_suffixes.jsonl"
JUN = ROOT / "results/r7d_ipma/step2_1/metrics/junction_proofs.json"
OUT = ROOT / "results/r7d_ipma/step2_1/analysis/gate_verdicts.json"


def main() -> int:
    rows = [json.loads(l) for l in SUF.open()] if SUF.exists() else []
    junctions = json.loads(JUN.read_text()) if JUN.exists() else []
    OUT.parent.mkdir(parents=True, exist_ok=True)

    by_cm = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by_cm[(r["cell"], r["model"])][r["branch"]].append(r)

    # ---- G1: real suffixes scorable ----
    n_scorable = sum(1 for r in rows if r.get("scorable"))
    g1 = dict(n_real_suffixes=len(rows), n_scorable=n_scorable,
              all_scorable=len(rows) > 0 and n_scorable == len(rows),
              at_least_20_scorable=n_scorable >= 20)
    g1["verdict"] = "PASS" if (g1["at_least_20_scorable"] and g1["all_scorable"]) else "FAIL"

    # ---- G2: family junctions ----
    found = [j for j in junctions if j.get("junction_found")]
    g2_cells = []
    for j in found:
        p = j.get("proof", {})
        if j["stratum"] == "T1":
            valid = p.get("remaining_evidence_sources", 0) >= 2 and p.get("mutation_not_yet_done") and p.get("endpoint_not_complete")
        else:
            valid = p.get("mutation_not_yet_done") and p.get("endpoint_not_complete") and p.get("reads_done", 0) >= 1
        g2_cells.append(dict(cell=j["cell"], model=j["model"], stratum=j["stratum"], valid=bool(valid),
                             proof={k: p.get(k) for k in ("reads_done", "mutations_done",
                                    "remaining_evidence_sources", "confirmation_not_yet_done",
                                    "mutation_not_yet_done", "endpoint_not_complete")}))
    n_found = len(found)
    n_valid = sum(1 for c in g2_cells if c["valid"])
    # at least one valid junction per constructible stratum (T1 and T2)
    strata_with_valid = {c["stratum"] for c in g2_cells if c["valid"]}
    g2 = dict(n_cell_model_attempts=len(junctions), n_junctions_found=n_found,
              n_junctions_valid=n_valid, strata_with_valid_junction=sorted(strata_with_valid),
              cells=g2_cells)
    g2["verdict"] = "PASS" if {"T1", "T2"}.issubset(strata_with_valid) else "FAIL"

    # ---- G3: N0 exact-repeat reproducibility on ACTIVE snapshots ----
    g3_cells = []
    for (cell, model), br in by_cm.items():
        n0 = br.get("N0", [])
        if not n0:
            continue
        tools = [r["n_tool_events"] for r in n0]
        active = max(tools) > 0  # snapshot is "active" if any N0 uses a tool
        seqs = {r["tool_sequence"] for r in n0}
        rng = (max(tools) - min(tools)) if tools else 0
        g3_cells.append(dict(cell=cell, model=model, n_n0=len(n0), n0_tools=tools,
                             tool_range=rng, identical_sequences=len(seqs) == 1,
                             active=active))
    active_cells = [c for c in g3_cells if c["active"]]
    if active_cells:
        frac_range_le1 = sum(1 for c in active_cells if c["tool_range"] <= 1) / len(active_cells)
        max_range = max(c["tool_range"] for c in active_cells)
    else:
        frac_range_le1, max_range = 0.0, 0
    g3 = dict(n_snapshots=len(g3_cells), n_active_snapshots=len(active_cells),
              frac_active_range_le1=round(frac_range_le1, 3), max_active_tool_range=max_range,
              cells=g3_cells,
              caveat="online vLLM: reproducibility rests on batch-invariance + fixed served-name/"
                     "parser/concurrency=1; not offline-deterministic, so not bit-exact across "
                     "hardware/version changes.")
    g3["verdict"] = "PASS" if (len(active_cells) > 0 and frac_range_le1 >= 0.90 and max_range <= 2) else "FAIL"

    # ---- G4: active-model positive control (eligibility PRE-TREATMENT via N1 liveness) ----
    g4_cells = []
    for (cell, model), br in by_cm.items():
        n1 = br.get("N1", [])
        p = br.get("P", [])
        if not n1 or not p:
            continue
        stratum = n1[0]["stratum"]
        n1_live = any(r["n_tool_events"] > 0 for r in n1)   # PRE-treatment liveness (N1 baseline)
        n1_reward_ok = any(r.get("endpoint_reward") is not None for r in n1)
        # P moves the primary metric in the pre-registered direction, in the suffix
        if stratum == "T1":
            n1_m = statistics.mean([r["n_tool_events"] for r in n1])
            p_m = statistics.mean([r["n_tool_events"] for r in p])
            p_moves = p_m > n1_m  # T1 direction: P adds a recheck -> more tools
            metric = "n_tool_events"
        else:
            # T2: P asks to summarize evidence before mutation -> more reads before first mutation
            def ev(rs):
                vals = [r["n_reads"] for r in rs]
                return statistics.mean(vals) if vals else 0
            n1_m, p_m = ev(n1), ev(p)
            p_moves = p_m > n1_m
            metric = "n_reads(before act)"
        p_reward_not_worse = (max([r.get("endpoint_reward") or 0 for r in p], default=0)
                              >= max([r.get("endpoint_reward") or 0 for r in n1], default=0))
        eligible = bool(n1_live and n1_reward_ok and p_moves and p_reward_not_worse)
        g4_cells.append(dict(cell=cell, model=model, stratum=stratum, metric=metric,
                             n1_live=n1_live, n1_mean=round(n1_m, 2), p_mean=round(p_m, 2),
                             p_moves_intended_dir=p_moves, p_reward_not_worse=p_reward_not_worse,
                             eligible=eligible))
    eligible_cells = [c for c in g4_cells if c["eligible"]]
    active_models = {c["model"] for c in g4_cells if c["n1_live"]}
    g4 = dict(n_cells=len(g4_cells), n_eligible=len(eligible_cells),
              active_models=sorted(active_models), cells=g4_cells,
              note="eligibility uses PRE-treatment N1 liveness + P sensitivity, never A/treatment outcome.")
    # G4 passes if >=1 eligible cell exists on >=1 active model (positive control works on an active model)
    g4["verdict"] = "PASS" if any(c["eligible"] and c["n1_live"] for c in g4_cells) else "FAIL"

    summary = dict(G1=g1, G2=g2, G3=g3, G4=g4,
                   overall="PROCEED_TO_18_TASK_PILOT" if all(
                       x["verdict"] == "PASS" for x in (g1, g2, g3, g4))
                   else "DO_NOT_PROCEED")
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("=== Step 2.1 GATE VERDICTS ===")
    print(f"G1 scorer (real suffixes): {g1['verdict']}  scorable={n_scorable}/{len(rows)} (>=20 & all)")
    print(f"G2 junctions: {g2['verdict']}  found={n_found} valid={n_valid} strata={sorted(strata_with_valid)}")
    print(f"G3 reproducibility: {g3['verdict']}  active_snapshots={len(active_cells)} "
          f"frac_range<=1={frac_range_le1:.0%} max_range={max_range}")
    print(f"G4 positive control: {g4['verdict']}  eligible_cells={len(eligible_cells)} "
          f"active_models={sorted(active_models)}")
    print(f"\nOVERALL: {summary['overall']}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
