from __future__ import annotations

import copy
import json
from typing import Any, Dict, List

from .evaluators import evaluate_run
from .model_client import OpenAICompatibleClient, extract_native_tool_calls, usage_counts
from .tool_environment import ToolEnvironment, manual_tool_protocol_text, openai_tools
from .utils import parse_json_object_from_text


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def run_agent(
    config: Dict[str, Any],
    model_entry: Dict[str, Any],
    task: Dict[str, Any],
    script: Dict[str, Any],
    run_meta: Dict[str, Any],
    temperature: float,
    seed: int | None,
) -> Dict[str, Any]:
    protocol = model_entry.get("tool_protocol", "native_tool_calls")
    model_id = model_entry.get("model_id")
    if not model_id:
        raise RuntimeError(f"Missing model_id for {model_entry.get('model_alias')}. Run preflight first.")

    client = OpenAICompatibleClient(model_entry["base_url"], model_entry.get("api_key", "EMPTY"))
    env = ToolEnvironment(task["initial_environment_state"], run_meta)
    max_steps = int(config["experiment"].get("max_steps", 10))
    top_p = float(config["experiment"].get("top_p", 1.0))
    system_prompt = config["agent"]["system_prompt"]

    api_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if protocol == "manual_tool_protocol":
        api_messages.append({"role": "system", "content": manual_tool_protocol_text()})
    conversation: List[Dict[str, Any]] = copy.deepcopy(api_messages)
    user_turns = list(script["user_turns"])
    next_user_turn = 0
    total_latency_ms = 0
    usages: List[Dict[str, Any]] = []
    error = ""

    def append_user(text: str, synthetic_confirmation: bool = False) -> None:
        nonlocal next_user_turn
        env.observe_user_message(text)
        msg = {"role": "user", "content": text}
        api_messages.append(msg)
        conversation.append({**msg, "synthetic_confirmation": synthetic_confirmation})
        next_user_turn += 1

    append_user(user_turns[next_user_turn])

    for step_index in range(max_steps):
        chat_seed = seed if _truthy(model_entry.get("supports_seed")) else None
        if protocol == "native_tool_calls":
            result = client.chat(
                model=model_id,
                messages=api_messages,
                temperature=temperature,
                top_p=top_p,
                tools=openai_tools(),
                tool_choice="auto",
                seed=chat_seed,
            )
        else:
            result = client.chat(
                model=model_id,
                messages=api_messages,
                temperature=temperature,
                top_p=top_p,
                tools=None,
                seed=chat_seed,
            )
        total_latency_ms += result.latency_ms
        usages.append(result.usage)
        if not result.ok:
            error = result.error
            conversation.append({"role": "assistant", "content": f"[MODEL_ERROR] {result.error}"})
            break

        if protocol == "native_tool_calls":
            message = result.message
            tool_calls = extract_native_tool_calls(message)
            assistant_msg = {"role": "assistant", "content": message.get("content")}
            if message.get("tool_calls") is not None:
                assistant_msg["tool_calls"] = message.get("tool_calls")
            api_messages.append(assistant_msg)
            conversation.append(copy.deepcopy(assistant_msg))

            if tool_calls:
                for call in tool_calls:
                    tool_result, _ = env.execute(call["name"], call["arguments"], step_index)
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": call.get("id") or f"call-{step_index}",
                        "name": call["name"],
                        "content": json.dumps(tool_result, sort_keys=True),
                    }
                    api_messages.append(tool_message)
                    conversation.append(copy.deepcopy(tool_message))
                    if call["name"] == "request_confirmation" and script.get("confirmation_response") and next_user_turn < len(user_turns):
                        append_user(script["confirmation_response"], synthetic_confirmation=True)
                continue

            if next_user_turn < len(user_turns):
                append_user(user_turns[next_user_turn])
                continue
            break

        content = result.message.get("content") or ""
        api_messages.append({"role": "assistant", "content": content})
        conversation.append({"role": "assistant", "content": content})
        obj = parse_json_object_from_text(content)
        tool_call = obj.get("tool_call") if isinstance(obj, dict) else None
        if isinstance(tool_call, dict):
            name = str(tool_call.get("name", ""))
            args = tool_call.get("arguments", {})
            tool_result, _ = env.execute(name, args, step_index)
            tool_content = json.dumps(tool_result, sort_keys=True)
            api_messages.append({"role": "user", "content": f"TOOL_RESULT {name}: {tool_content}"})
            conversation.append({"role": "tool", "name": name, "content": tool_content})
            if name == "request_confirmation" and script.get("confirmation_response") and next_user_turn < len(user_turns):
                append_user(script["confirmation_response"], synthetic_confirmation=True)
            continue

        if next_user_turn < len(user_turns):
            append_user(user_turns[next_user_turn])
            continue
        break

    token_counts = usage_counts(usages)
    final_state = env.final_state()
    metrics = evaluate_run(task, run_meta, env.tool_logs, conversation, final_state, total_latency_ms, token_counts)
    metrics["model_error"] = error
    return {
        "metrics": metrics,
        "tool_logs": env.tool_logs,
        "conversation": {
            **run_meta,
            "messages": conversation,
            "model_error": error,
        },
        "final_environment_state": {
            **run_meta,
            "state": final_state,
            "environment_state_hash_final": env.final_hash(),
        },
    }

