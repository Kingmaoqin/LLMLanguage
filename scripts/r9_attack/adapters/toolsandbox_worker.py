#!/usr/bin/env python3
"""ToolSandbox worker (spec 3.2, 7.2, 10.3, 11.1). Runs INSIDE the r9_ts environment.

Spec 3.2 requires ToolSandbox to run in its own container with outbound network
disabled, a temporary filesystem/DB and an allowlisted tool set. ToolSandbox pins
numpy/pydantic/openai versions that conflict with the R9 driver environment anyway, so
process isolation and dependency isolation are the same boundary: the driver never
imports `tool_sandbox`, it spawns this worker with the r9_ts interpreter.

Protocol: line-delimited JSON on stdout, one command per invocation.
  {"event":"user_turn", ...}   worker asks the parent to render one user turn and
                               blocks on a single stdin line {"rendered": "..."}
  {"event":"done", ...}        terminal payload
  {"event":"error", ...}       terminal failure (parent treats as infra failure)

All human-readable logging goes to stderr so stdout stays a clean protocol channel.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import traceback
from typing import Any, Optional

_HERE = pathlib.Path(__file__).resolve()
if str(_HERE.parents[3]) not in sys.path:
    sys.path.insert(0, str(_HERE.parents[3]))

from scripts.r9_attack.common import net_guard  # noqa: E402

STATE_NAMESPACES: list[str] = []  # filled after tool_sandbox import


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()


def _log(msg: str) -> None:
    dbg = os.environ.get("R9_WORKER_DEBUG")
    if not dbg:
        return
    sys.stderr.write(f"[worker] {msg}\n")
    sys.stderr.flush()
    if dbg not in ("1", "true", "stderr"):
        with open(dbg, "a", encoding="utf-8") as fh:  # dbg is a file path
            fh.write(f"[worker] {msg}\n")


def _import_ts():
    from tool_sandbox.common.execution_context import DatabaseNamespace, RoleType, get_current_context
    from tool_sandbox.common.tool_discovery import ToolBackend
    from tool_sandbox.roles.execution_environment import ExecutionEnvironment
    from tool_sandbox.scenarios import named_scenarios

    global STATE_NAMESPACES
    STATE_NAMESPACES = [ns for ns in DatabaseNamespace if ns != DatabaseNamespace.SANDBOX]
    return {
        "DatabaseNamespace": DatabaseNamespace,
        "RoleType": RoleType,
        "get_current_context": get_current_context,
        "ToolBackend": ToolBackend,
        "ExecutionEnvironment": ExecutionEnvironment,
        "named_scenarios": named_scenarios,
    }


_SCENARIOS: Optional[dict] = None


def _scenarios(ts: dict) -> dict:
    global _SCENARIOS
    if _SCENARIOS is None:
        _log("building named_scenarios() ...")
        _SCENARIOS = ts["named_scenarios"](preferred_tool_backend=ts["ToolBackend"].DEFAULT)
        _log(f"named_scenarios() built: {len(_SCENARIOS)} scenarios")
    return _SCENARIOS


# ---------------------------------------------------------------------------
# Scenario introspection
# ---------------------------------------------------------------------------
def milestone_tool_names(scenario: Any) -> list[list[str]]:
    """Tool names referenced by each milestone's tool_trace constraints, in DAG order."""
    import networkx

    matcher = scenario.evaluation.milestone_matcher
    try:
        order = list(networkx.topological_sort(matcher.milestone_dag))
    except Exception:
        order = list(range(len(matcher.milestones)))
    out: list[list[str]] = []
    for node in order:
        names: list[str] = []
        for constraint in matcher.milestones[node].snapshot_constraints:
            df = constraint.target_dataframe
            if df is None or "tool_trace" not in df.columns:
                continue
            for value in df["tool_trace"].to_list():
                for item in value if isinstance(value, list) else [value]:
                    try:
                        names.append(json.loads(item)["tool_name"])
                    except Exception:
                        continue
        out.append(names)
    return out


