#!/usr/bin/env python3
"""R8-A batch driver (spec 2, 8): dev optimization and held-out test.

DEV  (spec 2.1, 8): 12 tasks x 3 models x 4 attacker policies (P0..P3) x 3 replicates
                    = 432 episodes. All dev episodes run condition C4 with the policy
                    under test (P0..P3); the neutral C1 baseline for the dev joint
                    objective is drawn from the shared controller in each episode's
                    per-turn records. Dev is used ONLY to pick + FREEZE the policy.
TEST (spec 2.2): 24 tasks x 3 models x 5 conditions (C0..C4) x 5 replicates = 1800.
                 C4 uses the FROZEN policy from dev. No policy search on test.

A BLOCK = task x model x replicate x {all conditions}. Fresh env per episode. Resumable
(skips existing .json). Infra failures write .error.json; rerun to retry only those.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.r8_attack.run_attack_episode import run_one, MODEL_ENDPOINTS  # noqa: E402
from scripts.r8_attack.attacker import Objective  # noqa: E402

FROZEN = ROOT / "data/r8_attack/frozen"
DEV_POLICIES = ["P0", "P1", "P2", "P3"]
TEST_CONDITIONS = ["C0", "C1", "C2", "C3", "C4"]


def load_registry():
    return [json.loads(l) for l in (FROZEN / "task_registry.jsonl").read_text().splitlines() if l.strip()]


def frozen_policy() -> str:
    p = FROZEN / "frozen_policy.json"
    if p.exists():
        return json.loads(p.read_text())["policy"]
    return "P3"


def run_cell(t, model, condition, replicate, out_root, *, policy, skip_existing, skip_errored):
    obj = Objective(family=t["family"], target_direction=t["objective"]["target_direction"],
                    metric=t["objective"]["metric"])
    tag = policy if condition == "C4" else condition
    out_path = (out_root / t["split"] / t["domain"] / t["tau2_task_id"] / model /
                f"{condition}_{tag}" / f"rep_{replicate}.json")
    if skip_existing and out_path.exists():
        return "skip"
    if skip_errored and out_path.with_suffix(".error.json").exists():
        return "skip"
    seed = 1000 + replicate
    try:
        run_one(t["domain"], t["tau2_task_id"], model, condition, replicate, objective=obj,
                policy=policy, max_steps=100, seed=seed, out_path=out_path,
                family=t["family"], split=t["split"])
        return "ok"
    except Exception as exc:  # noqa: BLE001
        import traceback
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.with_suffix(".error.json").write_text(
            json.dumps({"error": repr(exc)[:300], "traceback": traceback.format_exc()[-1500:]}, indent=2))
        print(f"INFRA-FAIL {t['domain']}/{t['tau2_task_id']}/{model}/{condition}: {exc!r}", file=sys.stderr, flush=True)
        return "fail"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["dev", "test", "smoke"])
    ap.add_argument("--models", nargs="+", default=list(MODEL_ENDPOINTS))
    ap.add_argument("--tasks", nargs="+", default=None, help="restrict to these tau2 task ids")
    ap.add_argument("--replicates", type=int, default=None)
    ap.add_argument("--out-root", type=pathlib.Path, default=ROOT / "results/r8_attack/traces")
    ap.add_argument("--skip-existing", action="store_true", default=True)
    ap.add_argument("--skip-errored", action="store_true")
    args = ap.parse_args()

    reg = load_registry()
    if args.phase == "smoke":
        # 1 task per family, 1 model, all conditions, 1 rep (pipeline validation only).
        picks, seen = [], set()
        for t in reg:
            if t["split"] == "dev" and t["family"] not in seen:
                picks.append(t); seen.add(t["family"])
        reg = picks
        models = args.models[:1]
        combos = [(c, frozen_policy() if c == "C4" else None) for c in TEST_CONDITIONS]
        reps = 1
    elif args.phase == "dev":
        reg = [t for t in reg if t["split"] == "dev"]
        models = args.models
        combos = [("C4", p) for p in DEV_POLICIES]  # policy search on C4
        reps = args.replicates or 3
    else:  # test
        reg = [t for t in reg if t["split"] == "test"]
        models = args.models
        fp = frozen_policy()
        combos = [(c, fp if c == "C4" else None) for c in TEST_CONDITIONS]
        reps = args.replicates or 5

    if args.tasks:
        reg = [t for t in reg if t["tau2_task_id"] in set(args.tasks)]

    total = len(reg) * len(models) * len(combos) * reps
    print(f"[{args.phase}] {len(reg)} tasks x {len(models)} models x {len(combos)} cond/policy "
          f"x {reps} rep = {total} episodes", flush=True)

    n_ok = n_skip = n_fail = i = 0
    for t in reg:
        for model in models:
            for rep in range(reps):
                for condition, policy in combos:
                    i += 1
                    pol = policy or "P3"
                    r = run_cell(t, model, condition, rep, args.out_root, policy=pol,
                                 skip_existing=args.skip_existing, skip_errored=args.skip_errored)
                    n_ok += r == "ok"; n_skip += r == "skip"; n_fail += r == "fail"
                    if i % 10 == 0 or r == "fail":
                        print(f"  [{i}/{total}] ok={n_ok} skip={n_skip} fail={n_fail} "
                              f"last={t['domain']}/{t['tau2_task_id']}/{model}/{condition}/{pol}", flush=True)
    print(f"[{args.phase}] DONE ok={n_ok} skip={n_skip} fail={n_fail} total={total}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
