#!/usr/bin/env python3
"""R8 Full-Episode: build & FREEZE the 36-task registry + environment manifest.

Design (frozen, decided before selection):
    retail  : 6 read-heavy / 6 single-mutation / 6 compound   = 18
    airline : 4 read-heavy / 4 single-mutation / 10 compound   = 18
    total   : 36 tasks x 3 models x 5 conditions x 5 replicates = 2700 episodes

Why airline is 4/4/10 (NOT 6/6/6): airline is a booking domain; on the official
tau2 1.0.0 base split there are at most ~4 read-heavy and ~4 single-mutation
MULTI-STEP tasks even at the loosest reasonable complexity floor, so 6/6/6 is
infeasible without fabricating tasks (forbidden). Domain balance (18/18) and the
2700 scale are preserved; per-domain task_type imbalance is recorded as a domain
structural constraint and enters analysis as a covariate, never silently.

Selection is BLIND: tasks are gated only by (a) official scorer availability,
(b) a multi-step COMPLEXITY proxy computed from the reference actions, and
(c) not being flagged buggy. Within each (domain, task_type) bucket we take the
top-K by complexity (assistant tool-action count, then distinct tools), ties
broken by ascending task id. Historical PASR / mid-phase results are NEVER used.
Reference actions are used ONLY as a complexity proxy, never as the unique
correct trajectory (per the execution prompt).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.run import get_tasks  # noqa: E402
from tau2.registry import registry  # noqa: E402

FROZEN = ROOT / "data/r8_full_episode/frozen"
INTEGRITY = ROOT / "results/r8_full_episode/integrity"

# Mutation tool sets (official tau2 write tools; same sets used by R7-D).
MUT = {
    "retail": {"cancel_pending_order", "exchange_delivered_order_items",
               "modify_pending_order_address", "modify_pending_order_items",
               "modify_pending_order_payment", "modify_user_address",
               "return_delivered_order_items"},
    "airline": {"book_reservation", "cancel_reservation", "update_reservation_baggages",
                "update_reservation_flights", "update_reservation_passengers",
                "send_certificate"},
}

# Tools that are neither reads nor mutations (do not count toward read-intensity).
NON_READ_UTIL = {"calculate", "think", "transfer_to_human_agents"}

# Frozen design: (domain -> {task_type -> K}). Decided before looking at any run result.
DESIGN = {
    "retail": {"read": 6, "single": 6, "compound": 6},
    "airline": {"read": 4, "single": 4, "compound": 10},
}
N_MODELS = 3
N_CONDITIONS = 5
N_REPLICATES = 5

# Complexity floor: reference solution must have >= this many assistant tool actions
# (multi-step proxy). Combined with the required user information exchange this yields
# >= 5 interaction steps. Recorded in the manifest so the operationalization is explicit.
MIN_ASSISTANT_ACTIONS = 3


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify(task, mut: set[str]) -> dict | None:
    """Return complexity/type record for a task, or None if it fails the blind gate."""
    ec = task.evaluation_criteria
    if ec is None:
        return None
    aacts = [a for a in (ec.actions or []) if a.requestor == "assistant"]
    # exclude only tasks with an OPEN issue (RESOLVED / WONT_FIX are fine).
    issues = getattr(task, "issues", None) or []
    if any(getattr(i.status, "value", str(i.status)) == "open" for i in issues):
        return None
    tools = sorted({a.name for a in aacts})
    n_mut = sum(1 for a in aacts if a.name in mut)
    # reads = information-gathering tool calls (exclude mutations and non-read utilities).
    n_read = sum(1 for a in aacts if a.name not in mut and a.name not in NON_READ_UTIL)
    # (a) multi-step complexity proxy
    if len(aacts) < MIN_ASSISTANT_ACTIONS:
        return None
    # (c) requires a real user information/decision exchange
    if not str(task.user_scenario).strip():
        return None
    # (b) type-specific complexity gate:
    #   read-heavy  : READ-INTENSITY (>=3 reads across >=2 read tools). The generic
    #                 ">=3 distinct tools" gate is unreachable for pure-read airline
    #                 tasks (they only ever use get_reservation_details+get_user_details),
    #                 so read-heavy complexity is operationalized as read-intensity.
    #   mutation    : >=3 distinct tools OR (>=2 reads + >=1 mutation).
    if n_mut == 0:
        if not (n_read >= 3 and len(tools) >= 2):
            return None
        ttype = "read"
    elif n_mut == 1:
        # single mutation: needs surrounding read/verify work to be multi-step.
        if not (len(tools) >= 3 or n_read >= 2):
            return None
        ttype = "single"
    else:
        # compound: >=3 distinct tools OR (>=2 reads + mutation) OR >=3 mutations
        # (a task issuing 3+ writes is unambiguously multi-step compound even with
        # few distinct tools / no reads).
        if not (len(tools) >= 3 or (n_read >= 2 and n_mut >= 1) or n_mut >= 3):
            return None
        ttype = "compound"
    return dict(task_id=str(task.id), task_type=ttype, n_assistant_actions=len(aacts),
                n_distinct_tools=len(tools), n_reads=n_read, n_mutations=n_mut,
                ref_tools=tools)


def env_hashes(domain: str) -> dict:
    """Deterministic policy / tool-schema / initial-db hashes for a domain."""
    ctor = registry.get_env_constructor(domain)
    env = ctor()
    policy = env.get_policy() or ""
    tool_schemas = sorted(
        json.dumps(t.openai_schema, sort_keys=True) if hasattr(t, "openai_schema")
        else json.dumps(getattr(t, "params", str(t)), sort_keys=True, default=str)
        for t in env.get_tools()
    )
    try:
        db_hash = env.get_db_hash()
    except Exception:  # noqa: BLE001
        db_hash = None
    return dict(policy_hash=sha(policy), policy_len=len(policy),
                tool_schema_hash=sha("\n".join(tool_schemas)),
                n_tools=len(tool_schemas), initial_db_hash=db_hash)


def git_commit(repo: pathlib.Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                       text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main() -> int:
    FROZEN.mkdir(parents=True, exist_ok=True)
    INTEGRITY.mkdir(parents=True, exist_ok=True)

    tau_root = pathlib.Path("/home/xqin5/tau2-bench")
    selected: list[dict] = []
    per_domain_env: dict[str, dict] = {}
    availability: dict[str, dict] = {}

    for domain in ("retail", "airline"):
        tasks = {str(t.id): t for t in get_tasks(domain)}
        recs = [r for r in (classify(t, MUT[domain]) for t in tasks.values()) if r]
        buckets: dict[str, list[dict]] = {"read": [], "single": [], "compound": []}
        for r in recs:
            buckets[r["task_type"]].append(r)
        availability[domain] = {k: len(v) for k, v in buckets.items()}
        per_domain_env[domain] = env_hashes(domain)

        for ttype, k in DESIGN[domain].items():
            pool = sorted(buckets[ttype],
                          key=lambda r: (-r["n_assistant_actions"], -r["n_distinct_tools"],
                                         int(r["task_id"]) if r["task_id"].isdigit() else r["task_id"]))
            if len(pool) < k:
                raise SystemExit(
                    f"INFEASIBLE: {domain}/{ttype} needs {k} but only {len(pool)} eligible. "
                    f"Availability={availability[domain]}. Re-decide the design before freezing.")
            for r in pool[:k]:
                t = tasks[r["task_id"]]
                task_json = t.model_dump_json()
                selected.append(dict(
                    cell_uid=f"{domain}_{ttype}_{r['task_id']}",
                    domain=domain, tau2_task_id=r["task_id"], task_type=ttype,
                    complexity=dict(n_assistant_actions=r["n_assistant_actions"],
                                    n_distinct_tools=r["n_distinct_tools"],
                                    n_reads=r["n_reads"], n_mutations=r["n_mutations"],
                                    ref_tools=r["ref_tools"]),
                    task_hash=sha(task_json),
                    user_scenario=str(t.user_scenario)[:2000],
                    selection_basis="official scorer + multi-step complexity proxy; "
                                    "blind top-K by complexity, NOT PASR / mid-phase",
                ))

    # ---- write task_manifest.jsonl ----
    tm = FROZEN / "task_manifest.jsonl"
    with tm.open("w") as f:
        for row in selected:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ---- write environment_manifest.json ----
    counts: dict[str, dict[str, int]] = {"retail": {}, "airline": {}}
    for row in selected:
        counts[row["domain"]][row["task_type"]] = counts[row["domain"]].get(row["task_type"], 0) + 1
    manifest = dict(
        experiment="R8_full_episode",
        tau2_repo="/home/xqin5/tau2-bench",
        tau2_commit=git_commit(tau_root),
        ir_mstu_commit=git_commit(ROOT),
        task_split="official base split (tau2 1.0.0)",
        domains=["retail", "airline"],
        excluded_domains=["telecom (dual-control mixes user tool actions with language treatment)"],
        design=DESIGN,
        design_note="airline is 4/4/10 not 6/6/6: booking domain lacks >=6 read-heavy / "
                    "single-mutation MULTI-STEP tasks on the base split; domain balance 18/18 "
                    "and 2700 scale preserved; task_type imbalance recorded as covariate.",
        min_assistant_actions=MIN_ASSISTANT_ACTIONS,
        complexity_gates={
            "floor": f">= {MIN_ASSISTANT_ACTIONS} assistant tool actions + >=1 required user exchange",
            "read": ">=3 reads across >=2 read tools (read-INTENSITY; the generic >=3-distinct-tools "
                    "gate is unreachable for pure-read airline tasks, which only use "
                    "get_reservation_details+get_user_details)",
            "single": ">=3 distinct tools OR >=2 reads",
            "compound": ">=3 distinct tools OR (>=2 reads + mutation) OR >=3 mutations",
        },
        selection="blind top-K by complexity (assistant actions, then distinct tools); NOT PASR",
        n_tasks=len(selected),
        selected_counts=counts,
        eligible_availability=availability,
        expected_episodes=len(selected) * N_MODELS * N_CONDITIONS * N_REPLICATES,
        models={
            "gemma4_31b": {"served_name": "openai/g4-v2-1", "api_base": "http://127.0.0.1:8005/v1"},
            "gpt_oss_120b": {"served_name": "openai/gpt-oss", "api_base": "http://127.0.0.1:8192/v1"},
            "mistral_small_3p2": {"served_name": "openai/mistral-small-3p2", "api_base": "http://127.0.0.1:8007/v1"},
        },
        conditions=["C0", "C1", "C2", "C3", "C4"],
        replicates=5,
        env_hashes=per_domain_env,
        versions=env_versions(),
    )
    em = FROZEN / "environment_manifest.json"
    em.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    # ---- freeze hashes ----
    fh = INTEGRITY / "frozen_hashes.sha256"
    lines = []
    for p in (tm, em):
        lines.append(f"{sha(p.read_text())}  {p.relative_to(ROOT)}")
    fh.write_text("\n".join(lines) + "\n")

    print(f"selected {len(selected)} tasks; counts={counts}; availability={availability}")
    print(f"expected episodes = {manifest['expected_episodes']}")
    print(f"wrote {tm}\n      {em}\n      {fh}")
    return 0


def env_versions() -> dict:
    import importlib.metadata as im
    import platform
    out = {"python": platform.python_version()}
    for mod in ("tau2", "litellm", "vllm"):
        try:
            out[mod] = im.version(mod)
        except Exception:  # noqa: BLE001
            try:
                out[mod] = getattr(__import__(mod), "__version__", "?")
            except Exception:  # noqa: BLE001
                out[mod] = "not-importable"
    try:
        out["gpu"] = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True
        ).strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        out["gpu"] = "unknown"
    return out


if __name__ == "__main__":
    raise SystemExit(main())
