#!/usr/bin/env python3
"""Run the offline R7/IPMA script smoke suite.

This does not call any model endpoint and does not start the R7 full experiment.
It validates the R7 pre-main measurement-repair and analysis artifact pipeline
on already-completed R6 traces.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str]) -> dict[str, str | int]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return {"cmd": " ".join(cmd), "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()
    py = args.python
    commands = [
        # R6 measurement repair (PDF section 2)
        [py, "scripts/r7_ipma/reconstruct_tau2_field_diffs.py"],
        [py, "scripts/r7_ipma/extract_usage_and_timing.py"],
        [py, "scripts/r7_ipma/audit_r6_tool_trajectory_effects.py", "--max_cases_per_contrast", "8"],
        [py, "scripts/r7_ipma/export_abandonment_human_audit_sample.py"],
        # R7 template bank + contamination audit (PDF section 8)
        [py, "scripts/r7_ipma/audit_r7_templates.py"],
        [py, "scripts/r7_ipma/build_r7_template_bank.py"],
        [py, "scripts/r7_ipma/filter_template_contamination.py"],
        [py, "scripts/r7_ipma/judge_template_invariance.py"],
        [py, "scripts/r7_ipma/export_template_spotcheck.py"],
        # R7 task registry + dev/test freeze (PDF sections 9, 10)
        [py, "scripts/r7_ipma/build_r7_task_registry.py", "--smoke"],
        [py, "scripts/r7_ipma/build_r7_task_registry.py", "--full"],
        # Neutral reference / PASR pipeline smoke (PDF sections 12, 13)
        [py, "scripts/r7_ipma/build_neutral_reference_table.py"],
        [py, "scripts/r7_ipma/compute_pasr_metrics.py"],
        # Integrity (PDF section 16)
        [py, "scripts/r7_ipma/check_r7_integrity.py"],
    ]
    results = [run(cmd) for cmd in commands]
    out = ROOT / "results/r7_ipma/smoke/script_smoke_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [r for r in results if r["returncode"] != 0]
    print(json.dumps({"commands": len(results), "failed": len(failed), "log": str(out)}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

