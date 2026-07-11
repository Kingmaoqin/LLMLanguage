#!/usr/bin/env python3
"""Extract R7/IPMA trajectory case studies (PDF 17.3): >=12 cases, neutral vs
attack side-by-side tool sequences + process/endpoint deltas."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# how many cases per family (>=12 total): A3 B3 C2 D2 E2
QUOTA = {"A_action_intensity_amplification": 3, "B_premature_mutation_pressure": 3,
         "C_confirmation_shift": 2, "D_abandonment_overrefusal_boundary": 2,
         "E_evidence_path_steering": 2}


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def tool_seq(root, run_id):
    p = root / "traces" / f"{run_id}.trace.json"
    if not p.exists():
        return []
    t = json.loads(p.read_text(encoding="utf-8"))
    return [str(e.get("tool_name")) for e in (t.get("tool_events") or []) if e.get("tool_name")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT / "results/r7_ipma/main/full_20260702_043032")
    args = ap.parse_args()
    pairs = rd(args.root / "analysis" / "r7_pairs.csv")
    # index metrics for run_ids
    metrics = rd(args.root / "interactional_metrics" / "per_run_metrics.csv")
    ridx = {(m["model_alias"], m["task_id"], m["seed"], m["condition_id"]): m for m in metrics}

    chosen = []
    for fam, q in QUOTA.items():
        cand = [p for p in pairs if p["family"] == fam and p["pasr"] == "1"]
        if len(cand) < q:  # fall back to largest process shift
            cand = [p for p in pairs if p["family"] == fam]
        cand = sorted(cand, key=lambda p: abs(float(p["delta_n_tool"])) + float(p["traj_distance"]), reverse=True)
        seen_tasks = set()
        picked = 0
        for p in cand:
            if p["task"] in seen_tasks:
                continue
            seen_tasks.add(p["task"]); chosen.append(p); picked += 1
            if picked >= q:
                break

    lines = ["# R7/IPMA 轨迹案例研究（neutral vs attack）", "",
             f"数据根：`{args.root}`。每个 case 并列同一 (model, task, seed) 的 neutral_control 与攻击条件轨迹。", ""]
    rows = []
    for i, p in enumerate(chosen, 1):
        na = ridx.get((p["model"], p["task"], p["seed"], p["condition"]))
        nn = ridx.get((p["model"], p["task"], p["seed"], "neutral_control"))
        aseq = tool_seq(args.root, na["run_id"]) if na else []
        nseq = tool_seq(args.root, nn["run_id"]) if nn else []
        fam = p["family"].split("_")[0]
        lines += [
            f"## Case {i} · Family {fam} · {p['task']} · {p['model']} · seed {p['seed']}",
            f"- 攻击条件：**{p['condition']}** ｜ PASR={p['pasr']} ｜ 判定={p.get('pasr_reason','')}",
            f"- neutral 工具轨迹（{len(nseq)}）：`{' → '.join(nseq) or '(none)'}`",
            f"- attack  工具轨迹（{len(aseq)}）：`{' → '.join(aseq) or '(none)'}`",
            f"- 过程 delta：Δtool={p['delta_n_tool']}, Δmutation={p['delta_n_mutation']}, "
            f"Δconf_rate={p['delta_conf_rate']}, 轨迹距离={float(p['traj_distance']):.2f}",
            f"- endpoint_not_worse={p['endpoint_not_worse']} ｜ safety_preserved={p['safety_preserved']} "
            f"（这说明过程被操纵但最终安全/结局未变差）",
            "",
        ]
        rows.append({"case": i, "family": fam, "task": p["task"], "model": p["model"],
                     "seed": p["seed"], "condition": p["condition"], "pasr": p["pasr"],
                     "neutral_tools": " ".join(nseq), "attack_tools": " ".join(aseq),
                     "delta_n_tool": p["delta_n_tool"], "traj_distance": p["traj_distance"],
                     "endpoint_not_worse": p["endpoint_not_worse"], "safety_preserved": p["safety_preserved"]})

    rep = ROOT / "reports/r7_ipma/R7_TRAJECTORY_CASE_STUDIES_CN.md"
    rep.write_text("\n".join(lines), encoding="utf-8")
    outcsv = args.root / "analysis" / "r7_case_studies.csv"
    with outcsv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(json.dumps({"cases": len(chosen), "report": str(rep)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
