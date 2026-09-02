#!/usr/bin/env python3
"""Verify that an R7-C smoke run completed before allowing full rerun."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import read_csv, write_md


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-root", type=Path, required=True)
    ap.add_argument("--expected-traces", type=int, default=144)
    ap.add_argument("--expected-pairs", type=int, default=120)
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7c_ipma/R7C_SMOKE_GATE_VERIFY_CN.md")
    args = ap.parse_args()

    root = args.smoke_root if args.smoke_root.is_absolute() else ROOT / args.smoke_root
    failures: list[str] = []

    summary_path = root / "r7c_live_summary.json"
    endpoint_path = root / "r7c_endpoint_preflight.json"
    pair_path = root / "metrics/r7b_pairs.csv"
    success_path = root / "metrics/pasr_success_explanations.csv"
    analysis_path = root / "analysis/primary_pasr_contrasts.csv"

    summary = load_json(summary_path) if summary_path.exists() else {}
    endpoint = load_json(endpoint_path) if endpoint_path.exists() else []
    traces = list((root / "traces").glob("*.trace.json")) if (root / "traces").exists() else []
    pairs = read_csv(pair_path) if pair_path.exists() else []
    successes = read_csv(success_path) if success_path.exists() else []

    if not summary_path.exists():
        failures.append("missing_r7c_live_summary")
    else:
        if int(summary.get("planned", -1)) != args.expected_traces:
            failures.append(f"summary_planned={summary.get('planned')} != {args.expected_traces}")
        if int(summary.get("written", -1)) != args.expected_traces:
            failures.append(f"summary_written={summary.get('written')} != {args.expected_traces}")
        if int(summary.get("failed", -1)) != 0:
            failures.append(f"summary_failed={summary.get('failed')} != 0")
    if not endpoint_path.exists():
        failures.append("missing_endpoint_preflight")
    elif any(row.get("ok") is not True for row in endpoint):
        bad = [row.get("model") for row in endpoint if row.get("ok") is not True]
        failures.append(f"endpoint_not_ok={bad}")
    if len(traces) != args.expected_traces:
        failures.append(f"trace_count={len(traces)} != {args.expected_traces}")
    if len(pairs) != args.expected_pairs:
        failures.append(f"pair_count={len(pairs)} != {args.expected_pairs}")
    if not success_path.exists():
        failures.append("missing_pasr_success_explanations")
    if not analysis_path.exists():
        failures.append("missing_primary_pasr_contrasts")

    result = {
        "gate_pass": not failures,
        "failures": failures,
        "smoke_root": str(root),
        "summary": summary,
        "endpoint": endpoint,
        "trace_count": len(traces),
        "pair_count": len(pairs),
        "pasr_success": len(successes),
    }
    write_md(
        args.report,
        f"""# R7-C smoke gate verification

- gate_pass: {result['gate_pass']}
- smoke_root: `{root}`
- failures: {failures or '[]'}
- trace_count: {len(traces)}/{args.expected_traces}
- pair_count: {len(pairs)}/{args.expected_pairs}
- pasr_success: {len(successes)}
- endpoint_preflight: `{endpoint_path}`
- summary: `{summary_path}`

结论：{"允许进入 full 前人工 review。" if result['gate_pass'] else "不得进入 full；smoke 未通过或证据不完整。"}
""",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
