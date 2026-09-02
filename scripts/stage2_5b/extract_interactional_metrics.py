"""Extract the per-run interactional-robustness metric profile (round-5 §4).

Reads the stored run bundles (the trace source of truth), applies the bug-fixed token
recompute, and writes:

    <root>/interactional_metrics/per_run_metrics.csv
    <root>/interactional_metrics/per_run_metrics.jsonl

One row per run, grouped across endpoint / tool / trajectory / policy / efficiency /
conversation dimensions. Uncomputable values are emitted empty (missing), never 0.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.stage2_5b.metrics.trace_metrics import build_trace, interactional_metrics  # noqa: E402


def iter_bundle_dirs(results_root: Path):
    """Yield bundle directories for block-structured and flat result roots."""
    direct = results_root / "run_bundles"
    if direct.is_dir():
        yield direct
    for block in sorted(p for p in results_root.iterdir() if p.is_dir()):
        if block.name in {"run_bundles", "traces", "interactional_metrics"}:
            continue
        bundle_dir = block / "run_bundles"
        if bundle_dir.is_dir():
            yield bundle_dir


def iter_bundles(results_root: Path):
    for bundle_dir in iter_bundle_dirs(results_root):
        for path in sorted(bundle_dir.glob("*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="results/stage2_5b_repair/r4_1_confirmatory_canonical")
    return p


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    return value


def main() -> int:
    args = build_parser().parse_args()
    results_root = ROOT / args.root
    out_dir = results_root / "interactional_metrics"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for bundle in iter_bundles(results_root):
        trace = build_trace(bundle)
        rows.append(interactional_metrics(trace, bundle.get("metrics") or {}))
    if not rows:
        raise SystemExit(f"no run bundles found under {results_root}")

    fieldnames = list(rows[0].keys())
    with (out_dir / "per_run_metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: _cell(r.get(k)) for k in fieldnames})
    with (out_dir / "per_run_metrics.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")

    n_missing_tokens = sum(1 for r in rows if r.get("token_source") == "missing")
    print(json.dumps({
        "runs": len(rows),
        "csv": str((out_dir / "per_run_metrics.csv").relative_to(ROOT)),
        "runs_with_missing_tokens": n_missing_tokens,
        "token_sources": {s: sum(1 for r in rows if r.get("token_source") == s)
                          for s in {r.get("token_source") for r in rows}},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
