#!/usr/bin/env python3
"""Check R7-B attack-neutral pairing invariants."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import ATTACKS, iter_traces, read_csv, stable_hash, trace_meta, trace_run_id, write_csv, write_md


FIELDS = [
    "attack_run_id", "neutral_run_id", "condition", "same_model", "same_task_id",
    "same_seed", "same_initial_state_hash", "same_policy_spec_hash",
    "same_tool_permission_hash", "same_clean_task_semantics_hash", "same_turn_count",
    "same_required_information_hash", "same_endpoint_evaluator_hash",
    "pairing_invariant_pass", "exclusion_reason",
]


def load_trace_meta(root: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    out = {}
    for p in iter_traces(root):
        t = json.loads(p.read_text(encoding="utf-8"))
        m = trace_meta(t)
        rid = trace_run_id(t)
        key = (str(m.get("model") or m.get("model_alias")), str(m.get("task_id")), str(m.get("seed")), str(m.get("condition") or m.get("condition_id")))
        m = dict(m)
        m["run_id"] = rid
        m["trace_path"] = str(p)
        m["turn_count"] = len(t.get("conversation_turns") or [x for x in t.get("conversation", []) if x.get("role") == "user"])
        if not m.get("initial_state_hash"):
            obj = t.get("initial_environment_state") or {}
            m["initial_state_hash"] = obj.get("state_hash") if isinstance(obj, dict) else ""
        out[key] = m
    return out


def process(trace_root: Path, out_csv: Path, report: Path) -> tuple[int, int]:
    idx = load_trace_meta(trace_root)
    rows = []
    for (model, task, seed, cond), a in sorted(idx.items()):
        if cond not in ATTACKS:
            continue
        n = idx.get((model, task, seed, "neutral_control"))
        if not n:
            rows.append({"attack_run_id": a.get("run_id"), "condition": cond, "pairing_invariant_pass": False, "exclusion_reason": "missing_neutral"})
            continue
        # Fail-closed equality for hashes: both sides must be PRESENT and non-empty
        # and equal.  A missing/blank hash must NOT trivially pass ("None"=="None").
        def same_hash(field: str) -> bool:
            va, vn = a.get(field), n.get(field)
            sa, sn = ("" if va is None else str(va)), ("" if vn is None else str(vn))
            return bool(sa) and bool(sn) and sa == sn

        checks = {
            "same_model": model == str(n.get("model") or n.get("model_alias")),
            "same_task_id": task == str(n.get("task_id")),
            "same_seed": seed == str(n.get("seed")),
            "same_initial_state_hash": same_hash("initial_state_hash"),
            "same_policy_spec_hash": same_hash("policy_spec_hash"),
            "same_tool_permission_hash": same_hash("tool_permission_hash"),
            "same_clean_task_semantics_hash": same_hash("clean_task_semantics_hash"),
            "same_turn_count": str(a.get("turn_count")) == str(n.get("turn_count")),
            "same_required_information_hash": same_hash("required_information_hash"),
            "same_endpoint_evaluator_hash": same_hash("endpoint_evaluator_hash"),
        }
        fail = [k for k, v in checks.items() if not v]
        rows.append(
            {
                "attack_run_id": a.get("run_id"),
                "neutral_run_id": n.get("run_id"),
                "condition": cond,
                **checks,
                "pairing_invariant_pass": not fail,
                "exclusion_reason": ";".join(fail),
            }
        )
    write_csv(out_csv, rows, FIELDS)
    cnt = Counter(str(r["pairing_invariant_pass"]) for r in rows)
    write_md(report, f"""# R7-B pairing invariant 审计

- pairs checked: {len(rows)}
- PASS: {cnt.get('True', 0)}
- FAIL: {cnt.get('False', 0)}
- output: `{out_csv}`

规则：confirmatory PASR 只允许 `pairing_invariant_pass=True` 的 pair。
""")
    return len(rows), cnt.get("False", 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace_root", type=Path, default=ROOT / "results/r7b_ipma/main")
    ap.add_argument("--out_csv", type=Path, default=ROOT / "results/r7b_ipma/main/integrity/pairing_invariant_report.csv")
    ap.add_argument("--report", type=Path, default=ROOT / "reports/r7b_ipma/R7B_PAIRING_INVARIANT_AUDIT_CN.md")
    args = ap.parse_args()
    n, fail = process(args.trace_root, args.out_csv, args.report)
    print(json.dumps({"pairs": n, "fail": fail}, ensure_ascii=False))


if __name__ == "__main__":
    main()

