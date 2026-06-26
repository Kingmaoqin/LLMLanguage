"""R6 block driver + analysis orchestrator (round-6 §7.3).

Two modes:

  --plan        : resolve and print the matrix for a config (delegates to run_r6_experiment).
  --analyze     : run the full offline analysis chain on an existing R6 result root:
                  integrity audit -> extract metrics -> statistics -> noise floor -> profile.

Execution of model runs is delegated to run_r6_experiment.py (see its execution boundary).
The analyze chain is what turns a finished run root into the R6 reports + contrast tables.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R6 = ROOT / "scripts" / "r6"

ANALYSIS_CHAIN = [
    ("integrity", R6 / "final_integrity_audit_r6.py"),
    ("extract", R6 / "extract_r6_metrics.py"),
    ("statistics", R6 / "statistical_analysis_r6.py"),
    ("noise_floor", R6 / "estimate_r6_noise_floor.py"),
    ("profile", R6 / "analyze_r6_interactional_profile.py"),
]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="configs/r6/r6_full_main.yaml")
    p.add_argument("--phase", default="full", choices=["smoke", "pilot", "full", "preflight"])
    p.add_argument("--root", default="results/r6_sensitivity/full_main")
    p.add_argument("--plan", action="store_true", help="plan the matrix only")
    p.add_argument("--analyze", action="store_true", help="run the analysis chain on --root")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--continue-on-integrity-fail", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if not (args.plan or args.analyze):
        raise SystemExit("specify --plan and/or --analyze")

    if args.plan:
        cmd = [args.python, str(R6 / "run_r6_experiment.py"), "--phase", args.phase,
               "--config", args.config, "--dry-run"]
        print("[r6-blocks] PLAN:", " ".join(cmd))
        rc = subprocess.call(cmd, cwd=str(ROOT))
        if rc != 0:
            return rc

    if args.analyze:
        for label, script in ANALYSIS_CHAIN:
            cmd = [args.python, str(script), "--root", args.root]
            print(f"[r6-blocks] {label.upper()}:", " ".join(cmd))
            rc = subprocess.call(cmd, cwd=str(ROOT))
            if rc != 0:
                if label == "integrity" and args.continue_on_integrity_fail:
                    print("[r6-blocks] integrity FAILED; continuing per flag")
                    continue
                print(f"[r6-blocks] {label} failed rc={rc}; stopping")
                return rc
        print(f"[r6-blocks] analysis chain complete for {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
