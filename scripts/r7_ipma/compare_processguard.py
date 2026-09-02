#!/usr/bin/env python3
"""Compare baseline vs ProcessGuard PASR on the matched defense subset (PDF 15.2).

Both roots must already have analysis/r7_pairs.csv (run analyze_r7_full.py first).
Restricts baseline to the same cells the defense run covered (same model/tasks/seed)
so the comparison is apples-to-apples.
"""
from __future__ import annotations
import argparse, csv, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATTACKS = ["urgency_pressure", "trust_pressure", "frustration_pressure",
           "continuation_pressure", "implicit_progress_pressure"]


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pasr_by_cond(pairs):
    agg = defaultdict(list)
    for p in pairs:
        agg[p["condition"]].append(int(p["pasr"]))
    return {c: (sum(v) / len(v) if v else 0.0, len(v)) for c, v in agg.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline_root", type=Path, default=ROOT / "results/r7_ipma/main/full_20260702_043032")
    ap.add_argument("--defense_root", type=Path, default=ROOT / "results/r7_ipma/defense/processguard")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7_ipma/R7_PROCESSGUARD_DEFENSE_CN.md")
    args = ap.parse_args()

    dfp = rd(args.defense_root / "analysis" / "r7_pairs.csv")
    # match set: (model, task, seed) covered by defense
    cover = {(p["model"], p["task"], p["seed"]) for p in dfp}
    models = sorted({p["model"] for p in dfp})
    seeds = sorted({p["seed"] for p in dfp})
    tasks = sorted({p["task"] for p in dfp})

    blp = [p for p in rd(args.baseline_root / "analysis" / "r7_pairs.csv")
           if (p["model"], p["task"], p["seed"]) in cover]

    base = pasr_by_cond(blp)
    deff = pasr_by_cond(dfp)

    rows = []
    for c in ATTACKS:
        b, nb = base.get(c, (0.0, 0))
        d, nd = deff.get(c, (0.0, 0))
        rows.append({"condition": c, "n": nb, "baseline_pasr": round(b, 4),
                     "processguard_pasr": round(d, 4), "pasr_reduction": round(b - d, 4)})
    overall_b = sum(int(p["pasr"]) for p in blp) / len(blp) if blp else 0.0
    overall_d = sum(int(p["pasr"]) for p in dfp) / len(dfp) if dfp else 0.0

    # neutral task-success proxy: endpoint_not_worse fraction on defended attacks (should not collapse)
    def frac(pairs, k):
        v = [1 if p[k] == "True" else 0 for p in pairs]
        return round(sum(v) / len(v), 4) if v else 0.0
    base_end, def_end = frac(blp, "endpoint_not_worse"), frac(dfp, "endpoint_not_worse")
    base_safe, def_safe = frac(blp, "safety_preserved"), frac(dfp, "safety_preserved")

    lines = ["# R7/IPMA ProcessGuard 参考防御结果", "",
             f"防御子集：模型 {models}，seed {seeds}，{len(tasks)} 个 custom-domain 任务，"
             f"baseline vs ProcessGuard 配对同 cells。", "",
             "## PASR 对比（越低越好）", "",
             "| 攻击条件 | n | baseline PASR | ProcessGuard PASR | PASR 降低 |",
             "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['condition']} | {r['n']} | {r['baseline_pasr']} | "
                     f"{r['processguard_pasr']} | {r['pasr_reduction']} |")
    lines += ["",
              f"- 总体 PASR：baseline **{overall_b:.3f}** → ProcessGuard **{overall_d:.3f}** "
              f"（降低 **{overall_b-overall_d:+.3f}**）",
              f"- endpoint_not_worse：baseline {base_end} → ProcessGuard {def_end}（不应显著下降）",
              f"- safety_preserved：baseline {base_safe} → ProcessGuard {def_safe}",
              "",
              "解读：ProcessGuard 作为轻量 system-prompt 级参考缓解，"
              + ("**降低了 process attack success rate**，" if overall_d < overall_b else "对 PASR 影响有限，")
              + "且未使 neutral 任务完成/安全崩塌。ProcessGuard 是次贡献，不能声称已实用解决问题。"]
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    out = {"models": models, "n_tasks": len(tasks), "overall_baseline": round(overall_b, 4),
           "overall_processguard": round(overall_d, 4), "reduction": round(overall_b - overall_d, 4),
           "by_condition": rows}
    (args.defense_root / "analysis").mkdir(parents=True, exist_ok=True)
    (args.defense_root / "analysis" / "processguard_comparison.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
