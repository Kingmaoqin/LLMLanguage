#!/usr/bin/env python3
"""R8-B batch driver for Part A / B / C. Resumable (skip-existing). Errors -> .error.json.

Part A: 12 tasks x 3 models x {H0,H1,H2,H3} x 2 reps                     = 288
Part B: 5 modules x 3 tasks x 3 models x {N0,A0,N1,A1} x 2 reps          = 360
Part C: 4 tasks  x 3 models x {B0,B1,B2} x 2 reps                        = 72
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.r8_attack.run_attack_episode import MODEL_ENDPOINTS  # noqa: E402
from scripts.r8_attack.attacker import Objective  # noqa: E402
from scripts.r8b_attack.run_r8b_episode import run_one  # noqa: E402

FROZEN = ROOT / "data/r8b_attack/frozen"
OUT = ROOT / "results/r8b_attack"

# module -> confounder flag set present when arm has confounder "1"
MODULE_CONFOUNDER = {
    "M1": {"extra_turn": True}, "M2": {"long_msg": True}, "M3": {"fragment": True},
    "M4": {"scaffold_mode": "official"}, "M5": {"disclaimer": True},
}


def reg():
    return json.loads((FROZEN / "r8b_task_registry.json").read_text())


def _run(part, t, model, condition, rep, out_sub, *, confounders, boundary, skip_existing, skip_errored):
    obj = Objective(t["family"], t["objective"]["target_direction"], t["objective"]["metric"])
    key = f"{condition}"
    if confounders:
        key += "_" + "-".join(sorted(confounders))
    if boundary:
        key += f"_{boundary}"
    out_path = OUT / out_sub / t["domain"] / t["tau2_task_id"] / model / key / f"rep_{rep}.json"
    if skip_existing and out_path.exists():
        return "skip"
    if skip_errored and out_path.with_suffix(".error.json").exists():
        return "skip"
    seed = 2000 + rep
    try:
        run_one(t["domain"], t["tau2_task_id"], model, condition, rep, objective=obj, part=part,
                confounders=confounders, boundary=boundary, max_steps=100, seed=seed, out_path=out_path)
        return "ok"
    except Exception as exc:  # noqa: BLE001
        import traceback
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.with_suffix(".error.json").write_text(json.dumps({"error": repr(exc)[:300], "traceback": traceback.format_exc()[-1500:]}, indent=2))
        print(f"INFRA-FAIL {part}/{t['domain']}/{t['tau2_task_id']}/{model}/{condition}: {exc!r}", file=sys.stderr, flush=True)
        return "fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=["A", "B", "C"])
    ap.add_argument("--models", nargs="+", default=list(MODEL_ENDPOINTS))
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--skip-existing", action="store_true", default=True)
    ap.add_argument("--skip-errored", action="store_true")
    args = ap.parse_args()
    R = reg()
    n_ok = n_skip = n_fail = i = 0

    def tick(part, t, model, cond):
        nonlocal i
        i += 1
        if i % 10 == 0:
            print(f"  [{part} {i}] ok={n_ok} skip={n_skip} fail={n_fail} last={t['domain']}/{t['tau2_task_id']}/{model}/{cond}", flush=True)

    if args.part == "A":
        tasks = R["partA"]
        conds = ["H0", "H1", "H2", "H3"]
        total = len(tasks) * len(args.models) * len(conds) * args.reps
        print(f"[Part A] {total} episodes", flush=True)
        for t in tasks:
            for m in args.models:
                for rep in range(args.reps):
                    for c in conds:
                        r = _run("partA", t, m, c, rep, "high_intensity", confounders={}, boundary=None,
                                 skip_existing=args.skip_existing, skip_errored=args.skip_errored)
                        n_ok += r == "ok"; n_skip += r == "skip"; n_fail += r == "fail"; tick("A", t, m, c)
    elif args.part == "B":
        assign = R["partB_assign"]
        total = len(assign) * len(args.models) * 4 * args.reps
        print(f"[Part B] {total} episodes ({len(assign)} module-tasks x 4 arms)", flush=True)
        for a in assign:
            mod = a["module"]; conf = MODULE_CONFOUNDER[mod]
            arms = [("N0", "H0", {}), ("A0", "H3", {}), ("N1", "H0", conf), ("A1", "H3", conf)]
            for m in args.models:
                for rep in range(args.reps):
                    for arm, cond, cf in arms:
                        t = dict(a);
                        r = _run("partB", t, m, cond, rep, f"confounder_factorials/{mod}", confounders=cf,
                                 boundary=None, skip_existing=args.skip_existing, skip_errored=args.skip_errored)
                        n_ok += r == "ok"; n_skip += r == "skip"; n_fail += r == "fail"; tick(f"B/{mod}", t, m, f"{arm}")
    else:  # Part C
        tasks = R["partC"]
        total = len(tasks) * len(args.models) * 3 * args.reps
        print(f"[Part C] {total} episodes", flush=True)
        for idx, t in enumerate(tasks):
            # task-level frozen boundary type: alternate BC-A (delegation) / BC-D (deadline)
            btype = "delegation" if idx % 2 == 0 else "deadline"
            conds = [("B0", "H0", None), ("B1", "H3", None), ("B2", "H3", btype)]
            for m in args.models:
                for rep in range(args.reps):
                    for arm, cond, bnd in conds:
                        r = _run("partC", t, m, cond, rep, "boundary_controls", confounders={}, boundary=bnd,
                                 skip_existing=args.skip_existing, skip_errored=args.skip_errored)
                        n_ok += r == "ok"; n_skip += r == "skip"; n_fail += r == "fail"; tick("C", t, m, arm)
    print(f"[Part {args.part}] DONE ok={n_ok} skip={n_skip} fail={n_fail}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
