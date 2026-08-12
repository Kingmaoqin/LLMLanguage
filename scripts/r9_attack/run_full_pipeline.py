#!/usr/bin/env python3
"""R9 full-pipeline orchestrator (spec 22). Resumable, single entry point.

Runs the fixed stages in order and STOPS on the spec's stop conditions:
  safety_audit(0.2) -> build_splits(5) -> freeze canonical(7) -> calibration(6) ->
  [STOP if <2 models] -> dev(8) -> freeze_attacker(8.6/13) -> confirmatory(9) ->
  check_integrity(18) -> analyze(12/14/19) -> confounder(16) -> dual_review(15).

Confirmatory + confounder C4 use the FROZEN attacker (frozen priors + deterministic
program guard, NO live per-turn reviewer calls): spec 8.6/§2 forbid online candidate
search at test time, and the tactic library is pre-vetted during dev. The live dual
reviewers are used for dev candidate development (spec 8.5) and the POST-run trajectory
review (spec 15.2), not the confirmatory rollout.

Scale is configurable; defaults are the spec budgets. Every stage is resumable via the
ResultsSink episode-id dedup, so an OOM/kill mid-run is recovered by re-invoking.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.common import paths  # noqa: E402
from scripts.r9_attack.common.io_utils import read_json  # noqa: E402

PY = sys.executable


def sh(cmd: list[str], *, allow_fail: bool = False) -> int:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    rc = subprocess.call(cmd, cwd=str(ROOT))
    print(f"  -> rc={rc} ({time.time()-t0:.0f}s)", flush=True)
    if rc != 0 and not allow_fail:
        print(f"STAGE FAILED (rc={rc}); stopping pipeline.", flush=True)
        sys.exit(rc)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="R9 full pipeline (spec 22)")
    ap.add_argument("--candidates", nargs="+", default=["mistral_small_3p2", "gemma4_31b", "gpt_oss_120b"])
    ap.add_argument("--cal-repeats", type=int, default=2)
    ap.add_argument("--cal-limit", type=int, default=0, help="limit calibration tasks per benchmark (0=spec)")
    ap.add_argument("--dev-repeats", type=int, default=3)
    ap.add_argument("--dev-limit-tasks", type=int, default=0)
    ap.add_argument("--conf-repeats", type=int, default=5)
    ap.add_argument("--conf-limit-tasks", type=int, default=0)
    ap.add_argument("--confounder-repeats", type=int, default=3)
    ap.add_argument("--bfcl-scan", type=int, default=80, help="BFCL tasks to scan for splits")
    ap.add_argument("--skip-to", default="", help="skip stages before this one")
    ap.add_argument("--stop-after", default="", help="stop after this stage")
    args = ap.parse_args()

    stages = ["safety", "splits", "canonical", "calibration", "dev", "freeze",
              "prerun_review", "confirmatory", "integrity", "analyze", "confounder", "review"]
    start = stages.index(args.skip_to) if args.skip_to in stages else 0

    def active(name: str) -> bool:
        i = stages.index(name)
        if i < start:
            return False
        if args.stop_after and i > stages.index(args.stop_after):
            return False
        return True

    paths.ensure_dirs()

    if active("safety"):
        sh([PY, "scripts/r9_attack/safety_audit.py"])

    if active("splits"):
        sh([PY, "scripts/r9_attack/build_splits.py", "--bfcl-limit", str(args.bfcl_scan)])

    if active("canonical"):
        sh([PY, "scripts/r9_attack/canonical_message_cache.py", "--freeze"], allow_fail=True)

    if active("calibration"):
        cmd = [PY, "scripts/r9_attack/run_calibration.py", "--models", *args.candidates,
               "--repeats", str(args.cal_repeats)]
        if args.cal_limit:
            cmd += ["--limit-tasks", str(args.cal_limit)]
        sh(cmd, allow_fail=True)
        decision = read_json(paths.SELECTED_MODELS)
        if not decision["status"].startswith("SELECTED"):
            print(f"\n[pipeline] {decision['status']} — cannot proceed to main experiment (spec 6.5).", flush=True)
            print(f"[pipeline] per-model: {json.dumps(decision['per_model'], indent=1)}", flush=True)
            return 3
        if decision["status"] != "SELECTED":
            print(f"\n[pipeline] proceeding in REDUCED regime: {decision['status']}", flush=True)
        print(f"[pipeline] targets_bfcl={decision.get('targets_bfcl')} "
              f"targets_toolsandbox={decision.get('targets_toolsandbox')}", flush=True)
        targets = decision["selected_models"]
    else:
        targets = read_json(paths.SELECTED_MODELS).get("selected_models", args.candidates[:2]) \
            if paths.SELECTED_MODELS.exists() else args.candidates[:2]
    print(f"[pipeline] target models: {targets}", flush=True)

    if active("dev"):
        # Program-guard candidate vetting during dev (fast); the dedicated pre-run dual
        # review (spec 15.1) audits the frozen tactic library + candidates separately.
        cmd = [PY, "scripts/r9_attack/run_dev.py", "--models", *targets,
               "--repeats", str(args.dev_repeats), "--no-live-attacker"]
        if args.dev_limit_tasks:
            cmd += ["--limit-tasks", str(args.dev_limit_tasks)]
        sh(cmd)

    if active("freeze"):
        sh([PY, "scripts/r9_attack/freeze_attacker.py"])

    if active("prerun_review"):
        # spec 15.1: vet the frozen tactic library + candidates BEFORE confirmatory, so the
        # confirmatory rollout can apply the frozen policy deterministically (no live review).
        sh([PY, "scripts/r9_attack/run_dual_review.py", "--mode", "pre-run"], allow_fail=True)

    if active("confirmatory"):
        # Frozen fast path: frozen priors + program guard, no live per-turn reviewers.
        cmd = [PY, "scripts/r9_attack/run_confirmatory.py", "--stage", "confirmatory",
               "--models", *targets, "--repeats", str(args.conf_repeats), "--no-live-attacker"]
        if args.conf_limit_tasks:
            cmd += ["--limit-tasks", str(args.conf_limit_tasks)]
        sh(cmd)

    if active("integrity"):
        sh([PY, "scripts/r9_attack/check_integrity.py",
            "--stage-file", str(paths.CONFIRMATORY / "confirmatory_episodes.jsonl")], allow_fail=True)

    if active("analyze"):
        sh([PY, "scripts/r9_attack/analyze_confirmatory.py"])

    if active("confounder"):
        sh([PY, "scripts/r9_attack/run_confounder_module.py", "--models", *targets,
            "--repeats", str(args.confounder_repeats), "--no-live-attacker"], allow_fail=True)

    if active("review"):
        sh([PY, "scripts/r9_attack/run_dual_review.py", "--target", "300"], allow_fail=True)

    if active("review"):
        sh([PY, "scripts/r9_attack/generate_reports.py"], allow_fail=True)

    print("\n[pipeline] COMPLETE.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
