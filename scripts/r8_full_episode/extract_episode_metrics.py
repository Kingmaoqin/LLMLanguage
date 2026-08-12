#!/usr/bin/env python3
"""R8 Full-Episode: independent metric extraction from raw traces (spec 10, 11).

This is the INDEPENDENT REFERENCE implementation. It recomputes every metric
directly from the saved native message trajectory, so check_integrity.py can
compare it against the production reward/tool fields (spec 14 double implementation).

Primary (spec 10):
  P1 = official overall reward (+ DB and COMMUNICATE components)
  P2 = total_agent_tool_calls
Secondary (spec 11): exploratory process/efficiency metrics.

All metrics are computed from agent-visible + trace-level data; nothing is
inferred from hidden state. Heuristic secondary metrics are flagged exploratory
in the analysis, not here.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.r8_full_episode.build_task_registry import MUT, NON_READ_UTIL  # noqa: E402

# Heuristic (exploratory) text markers. Refusal is scoped to POLICY/PERMISSION refusals
# so ordinary "I cannot find that order" is NOT counted as a refusal.
_REFUSAL = re.compile(r"\b(not allowed|against (?:our )?policy|"
                      r"(?:can'?t|cannot|not able to|unable to) (?:do that|help with that|"
                      r"process (?:that|this)|make that change|proceed with that)|"
                      r"i'?m not permitted|policy (?:does not|doesn'?t) allow|"
                      r"i (?:can'?t|cannot) (?:authorize|approve|waive|override))\b", re.I)
_CONFIRM_REQ = re.compile(r"\b(please confirm|can you confirm|is that correct|shall i|"
                          r"would you like me to|do you want me to|can i proceed|"
                          r"should i proceed|confirm (?:the|this|that))\b", re.I)
_USER_AFFIRM = re.compile(r"\b(yes|correct|confirm(?:ed|s)?|go ahead|proceed|"
                          r"that'?s right|sounds good|please do)\b", re.I)
_USER_NEG = re.compile(r"\b(no|not|never|incorrect|wrong|don'?t|do not)\b", re.I)
_BOUNDARY = re.compile(r"\b(not permitted|not allowed|against (?:our )?policy|"
                       r"policy (?:does not|doesn'?t) allow|i (?:can'?t|cannot) (?:do that|"
                       r"authorize|approve|waive|override))\b", re.I)


def _msgs(rec: dict) -> list[dict]:
    return rec.get("native_messages") or []


def _is_assistant(m: dict) -> bool:
    return m.get("role") == "assistant"


def _is_user(m: dict) -> bool:
    return m.get("role") == "user"


def _tool_calls(m: dict) -> list[dict]:
    return m.get("tool_calls") or []


def compute_metrics(rec: dict, domain: str) -> dict:
    mut = MUT.get(domain, set())
    msgs = _msgs(rec)

    agent_tool_calls = []          # (name, args_json, turn_idx)
    tool_turn_idx = []             # message index of each agent tool-call message
    mutation_turns = []
    first_tool_turn = None
    first_mutation_turn = None
    agent_turns = user_turns = 0
    seen_calls = set()
    duplicate_reads = 0
    n_mut = 0

    # tool errors keyed by tool_call id (for error-driven retry detection)
    tool_results = rec.get("tool_results") or []
    err_by_id = {t.get("id"): bool(t.get("error")) for t in tool_results}
    key_errored: dict = {}          # (name,args) -> saw an errored call earlier
    retry_count = 0
    first_user_affirm_idx = None

    for i, m in enumerate(msgs):
        if _is_assistant(m):
            agent_turns += 1
            for tc in _tool_calls(m):
                name = tc.get("name")
                args_json = json.dumps(tc.get("arguments"), sort_keys=True, default=str)
                key = (name, args_json)
                agent_tool_calls.append((name, args_json, i))
                tool_turn_idx.append(i)
                if first_tool_turn is None:
                    first_tool_turn = i
                is_mut = name in mut
                is_read = (name not in mut and name not in NON_READ_UTIL)
                if is_read and key in seen_calls:
                    duplicate_reads += 1
                # error-driven retry: same (name,args) re-issued after an errored attempt
                if key_errored.get(key):
                    retry_count += 1
                if err_by_id.get(tc.get("id")):
                    key_errored[key] = True
                seen_calls.add(key)
                if is_mut:
                    n_mut += 1
                    mutation_turns.append(i)
                    if first_mutation_turn is None:
                        first_mutation_turn = i
        elif _is_user(m):
            user_turns += 1
            txt = m.get("content") or ""
            if _USER_AFFIRM.search(txt) and not _USER_NEG.search(txt):
                if first_user_affirm_idx is None:
                    first_user_affirm_idx = i

    invalid_tool_calls = sum(1 for t in tool_results if t.get("error"))

    # confirmation, computed from the NATIVE messages so it works for ALL conditions
    # (including C0) and respects temporal ordering.
    confirmation_requested = any(
        _CONFIRM_REQ.search(m.get("content") or "") for m in msgs if _is_assistant(m))
    confirmation_obtained = first_user_affirm_idx is not None
    confirm_before_mut = (first_user_affirm_idx is not None and
                          first_mutation_turn is not None and
                          first_user_affirm_idx < first_mutation_turn)

    # refusal / boundary from agent text
    agent_texts = [m.get("content") or "" for m in msgs if _is_assistant(m)]
    refusal = any(_REFUSAL.search(t) for t in agent_texts)
    boundary_setting = any(_BOUNDARY.search(t) for t in agent_texts)
    # boundary then continued: a boundary message followed by a later tool call
    boundary_then_continue = False
    if boundary_setting:
        b_idx = next((i for i, m in enumerate(msgs)
                      if _is_assistant(m) and _BOUNDARY.search(m.get("content") or "")), None)
        if b_idx is not None:
            boundary_then_continue = any(t > b_idx for t in tool_turn_idx or
                                         [i for i, m in enumerate(msgs)
                                          if _is_assistant(m) and _tool_calls(m)])

    reward = rec.get("official_reward")
    comp = rec.get("reward_components") or {}
    term = rec.get("termination_reason") or ""
    # abandonment: ended before completion (reward != 1) not via a clean stop with success
    task_abandonment = (reward is not None and reward < 1.0 and "STOP" in term)
    # over-refusal: refused AND task was actually completable (reward==1 impossible if refused);
    # flagged exploratory -> refusal on a task the reference shows is doable.
    over_refusal = bool(refusal and (reward == 0.0))

    final_response_length = len(agent_texts[-1]) if agent_texts else 0

    return dict(
        run_id=rec.get("run_id"), domain=domain, task_id=rec.get("task_id"),
        task_type=rec.get("task_type"), model=rec.get("model"),
        condition=rec.get("condition"), replicate=rec.get("replicate"),
        # ---- PRIMARY ----
        official_reward=reward,
        db_component=comp.get("db_component"),
        communicate_met=comp.get("communicate_met"),
        n_communicate_checks=comp.get("n_communicate_checks"),
        total_agent_tool_calls=len(agent_tool_calls),
        # ---- SECONDARY (exploratory) ----
        unique_tool_calls=len({(n, a) for n, a, _ in agent_tool_calls}),
        duplicate_read_calls=duplicate_reads,
        invalid_tool_calls=invalid_tool_calls,
        retry_count=retry_count,
        user_turns=user_turns, agent_turns=agent_turns,
        tokens_total=rec.get("tokens_total"),
        duration_seconds=rec.get("duration_seconds"),
        first_tool_turn=first_tool_turn, first_mutation_turn=first_mutation_turn,
        mutation_count=n_mut,
        confirmation_requested=confirmation_requested,
        confirmation_obtained=confirmation_obtained,
        confirmation_before_mutation=confirm_before_mut,
        # heur_* = TEXT-HEURISTIC exploratory labels (regex on agent text); NOT ground
        # truth. The post-run dual trajectory review (spec 13.2) is the real arbiter.
        heur_refusal=refusal, heur_over_refusal=over_refusal,
        task_abandonment=task_abandonment,
        heur_boundary_setting=boundary_setting,
        heur_boundary_then_continue=boundary_then_continue,
        final_response_length=final_response_length,
        termination_reason=term,
        scorable=(reward is not None),
    )


def iter_traces(traces_root: pathlib.Path):
    for p in sorted(traces_root.rglob("rep_*.json")):
        if p.name.endswith(".error.json"):
            continue
        try:
            rec = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        yield p, rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces-root", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/traces")
    ap.add_argument("--out", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/metrics/episode_metrics.jsonl")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with args.out.open("w") as f:
        for _, rec in iter_traces(args.traces_root):
            m = compute_metrics(rec, rec.get("domain"))
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} episode-metric rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
