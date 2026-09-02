#!/usr/bin/env python3
"""R8 Full-Episode: integrity + double-implementation audit (spec 14).

Checks, all fail-loud:
  - expected episodes = 2700; duplicates = 0; missing = 0 (or <=1% with a recorded
    infrastructure .error.json reason);
  - official reward None = 0 (over completed episodes);
  - initial-db-hash identical across all cells of the same (domain, task) -> no
    cross-condition / cross-rep initial-state leakage;
  - policy / tool-schema / task hash of every trace matches the frozen manifest;
  - no duplicate run_id (a duplicate would be a silent rerun);
  - DOUBLE IMPLEMENTATION on the tool-count primary: the trace's stored
    `agent_tool_calls` (sum of tool_calls) must equal an independent recompute
    from `native_messages`. Reward is single-source (native evaluator) and is
    only checked for non-None + internal consistency (official_reward ==
    reward_components.overall_reward).

Writes results/r8_full_episode/integrity/integrity_report.json and exits non-zero
if any hard check fails.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.r8_full_episode.run_full_episode import MODEL_ENDPOINTS  # noqa: E402
from scripts.r8_full_episode.extract_episode_metrics import compute_metrics  # noqa: E402

CONDITIONS = ["C0", "C1", "C2", "C3", "C4"]


def _rel(p):
    """Path display robust to relative/absolute traces-root."""
    try:
        return str(p.resolve().relative_to(ROOT))
    except Exception:
        return str(p)


def load_manifest(frozen: pathlib.Path):
    manifest = json.loads((frozen / "environment_manifest.json").read_text())
    tasks = [json.loads(l) for l in (frozen / "task_manifest.jsonl").read_text().splitlines() if l.strip()]
    return manifest, tasks


def expected_run_ids(tasks: list, replicates: int) -> set[str]:
    out = set()
    for t in tasks:
        for model in MODEL_ENDPOINTS:
            for cond in CONDITIONS:
                for rep in range(replicates):
                    out.add(f"r8_{t['domain']}_{t['tau2_task_id']}_{model}_{cond}_rep{rep}")
    return out


def indep_tool_count(rec: dict) -> int:
    return sum(len(m.get("tool_calls") or []) for m in (rec.get("native_messages") or [])
               if m.get("role") == "assistant")


def stored_tool_count(rec: dict) -> int:
    return sum(len(x.get("tool_calls") or []) for x in (rec.get("agent_tool_calls") or []))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces-root", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/traces")
    ap.add_argument("--frozen", type=pathlib.Path,
                    default=ROOT / "data/r8_full_episode/frozen")
    ap.add_argument("--out", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/integrity/integrity_report.json")
    ap.add_argument("--allow-partial", action="store_true",
                    help="do not fail on missing cells (for smoke/partial runs)")
    args = ap.parse_args()

    manifest, tasks = load_manifest(args.frozen)
    reps = manifest["replicates"]
    expected = expected_run_ids(tasks, reps)
    task_hash = {f"{t['domain']}_{t['tau2_task_id']}": t["task_hash"] for t in tasks}
    task_type = {f"{t['domain']}_{t['tau2_task_id']}": t["task_type"] for t in tasks}
    env_h = manifest["env_hashes"]

    present, dup_run_ids = {}, []
    reward_none, hash_mismatch, tool_count_mismatch, reward_inconsistent = [], [], [], []
    infra_errors, infra_error_ids = [], set()
    parse_failures = []
    initial_db = collections.defaultdict(set)  # (domain,task) -> {hashes}

    def rid_from_error_path(p: pathlib.Path) -> str:
        # traces/{domain}/{task}/{model}/{cond}/rep_{k}.error.json  -> run_id
        parts = p.parts
        try:
            dom, task, model, cond = parts[-5], parts[-4], parts[-3], parts[-2]
            rep = p.name.split("rep_")[1].split(".")[0]
            return f"r8_{dom}_{task}_{model}_{cond}_rep{rep}"
        except Exception:  # noqa: BLE001
            return str(p)

    for p in sorted(args.traces_root.rglob("rep_*.error.json")):
        infra_errors.append(_rel(p))
        infra_error_ids.add(rid_from_error_path(p))

    for p in sorted(args.traces_root.rglob("rep_*.json")):
        if p.name.endswith(".error.json"):
            continue
        try:
            rec = json.loads(p.read_text())
        except Exception as exc:  # noqa: BLE001 - a corrupt trace is a hard finding, not skipped
            parse_failures.append(f"{_rel(p)}: {exc!r}"[:200])
            continue
        rid = rec.get("run_id")
        if rid in present:
            dup_run_ids.append(rid)
        present[rid] = rec
        dk = f"{rec['domain']}_{rec['task_id']}"
        # reward non-None
        if rec.get("official_reward") is None:
            reward_none.append(rid)
        # reward internal consistency
        comp = rec.get("reward_components") or {}
        if comp.get("overall_reward") != rec.get("official_reward"):
            reward_inconsistent.append(rid)
        # hashes vs manifest
        if task_hash.get(dk) and rec.get("task_hash") != task_hash[dk]:
            hash_mismatch.append((rid, "task_hash"))
        if rec.get("domain") in env_h:
            if rec.get("policy_hash") != env_h[rec["domain"]]["policy_hash"]:
                hash_mismatch.append((rid, "policy_hash"))
            if rec.get("tool_schema_hash") != env_h[rec["domain"]]["tool_schema_hash"]:
                hash_mismatch.append((rid, "tool_schema_hash"))
        # initial-db leakage
        if rec.get("initial_db_hash") is not None:
            initial_db[dk].add(rec["initial_db_hash"])
        # GENUINE double implementation: production stored count vs the INDEPENDENT
        # reference implementation (extract_episode_metrics.compute_metrics).
        stored = stored_tool_count(rec)
        independent = compute_metrics(rec, rec.get("domain"))["total_agent_tool_calls"]
        if stored != independent:
            tool_count_mismatch.append((rid, independent, stored))

    missing = sorted(expected - set(present))
    unexplained_missing = [m for m in missing if m not in infra_error_ids]
    unexpected = sorted(set(present) - expected)
    db_leak = {k: sorted(v) for k, v in initial_db.items() if len(v) > 1}

    n_present = len(present)
    n_expected = len(expected)
    miss_frac = len(missing) / n_expected if n_expected else 0.0

    checks = {
        "expected_episodes": n_expected,
        "present_episodes": n_present,
        "missing": len(missing),
        "missing_frac": round(miss_frac, 4),
        "unexplained_missing": len(unexplained_missing),  # missing WITHOUT an .error.json
        "duplicate_run_ids": len(dup_run_ids),
        "unexpected_run_ids": len(unexpected),
        "reward_none": len(reward_none),
        "reward_inconsistent": len(reward_inconsistent),
        "hash_mismatch": len(hash_mismatch),
        "tool_count_double_impl_mismatch": len(tool_count_mismatch),
        "initial_db_leakage_tasks": len(db_leak),
        "infra_error_files": len(infra_errors),
        "parse_failures": len(parse_failures),
    }
    # spec 14: missing must be 0, OR <=1% AND every missing cell has a recorded infra
    # reason (an .error.json). Unexplained missing always fails (unless --allow-partial).
    missing_ok = (len(unexplained_missing) == 0) and (miss_frac <= 0.01)
    hard_fail = (
        (not args.allow_partial and not missing_ok) or
        len(dup_run_ids) > 0 or len(unexpected) > 0 or len(reward_none) > 0 or
        len(reward_inconsistent) > 0 or len(hash_mismatch) > 0 or
        len(tool_count_mismatch) > 0 or len(db_leak) > 0 or len(parse_failures) > 0
    )
    report = dict(
        verdict=("FAIL" if hard_fail else "PASS"),
        allow_partial=args.allow_partial,
        checks=checks,
        details=dict(
            missing_sample=missing[:20], unexplained_missing_sample=unexplained_missing[:20],
            duplicate_run_ids=dup_run_ids[:20],
            unexpected_sample=unexpected[:20], reward_none=reward_none[:20],
            reward_inconsistent=reward_inconsistent[:20],
            hash_mismatch=hash_mismatch[:20],
            tool_count_mismatch=tool_count_mismatch[:20],
            initial_db_leakage=db_leak, infra_error_files=infra_errors[:40],
            parse_failures=parse_failures[:20],
        ),
        selected_counts=manifest["selected_counts"],
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(checks, indent=2))
    print(f"verdict={report['verdict']}  (wrote {args.out})")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
