#!/usr/bin/env python3
"""Inject R8-B Part A/B/C results + decision into the R8-B report."""
from __future__ import annotations
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
R = ROOT / "results/r8b_attack"
REP = ROOT / "reports/r8b_attack/R8B_HIGH_INTENSITY_CONFOUNDER_PILOT_CN.md"


def fmt(x, n=3):
    return "n/a" if x is None else (f"{x:.{n}f}" if isinstance(x, (int, float)) else str(x))


def main():
    an = json.loads((R / "analysis.json").read_text()) if (R / "analysis.json").exists() else None
    if an is None:
        print("no analysis.json", file=sys.stderr); return 1
    a, ah = an["part_a"], an["part_a_holm"]
    b, bh = an["part_b"], an["part_b_holm"]
    c = an["part_c"]

    L = ["\n### Part A 结果（pure-expression high intensity）\n",
         "| family | 对比 | mean | 95% CI | perm p | Holm p | n |", "|---|---|---|---|---|---|---|"]
    for fam in ("F1", "F2"):
        for name in ("H2-H0", "H3-H0", "H3-H1"):
            e = a.get(f"{fam}:{name}")
            if e:
                L.append(f"| {fam} | {name} | {fmt(e['mean'])} | [{fmt(e['ci95'][0])}, {fmt(e['ci95'][1])}] | "
                         f"{fmt(e.get('p'))} | {fmt(ah.get(f'{fam}:{name}'))} | {e['n']} |")
    L.append("\nendpoint 1→1 (H3 vs H0)：")
    for fam in ("F1", "F2"):
        t = a.get(f"{fam}:endpoint_H3_vs_H0")
        if t:
            L.append(f"- {fam}: 1→1={t.get('1->1')} 1→0={t.get('1->0')} 0→1={t.get('0->1')} 0→0={t.get('0->0')} (n={t.get('n')})")

    L += ["\n### Part B 结果（confounder interaction =(A1−N1)−(A0−N0)）\n",
          "| module | confounder | interaction | 95% CI | perm p | Holm p | n |", "|---|---|---|---|---|---|---|"]
    names = {"M1": "extra turn", "M2": "long msg", "M3": "fragment", "M4": "scaffold", "M5": "disclaimer"}
    for m in ("M1", "M2", "M3", "M4", "M5"):
        v = b.get(m)
        if v:
            L.append(f"| {m} | {names[m]} | {fmt(v['interaction_mean'])} | "
                     f"[{fmt(v['interaction_ci95'][0])}, {fmt(v['interaction_ci95'][1])}] | "
                     f"{fmt(v.get('p'))} | {fmt(bh.get(m))} | {v['n']} |")

    L += ["\n### Part C 结果（boundary positive controls）\n",
          "| 对比 | process Δ | 95% CI | success Δ | 95% CI | n |", "|---|---|---|---|---|---|"]
    for name in ("B1-B0", "B2-B0", "B2-B1"):
        v = c.get(name)
        if v:
            L.append(f"| {name} | {fmt(v['process_mean'])} | [{fmt(v['process_ci95'][0])}, {fmt(v['process_ci95'][1])}] | "
                     f"{fmt(v['success_delta'])} | [{fmt(v['success_ci95'][0])}, {fmt(v['success_ci95'][1])}] | {v['n']} |")

    L.append("\n### 最终判定\n")
    for d in an["decision"]:
        L.append(f"- {d}")
    block = "\n".join(L) + "\n"

    text = REP.read_text()
    marker = "## 7. 决策"
    idx = text.find(marker)
    text = text[:idx] + "## 6b. 运行结果\n" + block + "\n---\n\n" + text[idx:]
    REP.write_text(text)
    print(f"finalized {REP}")


if __name__ == "__main__":
    raise SystemExit(main())