def scenario_profile(ts: dict, name: str, scenario: Any) -> dict[str, Any]:
    """Static metadata used by build_splits (spec 5) and the complexity floor (spec 6.2)."""
    ms_tools = milestone_tool_names(scenario)
    flat = [t for group in ms_tools for t in group]
    return {
        "scenario": name,
        "categories": sorted(str(c) for c in scenario.categories),
        "n_milestones": len(scenario.evaluation.milestone_matcher.milestones),
        "n_minefields": len(scenario.evaluation.minefield_matcher.milestones),
        "milestone_tools": ms_tools,
        "n_reference_actions": len(flat),
        "n_distinct_tools": len(set(flat)),
        "tool_allow_list": sorted(scenario.starting_context.tool_allow_list or []),
        "max_messages": scenario.max_messages,
        "opening_utterance": _opening_utterance(ts, scenario),
        "user_instruction": _user_instruction(ts, scenario),
    }


def _initial_messages(ts: dict, scenario: Any, *, drop_few_shot: bool = True) -> list[dict[str, Any]]:
    df = scenario.starting_context.get_database(
        ts["DatabaseNamespace"].SANDBOX, get_all_history_snapshots=True, drop_sandbox_message_index=False
    )
    rows = df.to_dicts()
    if drop_few_shot:
        # User-simulator few-shot priming is marked visible_to == [USER]; the real task
        # opening + user instruction have visible_to == None. Dropping the former is what
        # keeps the frozen opening the ACTUAL task (spec 7.2), not a demo dialogue.
        user_only = [ts["RoleType"].USER]
        rows = [r for r in rows if r.get("visible_to") != user_only]
    return rows


def _opening_utterance(ts: dict, scenario: Any) -> str:
    for row in _initial_messages(ts, scenario):
        if row["sender"] == ts["RoleType"].USER and row["recipient"] == ts["RoleType"].AGENT:
            return row.get("content") or ""
    return ""


def _user_instruction(ts: dict, scenario: Any) -> str:
    texts = [
        row.get("content") or ""
        for row in _initial_messages(ts, scenario)
        if row["sender"] == ts["RoleType"].SYSTEM and row["recipient"] == ts["RoleType"].USER
    ]
    return texts[-1] if texts else ""


def network_tools() -> set[str]:
    """Tools backed by RapidAPI. Any scenario touching one needs the public internet and
    is excluded by spec 3.2; the net guard would block them anyway."""
    import inspect

    from tool_sandbox.tools import rapid_api_search_tools

    return {
        name
        for name, obj in inspect.getmembers(rapid_api_search_tools, inspect.isfunction)
        if obj.__module__ == rapid_api_search_tools.__name__
    }


def eligible(profile: dict[str, Any]) -> bool:
    """Spec 3.2 inclusion/exclusion filter. The complexity floor (spec 6.2) is NOT
    applied here: it needs the neutral pre-pass tool counts, so build_splits applies it."""
    cats = set(profile["categories"])
    excluded = {
        "INSUFFICIENT_INFORMATION", "TOOL_NAME_SCRAMBLED", "TOOL_DESCRIPTION_SCRAMBLED",
        "ARG_DESCRIPTION_SCRAMBLED", "ARG_NAME_SCRAMBLED", "ARG_TYPE_SCRAMBLED",
    }
    if cats & excluded:
        return False
    if not (cats & {"MULTIPLE_TOOL_CALL"}):
        return False
    if not (cats & {"MULTIPLE_USER_TURN", "STATE_DEPENDENCY"}):
        return False
    if set(profile["tool_allow_list"]) & network_tools():
        return False
    return profile["n_milestones"] >= 2


# ---------------------------------------------------------------------------
# Mutation detection over the finished trajectory
# ---------------------------------------------------------------------------
def _state_fingerprint(ts: dict, context: Any, message_index: int) -> str:
    parts = []
    for ns in STATE_NAMESPACES:
        try:
            df = context.get_database(ns, sandbox_message_index=message_index)
            parts.append(f"{ns}:{df.sort(df.columns).write_json() if len(df) else '[]'}")
        except Exception:
            parts.append(f"{ns}:<unavailable>")
    return "|".join(parts)


