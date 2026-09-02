"""Measurement-complete experiment runner (round-5 §9).

Thin, non-duplicating wrapper around the frozen Stage-2.5b experiment runner. It runs the
requested phase with the token bug fixed at source, into a fresh versioned output root
(never overwriting prior results), then auto-emits canonical traces and the per-run
interactional-metric profile.

    python scripts/stage2_5b/run_measurement_complete_experiment.py --phase smoke
    python scripts/stage2_5b/run_measurement_complete_experiment.py --phase pilot
    python scripts/stage2_5b/run_measurement_complete_experiment.py --phase full

Smoke/pilot/full differ only in the seed/task matrix (see measurement_complete_rerun.yaml).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/stage2_5b/run_stage2_5b_experiment.py"
RECON = ROOT / "scripts/stage2_5b/reconstruct_traces_from_existing_artifacts.py"
EXTRACT = ROOT / "scripts/stage2_5b/extract_interactional_metrics.py"
REPORT_DIR = ROOT / "reports/measurement_repair"


def reconstruction_report_for(output_root: Path) -> Path:
    """Per-rerun audit path; never overwrite the canonical R4.1 reconstruction audit."""
    return REPORT_DIR / f"RECONSTRUCTION_AUDIT_{output_root.name}.md"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["smoke", "pilot", "full"], required=True)
    p.add_argument("--models", nargs="*", default=["gemma4_31b", "gpt_oss_120b"])
    p.add_argument("--output-root", default=None,
                   help="defaults to results/stage2_5b_repair/measurement_complete_<phase>_<UTCstamp>")
    p.add_argument("--tag", default=None, help="optional fixed tag instead of a timestamp")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--extra", nargs=argparse.REMAINDER, default=[],
                   help="extra args passed through to run_stage2_5b_experiment.py")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.output_root:
        out = Path(args.output_root)
    else:
        tag = args.tag or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = ROOT / f"results/stage2_5b_repair/measurement_complete_{args.phase}_{tag}"
    out_abs = out if out.is_absolute() else ROOT / out
    if out_abs.exists() and any(out_abs.iterdir()):
        # resume is allowed (immutable manifests guard it); a brand-new run wants a clean root
        print(f"[measurement-complete] reusing existing output root {out_abs}")

    run_cmd = [args.python, str(RUNNER), "--phase", args.phase,
               "--models", *args.models, "--output-dir", str(out_abs), *args.extra]
    print("[measurement-complete] RUN:", " ".join(run_cmd))
    rc = subprocess.call(run_cmd, cwd=str(ROOT))
    if rc != 0:
        print(f"[measurement-complete] experiment runner failed rc={rc}")
        return rc

    reconstruction_report = reconstruction_report_for(out_abs)
    post_steps = (
        ("reconstruct", RECON, ["--report", str(reconstruction_report)]),
        ("extract", EXTRACT, []),
    )
    for label, script, extra in post_steps:
        cmd = [args.python, str(script), "--root", str(out_abs), *extra]
        print(f"[measurement-complete] {label.upper()}:", " ".join(cmd))
        rc = subprocess.call(cmd, cwd=str(ROOT))
        if rc != 0:
            print(f"[measurement-complete] {label} failed rc={rc}")
            return rc

    print(f"[measurement-complete] DONE phase={args.phase} root={out_abs}")
    print("[measurement-complete] traces: <root>/traces/  metrics: <root>/interactional_metrics/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
