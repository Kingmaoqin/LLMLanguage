#!/usr/bin/env python3
"""R8 Full-Episode: batch driver (spec 4, 8).

A BLOCK = task x model x replicate x all 5 conditions. Blocks run from a clean
env each episode (run_one builds a fresh environment). Resumable (skips existing
.json). Fills task_type from the frozen manifest.

  --smoke : 3 tasks x 3 models x 5 conditions x 1 replicate = 45 episodes (spec 4.2).
            Smoke ONLY validates the pipeline; it must NOT be used to select tasks
            or tune thresholds (the 3 smoke tasks are a fixed deterministic pick).
  (default): all 36 tasks x 3 models x 5 conditions x 5 replicates = 2700 episodes.

Model endpoints must be live. Episodes that infra-fail write a .error.json; rerun
the driver to retry only those (block-level rerun policy lives here, not in run_one).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.r8_full_episode.run_full_episode import run_one, MODEL_ENDPOINTS  # noqa: E402

FROZEN = ROOT / "data/r8_full_episode/frozen"
CONDITIONS = ["C0", "C1", "C2", "C3", "C4"]


def load_tasks():
    return [json.loads(l) for l in (FROZEN / "task_manifest.jsonl").read_text().splitlines() if l.strip()]


def smoke_tasks(tasks):
    """Fixed deterministic 3-task pick spanning domains/types (NOT performance-based)."""
    by = {}
    for t in tasks:
        by.setdefault((t["domain"], t["task_type"]), t)
    picks = []
    for key in [("retail", "read"), ("retail", "single"), ("airline", "compound")]:
        if key in by:
            picks.append(by[key])
    return picks[:3]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--models", nargs="+", default=list(MODEL_ENDPOINTS))
    ap.add_argument("--replicates", type=int, default=None)
    ap.add_argument("--max-steps", type=int, default=100)
    ap.add_argument("--out-root", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/traces")
    ap.add_argument("--skip-errored", action="store_true",
                    help="also skip cells that already have a .error.json (do NOT retry "
                         "known failures) -> fills only the truly-missing cells")
    args = ap.parse_args()

    tasks = load_tasks()
    if args.smoke:
        tasks = smoke_tasks(tasks)
        reps = 1
    else:
        reps = args.replicates or 5

    total = len(tasks) * len(args.models) * len(CONDITIONS) * reps
    print(f"batch: {len(tasks)} tasks x {len(args.models)} models x {len(CONDITIONS)} cond "
          f"x {reps} rep = {total} episodes  (smoke={args.smoke})", flush=True)

    n_ok = n_skip = n_fail = 0
    i = 0
    for t in tasks:
        for model in args.models:
            for rep in range(reps):
                for cond in CONDITIONS:  # a block = the 5 conditions of this task/model/rep
                    i += 1
                    seed = 1000 + rep
                    out_path = (args.out_root / t["domain"] / t["tau2_task_id"] / model /
                                cond / f"rep_{rep}.json")
                    if out_path.exists():
                        n_skip += 1
                        continue
                    if args.skip_errored and out_path.with_suffix(".error.json").exists():
                        n_skip += 1
                        continue
                    try:
                        rec = run_one(t["domain"], t["tau2_task_id"], model, cond, rep,
                                      max_steps=args.max_steps, seed=seed, out_path=out_path,
                                      task_type=t["task_type"])
                        n_ok += 1
                        print(f"[{i}/{total}] OK {rec['run_id']} reward={rec['official_reward']} "
                              f"term={rec['termination_reason']} tools={len(rec['agent_tool_calls'])}",
                              flush=True)
                    except Exception as exc:  # noqa: BLE001 - record infra fail, continue
                        n_fail += 1
                        import traceback
                        (out_path.parent).mkdir(parents=True, exist_ok=True)
                        out_path.with_suffix(".error.json").write_text(json.dumps(
                            {"error": repr(exc)[:300], "traceback": traceback.format_exc()[-1500:]},
                            indent=2))
                        print(f"[{i}/{total}] INFRA-FAIL {t['domain']}/{t['tau2_task_id']}/{model}"
                              f"/{cond}/rep{rep}: {exc!r}", flush=True)
    print(f"DONE ok={n_ok} skip={n_skip} infra_fail={n_fail} total={total}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
