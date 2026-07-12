#!/usr/bin/env python3
"""R7-D Step 2 pilot orchestrator (minimal, methodology-validation scale).

For each (task, model, prefix_replicate):
  1. build a neutral opening from the tau2 task's structured instructions,
  2. run the agent until it first addresses the user (the junction),
  3. snapshot the real env + conversation,
  4. run all 5 branches (N0/N1/S/A/P) from that snapshot,
  5. record per-suffix process metrics + official endpoint reward.

Blocks = (task, model, replicate); a failed branch fails the whole block.
All model traffic is local vLLM. The tau2 DB is in-process synthetic and resets
per fresh environment; nothing external is touched.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.r7d_ipma.step2.tau2_runner import (  # noqa: E402
    Tau2Session, suffix_metrics, convo_to_text, get_domain_env,
)
from scripts.r7d_ipma.step2.branch_policies import BRANCHES, UserPolicy  # noqa: E402
from tau2.run import get_tasks  # noqa: E402

MUT_TOOLS = {
    "retail": {"cancel_pending_order", "exchange_delivered_order_items",
               "modify_pending_order_address", "modify_pending_order_items",
               "modify_pending_order_payment", "modify_user_address",
               "return_delivered_order_items"},
    "airline": {"book_reservation", "cancel_reservation", "update_reservation_baggages",
                "update_reservation_flights", "update_reservation_passengers",
                "send_certificate"},
    "telecom": {"suspend_line", "resume_line", "send_payment_request", "refuel_data",
                "enable_roaming", "disable_roaming", "set_data_limit"},
}

MAX_PREFIX_STEPS = 8
MAX_BRANCH_USER_TURNS = 3


def opening_message(task) -> str:
    ins = task.user_scenario.instructions
    reason = getattr(ins, "reason_for_call", "") or ""
    known = getattr(ins, "known_info", "") or ""
    parts = ["Hi."]
    if reason:
        parts.append(reason.strip())
    if known:
        parts.append(known.strip())
    return " ".join(parts)


def run_prefix(session: Tau2Session, task) -> tuple[int, str]:
    """Run neutral opening; stop at the first agent message that addresses the user
    (no tool call). Returns (prefix_len, junction_reason)."""
    u = session.user_say(opening_message(task))
    am = session.agent_respond(u)
    # session.agent_respond already loops tool calls and stops when the agent speaks
    # to the user. That user-facing message is our junction.
    reason = "agent_first_user_message"
    if not (am.content or "").strip():
        reason = "agent_first_user_message_empty"
    return len(session.convo), reason


def run_branch(session, snap, branch, stratum, prefix_len, seed, n0_text) -> dict:
    session.restore(snap)
    policy = UserPolicy(branch=branch, stratum=stratum, seed=seed, n0_fixed_text=n0_text)
    # the agent's last message at the junction:
    last_agent = next((t.content for t in reversed(session.convo) if t.speaker == "agent"), "")
    user_turns_emitted = []
    for _ in range(MAX_BRANCH_USER_TURNS):
        utext = policy.next_user_turn(last_agent)
        if utext is None:
            break
        user_turns_emitted.append(utext)
        u = session.user_say(utext)
        am = session.agent_respond(u)
        last_agent = am.content or ""
        # stop if agent signalled done
        if any(t.tool_name in ("done",) for t in session.convo[-4:] if t.speaker == "tool"):
            break
    m = suffix_metrics(session.convo, prefix_len)
    m.update(branch=branch, user_turns=user_turns_emitted,
             suffix_text=convo_to_text(session.convo, prefix_len))
    return m


def evaluate_endpoint(session, task, domain) -> dict:
    """Official tau2 endpoint reward on the full conversation, if constructible."""
    try:
        from tau2.evaluator.evaluator import evaluate_simulation, EvaluationType
        from tau2.data_model.simulation import SimulationRun
        from tau2.data_model.message import AssistantMessage, UserMessage, ToolMessage
        msgs = []
        for t in session.convo:
            if t.speaker == "user":
                msgs.append(UserMessage(role="user", content=t.content))
            elif t.speaker == "agent":
                msgs.append(AssistantMessage(role="assistant", content=t.content or ""))
            elif t.speaker == "tool":
                msgs.append(ToolMessage(id=str(t.idx), role="tool",
                                        content=t.content, requestor="assistant",
                                        error=bool(t.tool_error)))
        sim = SimulationRun(id="r7d_step2", task_id=str(task.id), messages=msgs,
                            trial=0, seed=0)
        rew = evaluate_simulation(sim, task, EvaluationType.ALL, False, domain)
        return {"endpoint_reward": getattr(rew, "reward", None),
                "endpoint_db_match": getattr(rew, "db_match", None)}
    except Exception as exc:  # noqa: BLE001
        return {"endpoint_reward": None, "endpoint_eval_error": repr(exc)[:150]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--models", nargs="+",
                    default=["gemma4_31b", "gpt_oss_120b", "mistral_small_3p2"])
    ap.add_argument("--replicates", type=int, default=2)
    ap.add_argument("--limit-tasks", type=int, default=0)
    args = ap.parse_args()

    args.out = args.out.resolve()
    reg = [json.loads(l) for l in args.registry.open()]
    if args.limit_tasks:
        reg = reg[:args.limit_tasks]
    tasks_by_dom = {}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    (args.out.parent / "traces").mkdir(exist_ok=True)
    rows = []
    n_block = 0
    t0 = time.time()

    for entry in reg:
        dom = entry["domain"]
        if dom not in tasks_by_dom:
            tasks_by_dom[dom] = {str(t.id): t for t in get_tasks(dom)}
        task = tasks_by_dom[dom][str(entry["tau2_task_id"])]
        stratum = entry["stratum"]
        for model in args.models:
            for rep in range(args.replicates):
                n_block += 1
                block_id = f"{entry['task_uid']}__{model}__rep{rep}"
                try:
                    session = Tau2Session(dom, model, MUT_TOOLS[dom])
                    prefix_len, junction = run_prefix(session, task)
                    snap = session.snapshot(junction)
                    n0_text = "Yes, please proceed with the required process."
                    block_rows = []
                    for branch in BRANCHES:
                        seed = abs(hash((block_id, branch))) % (2**31)
                        m = run_branch(session, snap, branch, stratum, prefix_len, seed, n0_text)
                        ep = evaluate_endpoint(session, task, dom)
                        m.update(ep)
                        m.update(task_uid=entry["task_uid"], tau2_task_id=entry["tau2_task_id"],
                                 domain=dom, stratum=stratum, model=model, replicate=rep,
                                 block_id=block_id, prefix_len=prefix_len,
                                 junction=junction, snapshot_db_hash=snap.db_hash)
                        block_rows.append(m)
                    rows.extend(block_rows)
                    # dump the block's full traces for review
                    (args.out.parent / "traces" / f"{block_id}.json").write_text(
                        json.dumps({"block_id": block_id, "prefix": convo_to_text(snap.convo),
                                    "branches": {r["branch"]: r["suffix_text"] for r in block_rows}},
                                   ensure_ascii=False, indent=2))
                    print(f"[{n_block}] {block_id}  OK  "
                          f"A_tools={next(r['n_tool_events'] for r in block_rows if r['branch']=='A')} "
                          f"N1_tools={next(r['n_tool_events'] for r in block_rows if r['branch']=='N1')}",
                          flush=True)
                except Exception as exc:  # noqa: BLE001
                    print(f"[{n_block}] {block_id}  BLOCK_FAIL {exc!r}", flush=True)
                    rows.append(dict(block_id=block_id, task_uid=entry["task_uid"],
                                     model=model, replicate=rep, branch="BLOCK_FAIL",
                                     error=repr(exc)[:200]))

    # write per-suffix metrics
    import csv
    keys = ["block_id", "task_uid", "tau2_task_id", "domain", "stratum", "model", "replicate",
            "branch", "prefix_len", "junction", "n_tool_events", "n_reads", "n_unique_reads",
            "n_duplicate_reads", "n_mutations", "n_tool_errors", "n_user_turns",
            "n_agent_messages", "first_mutation_step", "evidence_before_first_mutation",
            "tool_sequence", "endpoint_reward", "suffix_len_turns", "error"]
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    ok = sum(1 for r in rows if r.get("branch") != "BLOCK_FAIL")
    print(f"\nblocks={n_block}  suffix_rows={ok}  elapsed={time.time()-t0:.0f}s")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
