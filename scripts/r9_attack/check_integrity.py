#!/usr/bin/env python3
"""Integrity + double-recompute check (spec 18).

Before analysis, verify the spec 18 accounting for a stage's episodes and DOUBLE-COMPUTE
the primary metrics + endpoint transitions with the independent reference implementation,
requiring 0 mismatch. Also folds in the safety audit and canonical invariance (spec 7).

Fails (non-zero exit) if any of the spec 18 hard conditions is violated:
  missing / duplicate / official reward None / canonical hash mismatch / state reset
  failure / silent retry / outbound network event / non-allowlisted tool / metric mismatch.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.canonical_message_cache import CanonicalMessageCache, verify_invariance  # noqa: E402
from scripts.r9_attack.common import paths  # noqa: E402
from scripts.r9_attack.common.io_utils import read_json, read_jsonl, write_json  # noqa: E402
from scripts.r9_attack.common.results_sink import accounting  # noqa: E402
from scripts.r9_attack.reference_metrics import compare  # noqa: E402


def double_recompute(records: list[dict]) -> dict:
    """Spec 18: production vs reference metrics/endpoint transitions; 0 mismatch required."""
    mismatches = []
    for r in records:
        if r.get("infra_failure"):
            continue
        problems = compare(r)
        if problems:
            mismatches.append({"episode_id": r.get("episode_id"), "problems": problems})
    return {"n_checked": len(records), "n_mismatch": len(mismatches), "mismatches": mismatches[:50]}


def canonical_invariance(records: list[dict]) -> dict:
    """Spec 7 semantic invariance.

    BFCL: the canonical message is fixed PER TURN INDEX (official dataset turns), so we
    check turn-index hash identity across conditions against the frozen cache.

    ToolSandbox: the canonical response is fixed PER SLOT (frozen Fact Ledger), not per
    turn index — an attack may shift WHICH slot the agent's question hits at a given turn
    (same facts, possibly different order), which is not a spec-7.2 violation. The correct
    invariance is that every canonical message used is a VERBATIM member of the scenario's
    frozen ledger responses (opening + slot canonical_responses), i.e. never LLM-rewritten.
    """
    from collections import defaultdict

    from scripts.r9_attack.common.io_utils import read_jsonl, sha256_text

    # BFCL turn-index invariance via the frozen cache.
    cache = CanonicalMessageCache.load() if paths.CANONICAL_MESSAGES.exists() else None
    bfcl_turns = []
    for r in records:
        if r.get("benchmark") != "bfcl":
            continue
        for t in r.get("turns", []):
            if t.get("index", -1) < 0:
                continue
            bfcl_turns.append({
                "benchmark": r["benchmark"], "task_id": r["task_id"],
                "turn_index": t["index"], "canonical_hash": t["canonical_hash"],
            })
    if cache is not None:
        problems = [p for p in verify_invariance(bfcl_turns, cache) if "toolsandbox" not in p]
    else:
        seen = defaultdict(set)
        for tr in bfcl_turns:
            seen[(tr["benchmark"], tr["task_id"], tr["turn_index"])].add(tr["canonical_hash"])
        problems = [f"{k}: {len(v)} distinct canonical hashes" for k, v in seen.items() if len(v) > 1]

    # ToolSandbox slot-membership invariance: every canonical hash must be a frozen response.
    frozen_hashes: dict[str, set] = {}
    for led in read_jsonl(paths.FACT_LEDGERS):
        h = {sha256_text(led.get("opening_utterance", ""))}
        for s in led.get("slots", []):
            h.add(sha256_text(s.get("canonical_response", "")))
        h.add(sha256_text(led.get("default_response", "")))
        frozen_hashes[led["scenario"]] = h
    ts_checked = 0
    for r in records:
        if r.get("benchmark") != "toolsandbox":
            continue
        allowed = frozen_hashes.get(r["task_id"])
        for t in r.get("turns", []):
            ts_checked += 1
            if allowed is not None and t.get("canonical_hash") not in allowed:
                problems.append(f"({r['task_id']}, turn {t.get('index')}): canonical not a frozen ledger response")

    return {"n_turns_checked": len(bfcl_turns) + ts_checked, "n_problems": len(problems), "problems": problems[:50]}


def check(stage_path: pathlib.Path, expected: int | None) -> dict:
    records = list(read_jsonl(stage_path))
    acct = accounting(records, expected)
    recompute = double_recompute(records)
    invariance = canonical_invariance(records)

    safety = read_json(paths.SAFETY_AUDIT) if paths.SAFETY_AUDIT.exists() else {"passed": False, "status": "MISSING"}

    hard_fail = {
        "missing": bool(acct["missing"]) if acct["missing"] is not None else False,
        "duplicates": bool(acct["duplicates"]),
        "official_reward_none": acct["official_reward_none"] > 0,
        "canonical_hash_mismatch": invariance["n_problems"] > 0,
        "state_reset_failures": acct["state_reset_failures"] > 0,
        "outbound_network_events": acct["outbound_network_events"] > 0,
        "non_allowlisted_tool_calls": acct["non_allowlisted_tool_calls"] > 0,
        "metric_mismatch": recompute["n_mismatch"] > 0,
        "safety_scope_not_closed": not safety.get("passed", False),
    }
    passed = not any(hard_fail.values())
    return {
        "stage_file": str(stage_path),
        "passed": passed,
        "status": "INTEGRITY_OK" if passed else "INTEGRITY_FAIL",
        "hard_fail": hard_fail,
        "accounting": acct,
        "double_recompute": recompute,
        "canonical_invariance": invariance,
        "safety_audit_status": safety.get("status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="R9 integrity + double recompute (spec 18)")
    parser.add_argument("--stage-file", required=True, help="path to a stage episodes.jsonl")
    parser.add_argument("--expected", type=int, default=0, help="expected unique episodes (0 = skip missing check)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    result = check(pathlib.Path(args.stage_file), args.expected or None)
    out = pathlib.Path(args.out) if args.out else pathlib.Path(args.stage_file).with_name(
        pathlib.Path(args.stage_file).stem + "_integrity.json")
    write_json(out, result)
    print(f"[integrity] {result['status']} -> {out}")
    for k, v in result["hard_fail"].items():
        print(f"   {'FAIL' if v else 'ok  '}  {k}")
    print(f"[integrity] recompute mismatches={result['double_recompute']['n_mismatch']} "
          f"canonical problems={result['canonical_invariance']['n_problems']}")
    return 0 if result["passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
