#!/usr/bin/env python3
"""Two-pass deterministic replay of sealed MVEP traces; no model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer

from scripts.r7d_ipma.mvep.evaluator import evaluate_trace
from scripts.r7d_ipma.mvep.runner import MODEL_PATH, MUTATION_TOOLS, get_env
from scripts.r7d_ipma.mvep.trace_store import canonical_json, sha256_value
from scripts.r7d_ipma.step2_1.official_scorer import official_reward
from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage
from tau2.evaluator.evaluator import EvaluationType
from tau2.run import get_tasks


def reconstruct(trace: dict[str, Any]):
    env = get_env(trace["identity"]["domain"])
    messages = []
    for item in trace["conversation"]:
        role = item.get("role")
        if role == "system" or role == "tool":
            continue
        if role == "user":
            messages.append(UserMessage(role="user", content=item.get("content")))
            continue
        if role != "assistant":
            raise ValueError("unknown_conversation_role")
        calls = []
        for raw in item.get("tool_calls") or []:
            function = raw["function"]
            arguments = function["arguments"]
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            calls.append(ToolCall(id=raw["id"], name=function["name"],
                                  arguments=arguments, requestor="assistant"))
        messages.append(AssistantMessage(role="assistant", content=item.get("content"),
                                         tool_calls=calls or None))
        for call in calls:
            messages.append(env.get_response(call))
    return env, messages


def replay_once(path: Path, tokenizer) -> dict[str, Any]:
    trace = json.loads(path.read_text())
    env, messages = reconstruct(trace)
    task = next(task for task in get_tasks(trace["identity"]["domain"])
                if str(task.id) == trace["identity"]["task_id"])
    official = None
    if trace["identity"]["task_kind"] == "write":
        reward = official_reward(messages, task, trace["identity"]["domain"], EvaluationType.ENV)
        official = {"reward": reward.reward,
                    "db_match": getattr(reward.db_check, "db_match", None),
                    "components": reward.model_dump(mode="json")}
    scorer = evaluate_trace(
        {**trace, "db": {**trace["db"], "post_hash": env.get_db_hash()}},
        trace["expected_actions"], mutation_tools=MUTATION_TOOLS,
        official_env=official, required_communication=trace["required_communication"])
    token_counts = {
        "input": sum(len(tokenizer.encode(text)) for text in trace["rendered_messages"]),
        "output": sum(len(tokenizer.encode(canonical_json(item)))
                      for item in trace["assistant_messages"]),
        "tool": sum(len(tokenizer.encode(str(item.get("content") or "")))
                    for item in trace["tool_responses"]),
    }
    token_counts["total"] = sum(token_counts.values())
    return {
        "final_db_hash": env.get_db_hash(),
        "scorer": scorer,
        "ordered_trajectory_hash": sha256_value(trace["tool_calls"]),
        "ordered_tool_calls": trace["tool_calls"],
        "tokens": token_counts,
        "fresh_initial_hash": get_env(trace["identity"]["domain"]).get_db_hash(),
    }


def replay_twice_from_fresh_copies(path: Path, tokenizer) -> dict[str, Any]:
    results = []
    for _ in range(2):
        with tempfile.TemporaryDirectory(prefix="mvep_replay_") as directory:
            copy_path = Path(directory) / "raw_trace.json"
            shutil.copy2(path, copy_path)
            results.append(replay_once(copy_path, tokenizer))
    trace = json.loads(path.read_text())
    expected_tokens = {key: trace["tokens"][key] for key in ("input", "output", "tool", "total")}
    return {
        "trajectory_id": trace["identity"]["trajectory_id"],
        "copy_1": results[0], "copy_2": results[1],
        "two_replays_identical": results[0] == results[1],
        "db_matches_capture": results[0]["final_db_hash"] == trace["db"]["post_hash"],
        "scorer_matches_capture": results[0]["scorer"] == trace["scorer"],
        "ordered_matches_capture": results[0]["ordered_tool_calls"] == trace["tool_calls"],
        "tokens_match_capture": results[0]["tokens"] == expected_tokens,
        "fresh_reset_matches_capture": results[0]["fresh_initial_hash"] == trace["db"]["pre_hash"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    paths = sorted(args.run_root.glob("*/raw_trace.json"))
    if len(paths) != 8:
        raise RuntimeError(f"expected_8_traces_found_{len(paths)}")
    rows = [replay_twice_from_fresh_copies(path, tokenizer) for path in paths]
    required = ("two_replays_identical", "db_matches_capture", "scorer_matches_capture",
                "ordered_matches_capture", "tokens_match_capture", "fresh_reset_matches_capture")
    report = {"schema_version": "r7d-mvep-replay-v1", "n_trajectories": len(rows),
              "rows": rows, "all_pass": all(all(row[key] for key in required) for row in rows),
              "model_calls": 0, "effect_estimated": False}
    output = args.run_root / "replay_report.json"
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    print(json.dumps({"n": len(rows), "all_pass": report["all_pass"]}))
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