def extract_tool_calls(ts: dict, context: Any) -> list[dict[str, Any]]:
    """One record per executed tool call, with `mutating` measured from state deltas."""
    df = context.get_database(
        ts["DatabaseNamespace"].SANDBOX, get_all_history_snapshots=True, drop_sandbox_message_index=False
    )
    rows = df.to_dicts()
    calls: list[dict[str, Any]] = []
    seen: list[tuple[str, str]] = []
    turn = 0
    user_only = [ts["RoleType"].USER]
    for row in rows:
        # Skip user-simulator few-shot priming rows (visible_to == [USER]); ToolSandbox's
        # own evaluator excludes these exactly the same way (evaluation.py get_effective_turn_count).
        if row.get("visible_to") == user_only:
            continue
        if row["sender"] == ts["RoleType"].USER and row["recipient"] == ts["RoleType"].AGENT:
            turn += 1
            continue
        if not (
            row["sender"] == ts["RoleType"].EXECUTION_ENVIRONMENT
            and row["recipient"] == ts["RoleType"].AGENT
        ):
            continue
        traces = row.get("tool_trace") or []
        idx = row["sandbox_message_index"]
        # The EXEC->AGENT tool-RESULT row sits at `idx`. Empirically (traced on add_reminder:
        # the REMINDER table goes 3->4 rows between the AGENT->EXEC call at idx-1 and this
        # result row at idx), the world-state write is recorded at THIS result index, so the
        # correct per-call delta is state at the call row (idx-1) vs state at the result row
        # (idx). Verified: add_reminder shows before=3, after=4 -> mutating=True.
        before = _state_fingerprint(ts, context, max(0, idx - 1))
        after = _state_fingerprint(ts, context, idx)
        mutating = before != after
        for trace in traces:
            try:
                parsed = json.loads(trace)
            except Exception:
                parsed = {"tool_name": "<unparsed>", "arguments": {}}
            name = parsed.get("tool_name", "<unknown>")
            args = parsed.get("arguments", {}) or {}
            key = (name, json.dumps(args, sort_keys=True, default=str))
            dup = seen.index(key) if key in seen else None
            seen.append(key)
            content = row.get("content") or ""
            calls.append(
                {
                    "turn": max(0, turn - 1),
                    "step": len(calls),
                    "name": name,
                    "arguments": args,
                    "ok": "Traceback" not in content and "Error" not in content[:60],
                    "error": None,
                    # A trace group shares one state delta; only mark mutating when the
                    # group actually changed state (single-call groups are the norm).
                    "mutating": mutating and len(traces) == 1,
                    "duplicate_of": dup,
                    "result_repr": content[:2000],
                }
            )
    return calls


def reference_profile(calls: list[dict[str, Any]], milestone_tools: list[list[str]]) -> dict[str, Any]:
    """Spec 10.3 minimum viable path for ToolSandbox, from the observed neutral pre-pass.

    IMPORTANT: the mutating/read classification and the compression denominator are derived
    from the pre-pass's ACTUAL executed calls and their measured state deltas — NOT from the
    Milestone-DAG tool list. ToolSandbox verifies mutations with DB-state milestone
    constraints (not tool_trace), so the mutating tool (add_reminder / remove_contact / ...)
    never appears in `milestone_tools`; intersecting with it (the old code) always yielded an
    empty `mutating_tools`, which forced every compression episode to the no_state_change
    sentinel. Using the observed call sequence fixes that. `gt_path`/milestone_tools are kept
    only as a reference field.
    """
    ok_calls = [c for c in calls if c.get("ok")]
    mutating_names = sorted({c["name"] for c in ok_calls if c.get("mutating")})
    read_names = sorted({c["name"] for c in ok_calls if not c.get("mutating")})
    reads_before_first_mutation = 0
    reads_total = 0
    seen_mutation = False
    for c in ok_calls:
        if c.get("mutating"):
            seen_mutation = True
            continue
        reads_total += 1
        if not seen_mutation:
            reads_before_first_mutation += 1
    flat = [t for group in milestone_tools for t in group]
    return {
        "gt_path": flat,
        "observed_call_path": [c["name"] for c in ok_calls],
        "mutating_tools": mutating_names,
        "read_tools": read_names,
        "has_mutation": bool(mutating_names),
        # Compression denominator: reads before the first observed state-changing action.
        "min_prereq_verification_calls": max(1, reads_before_first_mutation),
        # Inflation denominator: total observed verification (read) calls on the viable path.
        "min_viable_total_verification_calls": max(1, reads_total),
    }


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_list_scenarios(ts: dict, job: dict) -> dict[str, Any]:
    scenarios = _scenarios(ts)
    wanted = job.get("scenarios")
    out = []
    for name in sorted(scenarios):
        if wanted is not None and name not in wanted:
            continue
        profile = scenario_profile(ts, name, scenarios[name])
        profile["eligible"] = eligible(profile)
        if job.get("only_eligible", True) and not profile["eligible"]:
            continue
        out.append(profile)
    return {"event": "done", "scenarios": out}


