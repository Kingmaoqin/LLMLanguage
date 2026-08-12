from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.manipulation_checks import run_checks
from src.model_client import OpenAICompatibleClient, extract_native_tool_calls
from src.tool_environment import ToolEnvironment, manual_tool_protocol_text, openai_tools
from src.utils import load_json, load_yaml, package_versions, parse_json_object_from_text, write_csv, write_json, write_yaml


PRECHECK_STATE = {
    "orders": {
        "ORD-000": {
            "order_id": "ORD-000",
            "status": "processing",
            "cancellable": True,
            "refund_eligible": True,
            "amount": 12.0,
        }
    },
    "support_tickets": [],
    "drafts": {},
    "sent_emails": [],
    "calendar": {},
    "employees": {},
    "emails": [],
}

PREFLIGHT_FIELDS = [
    "run_id",
    "model_alias",
    "protocol",
    "temperature",
    "tool_call_emitted",
    "json_parseable",
    "schema_valid",
    "arguments_match_schema",
    "unexpected_tool_called",
    "final_response_incorporated_tool_result",
    "error",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    config = load_yaml(root / args.config)
    reports_dir = root / "reports"
    results_dir = root / "results"

    base_tasks = load_json(root / "data" / "base_tasks.json")
    condition_scripts = load_json(root / "data" / "condition_scripts.json")
    checks_passed, invariant_rows, manipulation_rows = run_checks(base_tasks, condition_scripts, reports_dir)
    write_json(reports_dir / "package_versions.json", package_versions())

    model_config = {"models": []}
    preflight_rows: List[Dict[str, Any]] = []
    report_lines = [
        "# Preflight Report",
        "",
        f"Manipulation/invariant checks passed: `{checks_passed}`",
        "",
    ]
    if not checks_passed:
        report_lines.extend([
            "Invariant or contamination checks failed. Main experiment must not be run.",
            "",
            "See `reports/invariant_checks.csv` and `reports/manipulation_checks.csv`.",
        ])

    for model_spec in config["models"]:
        alias = model_spec["model_alias"]
        client = OpenAICompatibleClient(model_spec["base_url"], model_spec.get("api_key", "EMPTY"))
        entry = {
            "model_alias": alias,
            "base_url": model_spec["base_url"],
            "model_id": None,
            "api_key": model_spec.get("api_key", "EMPTY"),
            "serving_backend": "unknown",
            "supports_seed": "unknown",
            "supports_usage": "unknown",
            "supports_tool_calls": "unknown",
            "tool_protocol": "unknown",
            "preflight_passed": False,
            "notes": "",
        }
        report_lines.append(f"## {alias}")
        try:
            models_payload = client.list_models()
            model_ids = [item.get("id") for item in models_payload.get("data", []) if item.get("id")]
            entry["model_id"] = model_ids[0] if model_ids else None
            entry["notes"] = f"Detected model IDs: {model_ids}"
            report_lines.append(f"- `/models` IDs: `{model_ids}`")
        except Exception as exc:
            entry["notes"] = f"/models failed: {exc}"
            report_lines.append(f"- `/models` failed: `{exc}`")
            model_config["models"].append(entry)
            continue

        if not entry["model_id"]:
            entry["notes"] += "; no model_id returned"
            report_lines.append("- No model ID returned; preflight failed.")
            model_config["models"].append(entry)
            continue

        supports_seed = detect_seed_support(client, entry["model_id"])
        entry["supports_seed"] = supports_seed
        native_rows, native_valid, native_usage = run_protocol_preflight(client, entry, config, "native_tool_calls", supports_seed)
        preflight_rows.extend(native_rows)
        entry["supports_usage"] = native_usage
        if native_valid >= 5:
            entry["supports_tool_calls"] = True
            entry["tool_protocol"] = "native_tool_calls"
            entry["preflight_passed"] = bool(checks_passed)
            entry["notes"] += f"; native tool preflight valid {native_valid}/6"
            report_lines.append(f"- Native tool calls: `{native_valid}/6` schema-valid.")
        else:
            report_lines.append(f"- Native tool calls: `{native_valid}/6` schema-valid; testing manual JSON protocol.")
            manual_rows, manual_valid, manual_usage = run_protocol_preflight(client, entry, config, "manual_tool_protocol", supports_seed)
            preflight_rows.extend(manual_rows)
            entry["supports_usage"] = native_usage or manual_usage
            if manual_valid >= 5:
                entry["supports_tool_calls"] = False
                entry["tool_protocol"] = "manual_tool_protocol"
                entry["preflight_passed"] = bool(checks_passed)
                entry["notes"] += f"; native failed; manual protocol valid {manual_valid}/6"
                report_lines.append(f"- Manual JSON protocol: `{manual_valid}/6` schema-valid.")
            else:
                entry["supports_tool_calls"] = False
                entry["tool_protocol"] = "failed"
                entry["preflight_passed"] = False
                entry["notes"] += f"; native valid {native_valid}/6; manual valid {manual_valid}/6"
                report_lines.append(f"- Manual JSON protocol: `{manual_valid}/6`; preflight failed.")

        model_config["models"].append(entry)
        report_lines.append(f"- Selected protocol: `{entry['tool_protocol']}`")
        report_lines.append(f"- Preflight passed: `{entry['preflight_passed']}`")
        report_lines.append("")

    write_yaml(root / "model_config.yaml", model_config)
    write_csv(results_dir / "preflight_results.csv", preflight_rows, fieldnames=PREFLIGHT_FIELDS)
    all_passed = checks_passed and all(model.get("preflight_passed") for model in model_config["models"])
    report_lines.extend([
        "## Overall",
        "",
        f"Overall preflight pass: `{all_passed}`",
    ])
    if not all_passed:
        report_lines.append("")
        report_lines.append("Main experiment must not be run. Scientific claims cannot be made from failed preflight.")
    (reports_dir / "PREFLIGHT_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def detect_seed_support(client: OpenAICompatibleClient, model_id: str) -> bool:
    messages = [{"role": "user", "content": "Reply with the word ok."}]
    result = client.chat(model=model_id, messages=messages, temperature=0.0, seed=11)
    return result.ok


def run_protocol_preflight(
    client: OpenAICompatibleClient,
    model_entry: Dict[str, Any],
    config: Dict[str, Any],
    protocol: str,
    supports_seed: bool,
) -> Tuple[List[Dict[str, Any]], int, bool]:
    rows: List[Dict[str, Any]] = []
    valid_count = 0
    usage_seen = False
    temps = [0.0, 0.0, 0.0, 0.2, 0.2, 0.2]
    system_prompt = config["agent"]["system_prompt"]

    for idx, temp in enumerate(temps):
        run_id = f"preflight_{model_entry['model_alias']}_{protocol}_{idx}"
        messages = [{"role": "system", "content": system_prompt}]
        if protocol == "manual_tool_protocol":
            messages.append({"role": "system", "content": manual_tool_protocol_text()})
        messages.append({"role": "user", "content": "Please check the status of order ORD-000."})
        seed = [11, 13, 17, 19, 23, 29][idx] if supports_seed else None
        row = {
            "run_id": run_id,
            "model_alias": model_entry["model_alias"],
            "protocol": protocol,
            "temperature": temp,
            "tool_call_emitted": False,
            "json_parseable": False,
            "schema_valid": False,
            "arguments_match_schema": False,
            "unexpected_tool_called": False,
            "final_response_incorporated_tool_result": False,
            "error": "",
        }
        if protocol == "native_tool_calls":
            result = client.chat(model_entry["model_id"], messages, temp, tools=openai_tools(), seed=seed)
            usage_seen = usage_seen or bool(result.usage)
            if not result.ok:
                row["error"] = result.error
                rows.append(row)
                continue
            tool_calls = extract_native_tool_calls(result.message)
            row["tool_call_emitted"] = bool(tool_calls)
            if tool_calls:
                call = tool_calls[0]
                env = ToolEnvironment(PRECHECK_STATE, {"run_id": run_id, "model_alias": model_entry["model_alias"], "task_id": "preflight", "condition_id": "preflight", "repeat_id": idx, "temperature": temp, "tool_protocol": protocol})
                tool_result, log = env.execute(call["name"], call["arguments"], 0)
                row["json_parseable"] = isinstance(log["parsed_arguments"], dict) and not str(log["tool_error"]).startswith("json_parse_error")
                row["schema_valid"] = bool(log["schema_valid"])
                row["arguments_match_schema"] = log["parsed_arguments"].get("order_id") == "ORD-000"
                row["unexpected_tool_called"] = call["name"] != "get_order_status"
                messages.append({"role": "assistant", "content": result.message.get("content"), "tool_calls": result.message.get("tool_calls")})
                messages.append({"role": "tool", "tool_call_id": call.get("id") or "preflight-call", "name": call["name"], "content": json.dumps(tool_result, sort_keys=True)})
                final = client.chat(model_entry["model_id"], messages, temp, tools=openai_tools(), seed=seed)
                usage_seen = usage_seen or bool(final.usage)
                final_text = final.message.get("content", "") if final.ok else ""
                row["final_response_incorporated_tool_result"] = "ORD-000" in final_text or "processing" in final_text.lower() or "status" in final_text.lower()
        else:
            result = client.chat(model_entry["model_id"], messages, temp, seed=seed)
            usage_seen = usage_seen or bool(result.usage)
            if not result.ok:
                row["error"] = result.error
                rows.append(row)
                continue
            obj = parse_json_object_from_text(result.message.get("content") or "")
            tool_call = obj.get("tool_call") if isinstance(obj, dict) else None
            row["tool_call_emitted"] = isinstance(tool_call, dict)
            if isinstance(tool_call, dict):
                env = ToolEnvironment(PRECHECK_STATE, {"run_id": run_id, "model_alias": model_entry["model_alias"], "task_id": "preflight", "condition_id": "preflight", "repeat_id": idx, "temperature": temp, "tool_protocol": protocol})
                tool_result, log = env.execute(str(tool_call.get("name", "")), tool_call.get("arguments", {}), 0)
                row["json_parseable"] = True
                row["schema_valid"] = bool(log["schema_valid"])
                row["arguments_match_schema"] = log["parsed_arguments"].get("order_id") == "ORD-000"
                row["unexpected_tool_called"] = str(tool_call.get("name", "")) != "get_order_status"
                messages.append({"role": "assistant", "content": result.message.get("content") or ""})
                messages.append({"role": "user", "content": f"TOOL_RESULT get_order_status: {json.dumps(tool_result, sort_keys=True)}"})
                final = client.chat(model_entry["model_id"], messages, temp, seed=seed)
                usage_seen = usage_seen or bool(final.usage)
                final_text = final.message.get("content", "") if final.ok else ""
                row["final_response_incorporated_tool_result"] = "ORD-000" in final_text or "processing" in final_text.lower() or "status" in final_text.lower()

        if row["tool_call_emitted"] and row["json_parseable"] and row["schema_valid"] and row["arguments_match_schema"] and not row["unexpected_tool_called"]:
            valid_count += 1
        rows.append(row)
    return rows, valid_count, usage_seen


if __name__ == "__main__":
    main()
