#!/usr/bin/env python3
"""Minimal live dev smoke for tau2 snapshot instrumentation (PDF A-option step).

Purpose: prove that the tau2 runner, with full-DB-snapshot capture enabled, now
writes initial/final snapshots that reconstruct_tau2_field_diffs.py can diff --
i.e. the R6 measurement gap (`cannot_reconstruct_missing_snapshot`) is fixed at
the source for new runs.

This is intentionally tiny: 1 tau2 task x 1 model x 1 seed x 1 condition.  It
makes REAL model calls, so it must be run in the tau2/litellm env, e.g.:

  conda run -n agentsearch python scripts/r7_ipma/run_r7_tau2_snapshot_smoke.py

It does NOT start the R7 full experiment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.r6.minimal_env import write_trace  # noqa: E402
from src.r6.trace_schema import validate_r6_trace  # noqa: E402
from scripts.r6.run_r6_live import endpoint_ok, load_models, load_tasks, run_cell_live  # noqa: E402
from scripts.r7_ipma.reconstruct_tau2_field_diffs import process as reconstruct  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma4_31b")
    ap.add_argument("--task", default="r6_retail_03_return_confirmed",
                    help="a tau2 retail/airline task (mutation task gives a visible diff)")
    ap.add_argument("--condition", default="neutral_clean")
    ap.add_argument("--seed", type=int, default=300)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max_steps", type=int, default=30)
    ap.add_argument("--out_root", type=Path, default=ROOT / "results/r7_ipma/dev_smoke")
    args = ap.parse_args()

    model = load_models([args.model])[0]
    tasks = load_tasks()
    if args.task not in tasks:
        raise SystemExit(f"unknown task {args.task}")
    task = tasks[args.task]
    if task["domain"] not in {"retail", "airline"}:
        raise SystemExit(f"task {args.task} is not a tau2 domain (got {task['domain']})")

    ok, detail = endpoint_ok(model)
    print(f"[r7-dev-smoke] endpoint {model['alias']}: {'OK' if ok else 'FAIL'} - {detail}")
    if not ok:
        raise SystemExit(f"[r7-dev-smoke] endpoint not reachable for {model['alias']}")

    trace = run_cell_live(model, task, args.condition, args.seed, args.temperature,
                          args.max_steps, capture_full_snapshots=True)
    errs = validate_r6_trace(trace)
    trace_dir = args.out_root
    path = write_trace(trace_dir, trace, overwrite=True)
    print(f"[r7-dev-smoke] wrote {path}")
    print(f"[r7-dev-smoke] snapshots_captured={trace['run_meta'].get('full_db_snapshot_captured')} "
          f"diff_source={trace['run_meta'].get('field_level_state_diff_source')} schema_errors={errs}")

    # Reconstruct field diffs on the fresh trace directory.
    seen, rec, rerun = reconstruct(trace_dir, trace_dir / "measurement_repair",
                                   trace_dir / "R7_DEV_SMOKE_FIELD_DIFF_CN.md")
    print(json.dumps({"tau2_seen": seen, "reconstructable": rec, "rerun_needed": rerun}, ensure_ascii=False))

    snap_ok = bool(trace["run_meta"].get("full_db_snapshot_captured"))
    recon_ok = rec >= 1 and rerun == 0
    verdict = "PASS" if (snap_ok and recon_ok and not errs) else "FAIL"
    print(f"[r7-dev-smoke] VERDICT={verdict} "
          f"(snapshot_captured={snap_ok}, reconstructable={recon_ok}, schema_ok={not errs})")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