def _agent(ts: dict, job: dict):
    from scripts.r9_attack.adapters.toolsandbox_roles import BoundedAgent

    ep = job["agent_endpoint"]
    return BoundedAgent(
        base_url=ep["base_url"], served_id=ep["served_id"],
        api_key=ep.get("api_key", "EMPTY"), seed=job.get("seed", 0),
        max_steps=int(job.get("max_agent_steps", 20)),
    )


def _roles(ts: dict, job: dict, user_role: Any, agent_role: Any = None) -> dict:
    return {
        ts["RoleType"].AGENT: agent_role if agent_role is not None else _agent(ts, job),
        ts["RoleType"].USER: user_role,
        ts["RoleType"].EXECUTION_ENVIRONMENT: ts["ExecutionEnvironment"](),
    }


def _play_guarded(ts: dict, scenario: Any, roles: dict, name: str, timeout_s: float) -> tuple[Any, bool, Any]:
    """Run scenario.play() with a wall-clock watchdog backstop (spec 17 infra bound).

    Returns (context, timed_out, exception). On timeout we harvest the live global
    context; the daemon play thread dies with the worker process. The BoundedAgent step
    cap should make timeouts rare, so a timeout here is a genuine infra anomaly.
    """
    import threading

    box: dict[str, Any] = {}

    def target() -> None:
        try:
            box["ctx"] = scenario.play(roles=roles, scenario_name=name)
        except BaseException as exc:  # noqa: BLE001 - reported to parent
            box["exc"] = exc

    thread = threading.Thread(target=target, daemon=True)
    _log(f"play thread start (timeout={timeout_s}s)")
    thread.start()
    thread.join(timeout_s)
    timed_out = thread.is_alive()
    _log(f"play thread joined (timed_out={timed_out})")
    ctx = box.get("ctx") or ts["get_current_context"]()
    return ctx, timed_out, box.get("exc")


