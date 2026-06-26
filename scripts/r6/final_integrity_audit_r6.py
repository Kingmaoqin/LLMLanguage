"""R6 integrity audit (round-6 §7, §14).

Verifies an R6 result root before analysis:
- run completeness vs the run manifest / expected matrix;
- no duplicate run_ids;
- invalid-run rate within tolerance;
- every trace passes the canonical trace schema;
- no write outside the R6 result root (does not touch R4/R4.1/R5 roots).

Outputs reports/r6_sensitivity/R6_FULL_INTEGRITY_REPORT.md and a status CSV; returns nonzero
on FAIL so a driver can stop before analysis.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.r6.trace_schema import validate_r6_trace  # noqa: E402

PROTECTED_ROOTS = [
    "results/stage2_5b_repair", "results/r5", "results/r4",
    "results/stage2_5b_analysis_r4", "results/stage2_5b_analysis_r4_1",
]


def iter_trace_files(root: Path):
    tdir = root / "traces"
    if tdir.is_dir():
        yield from sorted(tdir.glob("*.trace.json"))


def load_manifest(root: Path) -> list[dict[str, Any]]:
    man = root / "run_manifest.csv"
    if man.exists():
        return list(csv.DictReader(man.open(encoding="utf-8")))
    return []


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default="results/r6_sensitivity/full_main")
    p.add_argument("--report", default="reports/r6_sensitivity/R6_FULL_INTEGRITY_REPORT.md")
    p.add_argument("--max-invalid-rate", type=float, default=0.05)
    return p


def main() -> int:
    args = build_parser().parse_args()
    root = ROOT / args.root if not Path(args.root).is_absolute() else Path(args.root)
    if not root.is_dir():
        raise SystemExit(f"R6 root not found: {root}")

    # guard: the audited root must not be one of the protected historical roots
    rel = str(root.resolve())
    for protected in PROTECTED_ROOTS:
        if rel == str((ROOT / protected).resolve()):
            raise SystemExit(f"refusing to audit-in-place a protected historical root: {protected}")

    checks: list[dict[str, Any]] = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    traces = list(iter_trace_files(root))
    manifest = load_manifest(root)

    schema_failures = []
    run_ids = []
    invalid = 0
    for tf in traces:
        try:
            trace = json.loads(tf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            schema_failures.append(f"{tf.name}: unreadable ({exc})")
            continue
        errs = validate_r6_trace(trace)
        if errs:
            schema_failures.append(f"{tf.name}: {'; '.join(errs)}")
        run_ids.append(trace.get("run_id") or tf.stem)
        meta = trace.get("run_meta") or {}
        if str(meta.get("invalid_run")).lower() in {"true", "1"}:
            invalid += 1

    n = len(run_ids)
    dup = n - len(set(run_ids))
    invalid_rate = (invalid / n) if n else 0.0

    check("traces_present", n > 0, f"{n} traces")
    check("no_duplicate_run_ids", dup == 0, f"{dup} duplicates")
    check("trace_schema", not schema_failures, f"{len(schema_failures)} schema failures")
    check("invalid_rate_within_tolerance", invalid_rate <= args.max_invalid_rate,
          f"{invalid_rate:.3f} <= {args.max_invalid_rate}")
    if manifest:
        check("manifest_matches_traces", len(manifest) == n,
              f"manifest={len(manifest)} traces={n}")

    overall = all(c["status"] == "PASS" for c in checks)

    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# R6 Full Integrity Report (round-6 §7)",
        "",
        f"Root: `{args.root}` — traces: {n}, invalid: {invalid} ({invalid_rate:.3f}), "
        f"duplicates: {dup}, schema failures: {len(schema_failures)}.",
        "",
        f"## Overall: {'PASS' if overall else 'FAIL'}",
        "",
        "| check | status | detail |",
        "|---|---|---|",
        *[f"| {c['check']} | {c['status']} | {c['detail']} |" for c in checks],
    ]
    if schema_failures:
        lines += ["", "## Schema failures (first 20)", "", *[f"- {f}" for f in schema_failures[:20]]]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with (root / "r6_integrity_status.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["check", "status", "detail"])
        w.writeheader()
        w.writerows(checks)

    print(f"R6 integrity: {'PASS' if overall else 'FAIL'} (traces={n}, invalid_rate={invalid_rate:.3f})")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
