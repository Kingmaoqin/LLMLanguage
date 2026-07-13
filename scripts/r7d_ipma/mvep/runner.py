#!/usr/bin/env python3
"""Sealed MVEP runner: 3 liveness calls plus exactly 8 fixed trajectories."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from openai import OpenAI
from transformers import AutoTokenizer

from scripts.r7d_ipma.mvep.evaluator import evaluate_trace
from scripts.r7d_ipma.mvep.junction import assert_valid_junction
from scripts.r7d_ipma.mvep.trace_store import (
    TraceStore, canonical_json, sha256_value, trace_complete,
)
from scripts.r7d_ipma.step2_1.official_scorer import official_reward
from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage
from tau2.evaluator.evaluator import EvaluationType
from tau2.run import get_tasks


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "data/r7d_ipma/mvep/frozen_fixtures_v1.json"
MUTATION_TOOLS = {
    "cancel_pending_order", "exchange_delivered_order_items",
    "modify_pending_order_address", "modify_pending_order_items",
    "modify_pending_order_payment", "modify_user_address",
    "return_delivered_order_items",
}
ENDPOINTS = {
    "gemma4_31b": {"base_url": "http://127.0.0.1:8005/v1", "served": "g4-v2-1"},
    "gpt_oss_120b": {"base_url": "http://127.0.0.1:8192/v1", "served": "gpt-oss"},
    "mistral_small_3p2": {"base_url": "http://127.0.0.1:8007/v1", "served": "mistral-small-3p2"},
}
MODEL_PATH = "/home/xqin5/hf_p08_models/gpt-oss-120b"
PARAMS = {"temperature": 0.0, "top_p": 1.0, "seed": 20260712,
          "max_tokens": 1024, "timeout_seconds": 90, "retry_policy": "zero_retry"}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def get_env(domain: str):
    mod = __import__(f"tau2.domains.{domain}.environment", fromlist=["get_environment"])
    return mod.get_environment()


def db_snapshot(env) -> dict[str, Any]:
    return env.tools.db.model_dump(mode="json")


def openai_tool_message(tc: ToolCall) -> dict[str, Any]:
    return {"role": "assistant", "content": "", "tool_calls": [{
        "id": tc.id, "type": "function",
        "function": {"name": tc.name, "arguments": canonical_json(tc.arguments)},
    }]}


def openai_assistant_message(message: Any) -> dict[str, Any]:
    """Serialize a model response for the next OpenAI-compatible request.

    Tool-call responses commonly carry ``content=None``.  The frozen gpt-oss
    template treats a present content field as text, so preserve the absence of
    text as the protocol-equivalent empty string before the next render.
    """
    payload = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        payload["tool_calls"] = [item.model_dump(mode="json")
                                 for item in message.tool_calls]
    return payload


def prefix_for_fixture(env, task, fixture: dict[str, Any]):
    api_messages: list[dict[str, Any]] = [
        {"role": "system", "content": env.get_policy()},
        {"role": "user", "content": fixture["opening"]},
    ]
    tau_messages: list[Any] = [UserMessage(role="user", content=fixture["opening"])]
    observations, flat_calls, flat_responses = [], [], []
    for position, action_index in enumerate(fixture["prefix_action_indexes"]):
        action = task.evaluation_criteria.actions[action_index]
        tc = ToolCall(id=f"prefix-{position}", name=action.name,
                      arguments=copy.deepcopy(action.arguments), requestor="assistant")
        assistant = AssistantMessage(role="assistant", content=None, tool_calls=[tc])
        response = env.get_response(tc)
        tau_messages.extend([assistant, response])
        api_messages.extend([
            openai_tool_message(tc),
            {"role": "tool", "tool_call_id": tc.id, "content": str(response.content)},
        ])
        call = {"id": tc.id, "name": tc.name, "arguments": tc.arguments,
                "target": tc.arguments, "mutating": tc.name in MUTATION_TOOLS,
                "source": "deterministic_prefix"}
        resp = response.model_dump(mode="json")
        flat_calls.append(call); flat_responses.append(resp)
        observations.append({
            "event_id": tc.id,
            "evidence_id": f"{fixture['fixture_id']}:{action.action_id}",
            "tool_name": tc.name,
            "arguments_hash": sha256_value(tc.arguments),
            "response_hash": sha256_value(resp),
        })
    remaining = []
    for action_index in fixture["remaining_action_indexes"]:
        action = task.evaluation_criteria.actions[action_index]
        remaining.append({
            "required_action_id": action.action_id,
            "tool_name": action.name,
            "target_binding": canonical_json(action.arguments),
            "reason": "frozen task-required action/evidence",
        })
    proof = {
        "task_kind": fixture["task_kind"], "label": fixture["junction_label"],
        "junction_id": fixture["junction_id"],
        "junction_after_event_id": observations[-1]["event_id"],
        "recorded_observations": observations,
        "remaining_required_path": remaining,
        "suffix_required": True, "mutation_consumed": False,
        "confirmation_consumed": False, "confirmation_asked": False,
    }
    assert_valid_junction(proof)
    return api_messages, tau_messages, observations, flat_calls, flat_responses, proof


class Caller:
    def __init__(self, tokenizer, store: TraceStore):
        self.tokenizer = tokenizer
        self.store = store
        self.usage = []
        self.rendered = []
        self.assistant = []
        self.tool_token_texts = []

    def call(self, *, base_url: str, model: str, messages: list[dict[str, Any]],
             tools: list[dict[str, Any]] | None, role: str):
        try:
            rendered = self.tokenizer.apply_chat_template(
                messages, tools=tools or None, tokenize=False, add_generation_prompt=True,
            )
        except Exception as exc:
            self.store.append("CALL_EXCEPTION", {
                "role": role, "stage": "request_render", "type": type(exc).__name__,
                "message": str(exc), "attempt": 0, "request_sent": False,
                "messages": messages, "tools": tools or [],
                "unrendered_input_hash": sha256_value({"messages": messages,
                                                         "tools": tools or []}),
            })
            raise
        prepared = {"role": role, "endpoint": base_url, "served_model": model,
                    "messages": messages, "tools": tools or [], "rendered": rendered,
                    "input_hash": hashlib.sha256(rendered.encode()).hexdigest(),
                    "parameters": PARAMS, "prepared_at": utc_now()}
        self.store.append("CALL_PREPARED", prepared)
        start_wall, start = utc_now(), time.perf_counter()
        try:
            client = OpenAI(base_url=base_url, api_key="EMPTY", max_retries=0,
                            timeout=PARAMS["timeout_seconds"])
            response = client.chat.completions.create(
                model=model, messages=messages, tools=tools or None,
                temperature=PARAMS["temperature"], top_p=PARAMS["top_p"],
                seed=PARAMS["seed"], max_tokens=PARAMS["max_tokens"],
            )
        except Exception as exc:
            self.store.append("CALL_EXCEPTION", {"role": role, "type": type(exc).__name__,
                                                   "message": str(exc), "attempt": 1})
            raise
        latency = round((time.perf_counter() - start) * 1000, 3)
        raw = response.model_dump(mode="json")
        self.store.append("CALL_RESPONSE", {"role": role, "response": raw,
                                             "start": start_wall, "end": utc_now(),
                                             "latency_ms": latency, "attempt": 1})
        message = response.choices[0].message
        assistant = message.model_dump(mode="json")
        assistant["mvep_role"] = role
        self.rendered.append(rendered); self.assistant.append(assistant)
        self.usage.append({"role": role, "server": response.usage.model_dump() if response.usage else None,
                           "input_local": len(self.tokenizer.encode(rendered)),
                           "output_local": len(self.tokenizer.encode(canonical_json(assistant))),
                           "latency_ms": latency, "start": start_wall, "end": utc_now()})
        return message


def run_trajectory(fixture, architecture, condition, run_root, manifest_hash,
                   environment_hash, tokenizer, tokenizer_hash, code_hashes,
                   incident_recovery: bool = False):
    identity = {"trajectory_id": f"{fixture['fixture_id']}__{architecture}__{condition}",
                "task_id": fixture["task_id"], "domain": fixture["domain"],
                "task_kind": fixture["task_kind"], "architecture": architecture,
                "condition": condition, "junction_id": fixture["junction_id"]}
    trajectory_root = run_root / identity["trajectory_id"]
    if trajectory_root.exists():
        if not incident_recovery:
            raise FileExistsError(trajectory_root)
        if (trajectory_root / "raw_trace.json").exists():
            raise RuntimeError("completed_trajectory_cannot_be_replaced")
        old = TraceStore.recover(trajectory_root, "v1.0.2_render_incident")
        old.terminal("ABORTED-PRE-MODEL-CALL-RENDER")
        trajectory_root = run_root / f"{identity['trajectory_id']}__attempt2"
    store = TraceStore.create(trajectory_root, identity, manifest_hash)
    start_wall, start = utc_now(), time.perf_counter()
    env = get_env(fixture["domain"])
    fresh = get_env(fixture["domain"])
    initial_hash = env.get_db_hash()
    fresh_reset = fresh.get_db_hash() == initial_hash
    tasks = {str(task.id): task for task in get_tasks(fixture["domain"])}
    task = tasks[fixture["task_id"]]
    api_messages, tau_messages, observations, calls, responses, proof = prefix_for_fixture(
        env, task, fixture)
    store.append("PREFIX_CAPTURED", {"messages": api_messages, "observations": observations,
                                      "db_hash": env.get_db_hash()})
    store.append("JUNCTION_PROOF", proof)
    turn = fixture[f"{condition}_turn"]
    api_messages.append({"role": "user", "content": turn})
    tau_messages.append(UserMessage(role="user", content=turn))
    caller = Caller(tokenizer, store)
    caller.tool_token_texts.extend(str(item.get("content") or "") for item in responses)
    endpoint = ENDPOINTS["gpt_oss_120b"]
    if architecture == "mas":
        coordinator_messages = [
            {"role": "system", "content": "You are a read-only coordinator. Give the executor a concise plan. You have no tools and must not claim completion."},
            *api_messages,
        ]
        advisory = caller.call(base_url=endpoint["base_url"], model=endpoint["served"],
                               messages=coordinator_messages, tools=None, role="mas_coordinator")
        api_messages.append({"role": "system", "content": "Read-only coordinator advisory: " + (advisory.content or "")})
    tools = [tool.openai_schema for tool in env.get_tools()]
    final_text = ""
    for turn_index in range(4):
        message = caller.call(base_url=endpoint["base_url"], model=endpoint["served"],
                              messages=api_messages, tools=tools, role="executor")
        tool_calls = message.tool_calls or []
        api_messages.append(openai_assistant_message(message))
        tau_calls = []
        for tc in tool_calls:
            args = json.loads(tc.function.arguments)
            tau_tc = ToolCall(id=tc.id, name=tc.function.name, arguments=args,
                              requestor="assistant")
            tau_calls.append(tau_tc)
            call = {"id": tc.id, "name": tc.function.name, "arguments": args,
                    "target": args, "mutating": tc.function.name in MUTATION_TOOLS,
                    "source": "model_suffix"}
            calls.append(call)
        tau_assistant = AssistantMessage(role="assistant", content=message.content,
                                         tool_calls=tau_calls or None)
        tau_messages.append(tau_assistant)
        if not tool_calls:
            final_text = message.content or ""
            break
        for tau_tc in tau_calls:
            response = env.get_response(tau_tc)
            tau_messages.append(response)
            payload = response.model_dump(mode="json")
            responses.append(payload)
            api_tool = {"role": "tool", "tool_call_id": tau_tc.id,
                        "content": str(response.content)}
            api_messages.append(api_tool)
            caller.tool_token_texts.append(api_tool["content"])
            store.append("TOOL_RESPONSE", {"call_id": tau_tc.id, "tool_name": tau_tc.name,
                                            "arguments": tau_tc.arguments, "response": payload,
                                            "db_hash_after": env.get_db_hash()})
    post_snapshot = db_snapshot(env); post_hash = env.get_db_hash()
    official = None
    if fixture["task_kind"] == "write":
        reward = official_reward(tau_messages, task, fixture["domain"], EvaluationType.ENV)
        official = {"reward": reward.reward,
                    "db_match": getattr(reward.db_check, "db_match", None),
                    "components": reward.model_dump(mode="json")}
    preliminary = {
        "schema_version": "r7d-mvep-raw-trace-v1", "identity": identity,
        "manifest_hash": manifest_hash, "environment_lock_hash": environment_hash,
        "rendered_messages": caller.rendered, "input_hash": sha256_value(caller.rendered),
        "assistant_messages": caller.assistant, "tool_calls": calls,
        "tool_responses": responses,
        "db": {"pre_snapshot": db_snapshot(fresh), "pre_hash": initial_hash,
               "post_snapshot": post_snapshot, "post_hash": post_hash,
               "fresh_reset": fresh_reset},
        "scorer": {},
        "tokens": {"input": sum(item["input_local"] for item in caller.usage),
                   "output": sum(item["output_local"] for item in caller.usage),
                   "tool": sum(len(tokenizer.encode(text)) for text in caller.tool_token_texts),
                   "total": 0, "tokenizer_hash": tokenizer_hash,
                   "per_call": caller.usage},
        "timing": {"start": start_wall, "end": utc_now(),
                   "latency_ms": round((time.perf_counter() - start) * 1000, 3)},
        "retry": {"policy": "zero_retry", "attempts": len(caller.usage),
                  "silent_retry": False, "exceptions": []},
        "code_environment_model_hashes": code_hashes,
        "junction_proof": proof,
        "conversation": api_messages,
        "required_communication": fixture["required_communication"],
        "official_env": official,
        "final_assistant_text": final_text,
    }
    preliminary["tokens"]["total"] = (preliminary["tokens"]["input"]
                                         + preliminary["tokens"]["output"]
                                         + preliminary["tokens"]["tool"])
    expected = []
    for index in fixture["prefix_action_indexes"]:
        action = task.evaluation_criteria.actions[index]
        expected.append({"name": action.name, "arguments": action.arguments,
                         "target": action.arguments, "mutating": action.name in MUTATION_TOOLS})
    if condition == "positive_control":
        expected.append({"name": fixture["positive_control_extra_tool"],
                         "arguments": fixture["positive_control_extra_arguments"],
                         "target": fixture["positive_control_extra_arguments"], "mutating": False})
    for index in fixture["remaining_action_indexes"]:
        action = task.evaluation_criteria.actions[index]
        expected.append({"name": action.name, "arguments": action.arguments,
                         "target": action.arguments, "mutating": action.name in MUTATION_TOOLS})
    preliminary["expected_actions"] = expected
    preliminary["scorer"] = evaluate_trace(
        preliminary, expected, mutation_tools=MUTATION_TOOLS,
        official_env=official, required_communication=fixture["required_communication"])
    store.append("SCORER_RESULT", preliminary["scorer"])
    complete, missing = trace_complete(preliminary)
    if not complete:
        raise RuntimeError("incomplete_trace:" + ",".join(missing))
    store.materialize(preliminary); store.terminal("CAPTURED")
    return preliminary


def liveness_call(alias: str, store_root: Path, manifest_hash: str) -> dict[str, Any]:
    endpoint = ENDPOINTS[alias]
    store = TraceStore.create(store_root / f"liveness__{alias}",
                              {"call_type": "endpoint_liveness", "alias": alias},
                              manifest_hash)
    request = {"model": endpoint["served"],
               "messages": [{"role": "user", "content": "Reply exactly: MVEP_LIVE"}],
               "temperature": 0, "top_p": 1, "seed": PARAMS["seed"],
               "max_tokens": 16, "retry": "zero_retry"}
    store.append("CALL_PREPARED", {"endpoint": endpoint["base_url"], "request": request,
                                    "request_hash": sha256_value(request), "prepared_at": utc_now()})
    start = time.perf_counter()
    client = OpenAI(base_url=endpoint["base_url"], api_key="EMPTY", max_retries=0,
                    timeout=PARAMS["timeout_seconds"])
    try:
        response = client.chat.completions.create(**{key: value for key, value in request.items()
                                                     if key != "retry"})
    except Exception as exc:
        store.append("CALL_EXCEPTION", {"type": type(exc).__name__, "message": str(exc),
                                         "attempt": 1})
        store.terminal("FAILED")
        raise
    raw = response.model_dump(mode="json")
    store.append("CALL_RESPONSE", {"response": raw, "attempt": 1,
                                    "latency_ms": round((time.perf_counter() - start) * 1000, 3)})
    store.terminal("CAPTURED")
    return {"alias": alias, "served": endpoint["served"],
            "response": response.choices[0].message.content,
            "usage": response.usage.model_dump() if response.usage else None,
            "latency_ms": round((time.perf_counter() - start) * 1000, 3)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--environment-lock", type=Path, required=True)
    parser.add_argument("--incident-recovery-v1-0-2", action="store_true")
    args = parser.parse_args()
    args.run_root.parent.mkdir(parents=True, exist_ok=True)
    if args.incident_recovery_v1_0_2:
        if not args.run_root.is_dir():
            raise RuntimeError("incident_recovery_requires_existing_root")
    else:
        args.run_root.mkdir(parents=False, exist_ok=False)
    manifest_hash = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    environment_hash = hashlib.sha256(args.environment_lock.read_bytes()).hexdigest()
    frozen = json.loads(FIXTURES.read_text())
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    environment = json.loads(args.environment_lock.read_text())
    tokenizer_hash = environment["models"]["gpt_oss_120b"]["tokenizer_sha256"]
    code_hashes = {"manifest": manifest_hash, "environment": environment_hash,
                   "git_commit": environment["git"]["code_commit"]}
    if args.incident_recovery_v1_0_2:
        liveness = json.loads((args.run_root / "endpoint_liveness.json").read_text())
        if len(liveness) != 3:
            raise RuntimeError("incident_liveness_ledger_invalid")
        for alias in ENDPOINTS:
            events = TraceStore.read_and_validate(args.run_root / f"liveness__{alias}")
            if events[-1]["event"] != "TERMINAL" or events[-1]["payload"]["status"] != "CAPTURED":
                raise RuntimeError("incident_liveness_trace_not_terminal")
    else:
        liveness = [liveness_call(alias, args.run_root, manifest_hash) for alias in ENDPOINTS]
        (args.run_root / "endpoint_liveness.json").write_text(
            json.dumps(liveness, indent=2, ensure_ascii=False))
    rows = []
    for fixture in frozen["fixtures"]:
        for architecture in frozen["architectures"]:
            for condition in frozen["conditions"]:
                rows.append(run_trajectory(
                    fixture, architecture, condition, args.run_root, manifest_hash,
                    environment_hash, tokenizer, tokenizer_hash, code_hashes,
                    incident_recovery=args.incident_recovery_v1_0_2))
    (args.run_root / "run_summary.json").write_text(json.dumps({
        "liveness_calls": len(liveness), "trajectories": len(rows),
        "attack_conditions": 0, "effect_estimated": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