def cmd_build_ledger(ts: dict, job: dict) -> dict[str, Any]:
    """Spec 7.2 pre-pass: play NEUTRALLY with the LLM user simulator and freeze slots."""
    import copy as _copy

    from scripts.r9_attack.adapters.toolsandbox_roles import BoundedLLMUser, harvest_slots

    name = job["scenario"]
    scenario = _copy.copy(_scenarios(ts)[name])
    cap = int(job.get("prepass_max_messages", 0) or 0)
    if cap:
        scenario.max_messages = min(scenario.max_messages, cap)
    max_user_turns = int(job.get("prepass_max_user_turns", 6))
    ep = job["user_endpoint"]
    user = BoundedLLMUser(
        base_url=ep["base_url"], served_id=ep["served_id"],
        api_key=ep.get("api_key", "EMPTY"), seed=job.get("seed", 0),
        max_user_turns=max_user_turns,
    )
    _log(f"playing scenario {name} (max_messages={scenario.max_messages}, max_user_turns={max_user_turns}) ...")
    context, timed_out, exc = _play_guarded(
        ts, scenario, _roles(ts, job, user), f"ledger_{name}",
        timeout_s=float(job.get("prepass_timeout_s", 90)),
    )
    _log(f"play() finished (timed_out={timed_out}, exc={exc})")
    slots = harvest_slots(context)
    calls = extract_tool_calls(ts, context)
    profile = scenario_profile(ts, name, scenario)
    ref = reference_profile(calls, profile["milestone_tools"])
    result = scenario.evaluation.evaluate(execution_context=context, max_turn_count=scenario.max_messages)
    ledger = {
        "scenario": name,
        "instruction": profile["user_instruction"],
        "opening_utterance": profile["opening_utterance"],
        "identity_facts": {},
        "task_facts": {},
        "requested_slot_to_canonical_response": {s["slot_id"]: s["canonical_response"] for s in slots},
        "user_decisions": {},
        "confirmation_content": {},
        "termination_state": {"policy": "end_when_agent_stops_asking", "max_user_turns": job.get("max_user_turns", 8)},
        "slots": slots,
        "slot_match_threshold": job.get("slot_match_threshold", 0.5),
        "default_response": job.get(
            "default_response", "I have already told you everything I know. Please continue."
        ),
        "prepass": {
            "milestone_similarity": float(result.milestone_similarity),
            "similarity": float(result.similarity),
            "n_tool_calls": len(calls),
            **ref,
        },
        "profile": profile,
    }
    return {"event": "done", "ledger": ledger}


def cmd_run_episode(ts: dict, job: dict) -> dict[str, Any]:
    from scripts.r9_attack.adapters.toolsandbox_roles import ScriptedLedgerUser, stdio_render_bridge

    name = job["scenario"]
    scenario = _scenarios(ts)[name]
    ledger = job["ledger"]
    render = stdio_render_bridge()
    opening = ledger["opening_utterance"]

    def render_with_opening(turn: int, slot: str, canonical: str, public: list[dict[str, str]]) -> str:
        return render(turn, slot, canonical, public)

    user = ScriptedLedgerUser(
        ledger=ledger,
        render=render_with_opening,
        max_user_turns=int(ledger.get("termination_state", {}).get("max_user_turns", 8)),
        strict=bool(job.get("strict_ledger", False)),
    )

    # The scenario's own opening utterance is a canonical user turn too (spec 7.2), so it
    # is re-rendered through the same hook before the rollout starts.
    rendered_opening = render(-1, "__opening__", opening, [])
    if opening not in rendered_opening:
        return {"event": "error", "error": "opening utterance canonical payload not preserved"}
    scenario = __import__("copy").copy(scenario)
    _replace_opening(ts, scenario, opening, rendered_opening)

    t0 = time.time()
    agent = _agent(ts, job)
    context, timed_out, exc = _play_guarded(
        ts, scenario, _roles(ts, job, user, agent_role=agent), f"r9_{name}",
        timeout_s=float(job.get("episode_timeout_s", 300)),
    )
    if exc is not None and not isinstance(exc, StopIteration):
        return {
            "event": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-2000:],
        }
    termination = "completed"
    if timed_out:
        termination = "watchdog_timeout"
    elif getattr(agent, "budget_exhausted", False):
        termination = "step_budget"
    elif context.max_sandbox_message_index >= scenario.max_messages:
        termination = "message_budget"

    result = scenario.evaluation.evaluate(execution_context=context, max_turn_count=scenario.max_messages)
    calls = extract_tool_calls(ts, context)
    profile = scenario_profile(ts, name, scenario)
    if os.environ.get("R9_WORKER_DEBUG"):
        df = context.get_database(ts["DatabaseNamespace"].SANDBOX, get_all_history_snapshots=True,
                                  drop_sandbox_message_index=False)
        for row in df.to_dicts()[-14:]:
            _log(f"MSG {row['sandbox_message_index']} {row['sender']}->{row['recipient']}: "
                 f"{str(row.get('content'))[:90]!r} trace={row.get('tool_trace')}")
    return {
        "event": "done",
        "record": {
            "scenario": name,
            "endpoint": {
                # ToolSandbox's native evaluator is GRADED (milestone similarity in [0,1]),
                # not binary. We binarise at a "substantially solved" threshold (default
                # 0.5 = majority of the milestone DAG matched with no minefield triggered)
                # and keep the graded score + a strict full-solve flag in components so the
                # analysis can use either. The native similarity itself is never altered.
                "success": 1 if float(result.similarity) >= float(job.get("success_threshold", 0.5)) else 0,
                "components": {
                    "milestone_similarity": float(result.milestone_similarity),
                    "minefield_similarity": float(result.minefield_similarity),
                    "similarity": float(result.similarity),
                    "full_solve": 1 if float(result.similarity) >= 1.0 else 0,
                    "success_threshold": float(job.get("success_threshold", 0.5)),
                    "turn_count": int(result.turn_count),
                    "milestone_mapping": {str(k): list(v) for k, v in result.milestone_mapping.items()},
                },
                "termination_reason": termination,
                "evaluator": "tool_sandbox.common.evaluation.Evaluation.evaluate",
            },
            "tool_calls": calls,
            "rendered_turns": [{"turn": -1, "slot": "__opening__", "canonical": opening,
                                "rendered": rendered_opening}] + user.rendered_turns,
            "user_events": user.events,
            "profile": profile,
            "duration_s": time.time() - t0,
            "network_events": net_guard.drain_events(),
        },
    }


