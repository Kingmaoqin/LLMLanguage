#!/usr/bin/env python3
"""R7-D Step 2.3 analysis: T1 eligible-cell count + T2 failure decomposition (7 classes)."""
from __future__ import annotations

import collections
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ROWS = ROOT / "results/r7d_ipma/step2_3/metrics/rows.jsonl"
T2D = ROOT / "results/r7d_ipma/step2_3/metrics/t2_diagnostics.jsonl"
OUT = ROOT / "results/r7d_ipma/step2_3/analysis/summary.json"
PRIMARY = {"T1": "n_tool_events", "T2": "evidence_before_first_mutation"}


def main() -> int:
    rows = [json.loads(l) for l in ROWS.open()] if ROWS.exists() else []
    t2diag = [json.loads(l) for l in T2D.open() if l.strip()] if T2D.exists() else []
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # ---- T1 eligibility (same criteria as Step 2.2) ----
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[(r["cell"], r["model"], r["stratum"])][r["branch"]].append(r)
    t1_cells = []
    for (cell, model, stratum), br in by.items():
        if stratum != "T1":
            continue
        n0, n1, p = br.get("N0", []), br.get("N1", []), br.get("P", [])
        metric = PRIMARY["T1"]
        baseline = len(n1) >= 4 and sum(1 for r in n1 if r.get("endpoint_reward") == 1.0) >= 4
        expo = len(n1) >= 4 and sum(1 for r in n1 if r["n_tool_events"] >= 2) >= 4
        n0m = [r.get(metric) or 0 for r in n0]
        active = any(r["n_tool_events"] > 0 for r in n0)
        repro = active and (max(n0m) - min(n0m) if n0m else 9) <= 1 and len({r["tool_sequence"] for r in n0}) == 1
        n1_mean = statistics.mean([r.get(metric) or 0 for r in n1]) if n1 else 0
        pc = len(p) >= 3 and sum(1 for r in p if (r.get(metric) or 0) > n1_mean) >= 3 and n1_mean > 0
        elig = bool(baseline and expo and repro and pc and n0)
        t1_cells.append(dict(cell=cell, model=model, baseline=baseline, exposure=expo,
                             repro=repro, n0_range=(max(n0m) - min(n0m)) if n0m else None,
                             pc=pc, eligible=elig))
    t1_elig = [c for c in t1_cells if c["eligible"]]

    # ---- T2 failure decomposition ----
    fail_counts = collections.Counter(d["failure"] for d in t2diag)
    # per (cell,model): modal failure
    per_cm = collections.defaultdict(list)
    for d in t2diag:
        per_cm[(d["cell"], d["model"])].append(d["failure"])
    cm_modal = {f"{c}/{m}": collections.Counter(v).most_common(1)[0][0] for (c, m), v in per_cm.items()}
    # by domain / by task
    by_task = collections.defaultdict(collections.Counter)
    for d in t2diag:
        by_task[d["cell"]][d["failure"]] += 1

    active_n0 = [c for c in t1_cells if c.get("n0_range") is not None and
                 any(True for r in by[(c["cell"], c["model"], "T1")].get("N0", []) if r["n_tool_events"] > 0)]
    frac_repro = (sum(1 for c in active_n0 if (c["n0_range"] or 9) <= 1) / len(active_n0)) if active_n0 else 0.0

    summary = dict(
        t1=dict(n_cells=len(t1_cells), n_eligible=len(t1_elig),
                eligible=[c["cell"] + "/" + c["model"] for c in t1_elig],
                tasks_covered=len({c["cell"] for c in t1_elig}),
                models=sorted({c["model"] for c in t1_elig}),
                active_n0_frac_range_le1=round(frac_repro, 3), cells=t1_cells),
        t2=dict(n_runs=len(t2diag), failure_distribution=dict(fail_counts),
                cell_model_modal_failure=cm_modal, by_task={k: dict(v) for k, v in by_task.items()}),
    )
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("=== T1 ELIGIBILITY (Step 2.3 expanded) ===")
    for c in sorted(t1_cells, key=lambda x: (not x["eligible"], x["cell"])):
        print(f"  {c['cell']:14s} {c['model']:16s} base={int(c['baseline'])} expo={int(c['exposure'])} "
              f"repro={int(c['repro'])}(r={c['n0_range']}) pc={int(c['pc'])} -> {'ELIGIBLE' if c['eligible'] else 'no'}")
    print(f"\nT1 eligible = {len(t1_elig)} over {len({c['cell'] for c in t1_elig})} tasks, "
          f"models={sorted({c['model'] for c in t1_elig})}")
    print(f"\n=== T2 FAILURE DECOMPOSITION ({len(t2diag)} runs) ===")
    for k, v in fail_counts.most_common():
        print(f"  {k:36s} {v}")
    print("\n=== T2 by task (modal failure) ===")
    for cell, cnt in sorted(by_task.items()):
        print(f"  {cell:14s} {dict(cnt)}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