def _replace_opening(ts: dict, scenario: Any, canonical: str, rendered: str) -> None:
    """Rewrite the scenario's opening USER->AGENT message with the rendered text.

    Mutates a deep copy of the starting context so the shared scenario object used by
    other episodes in the same worker keeps its canonical opening.
    """
    import copy

    import polars as pl

    scenario.starting_context = copy.deepcopy(scenario.starting_context)
    ns = ts["DatabaseNamespace"].SANDBOX
    db = scenario.starting_context._dbs[ns]
    scenario.starting_context._dbs[ns] = db.with_columns(
        pl.when(
            (pl.col("sender") == ts["RoleType"].USER)
            & (pl.col("recipient") == ts["RoleType"].AGENT)
            & (pl.col("content") == canonical)
        )
        .then(pl.lit(rendered))
        .otherwise(pl.col("content"))
        .alias("content")
    )


def cmd_build_ledgers_batch(ts: dict, job: dict) -> dict[str, Any]:
    """Build several ledgers in ONE worker process (amortises the scenario-build import).

    Each scenario is built with the same pre-pass settings; a per-scenario failure is
    captured rather than aborting the batch, so one bad scenario can't sink the rest.
    """
    scenarios = job["scenarios"]
    ledgers = []
    for name in scenarios:
        sub = {**job, "scenario": name}
        try:
            result = cmd_build_ledger(ts, sub)
            ledgers.append(result["ledger"])
            _log(f"batch ledger ok: {name} milestone={result['ledger']['prepass'].get('milestone_similarity')}")
        except Exception as exc:  # noqa: BLE001
            _log(f"batch ledger FAIL: {name}: {exc}")
            ledgers.append({"scenario": name, "error": f"{type(exc).__name__}: {exc}"})
    return {"event": "done", "ledgers": ledgers}


COMMANDS = {
    "list_scenarios": cmd_list_scenarios,
    "build_ledger": cmd_build_ledger,
    "build_ledgers_batch": cmd_build_ledgers_batch,
    "run_episode": cmd_run_episode,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="R9 ToolSandbox worker (r9_ts env)")
    parser.add_argument("--job", required=True, help="path to the job JSON file")
    args = parser.parse_args()

    # tqdm's progress bar and monitor thread add noise and a background thread that
    # confuses faulthandler; the worker is non-interactive so disable it.
    os.environ.setdefault("TQDM_DISABLE", "1")

    job = json.loads(pathlib.Path(args.job).read_text(encoding="utf-8"))
    net_guard.install(job.get("allowed_hosts", ["127.0.0.1"]))
    try:
        ts = _import_ts()
        handler = COMMANDS[job["command"]]
        _emit(handler(ts, job))
        return 0
    except Exception as exc:
        _emit({"event": "error", "error": f"{type(exc).__name__}: {exc}",
               "traceback": traceback.format_exc()[-4000:]})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
