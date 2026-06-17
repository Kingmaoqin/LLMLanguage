"""Endpoint precheck for the Stage-2 model roster (plan §20).

For every locally-served model in the roster, verifies: /models lists the served id,
/chat/completions answers, and a native tool call is emitted and parseable. Writes
reports/MODEL_ENDPOINT_CHECK.md. A model that fails here must not enter the experiment.

Pure stdlib (urllib) so it has no dependency on the serving env.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

PROBE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_order_status",
        "description": "Get the status of a retail order.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
}
PROBE_USER = "Please check the status of order ORD-000."


def _post(url: str, body: dict, api_key: str, timeout: int = 60) -> dict:
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get(url: str, api_key: str, timeout: int = 15) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def check_model(model: dict) -> dict:
    base, key, served = model["base_url"].rstrip("/"), model.get("api_key", "EMPTY"), model["served_id"]
    result = {"alias": model["alias"], "served_id": served, "models_ok": False,
              "chat_ok": False, "tool_call_ok": False, "error": ""}
    try:
        ids = [m.get("id") for m in _get(f"{base}/models", key).get("data", [])]
        result["models_ok"] = served in ids
        if not result["models_ok"]:
            result["error"] = f"served_id not in /models: {ids}"
            return result
        body = {
            "model": served,
            "messages": [{"role": "user", "content": PROBE_USER}],
            "tools": [PROBE_TOOL],
            "tool_choice": "auto",
            "temperature": 0.0,
            "max_tokens": 256,
        }
        msg = (_post(f"{base}/chat/completions", body, key).get("choices") or [{}])[0].get("message", {})
        result["chat_ok"] = bool(msg.get("content") or msg.get("tool_calls"))
        for call in msg.get("tool_calls") or []:
            fn = call.get("function") or {}
            if fn.get("name") == "get_order_status":
                args = json.loads(fn.get("arguments") or "{}")
                result["tool_call_ok"] = "order_id" in args
                break
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def run_precheck(root: Path, config_rel: str, aliases: list[str] | None = None) -> dict[str, bool]:
    """Check endpoints, write reports/MODEL_ENDPOINT_CHECK.md, return {alias: passed}.

    Shared by the standalone script and the runner's pre-run gate, so the precheck report is
    produced on either path.
    """
    cfg = yaml.safe_load((root / config_rel).read_text(encoding="utf-8"))
    models = [m for m in cfg["models"] if m.get("local") and (aliases is None or m["alias"] in aliases)]
    results = [check_model(m) for m in models]
    passed = {r["alias"]: (r["models_ok"] and r["chat_ok"] and r["tool_call_ok"]) for r in results}

    lines = ["# MODEL_ENDPOINT_CHECK", "", f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
             "| model | /models | /chat | tool-call | error |", "|---|---|---|---|---|"]
    for r in results:
        mark = "✅" if passed[r["alias"]] else "❌"
        lines.append(f"| {r['alias']} {mark} | {r['models_ok']} | {r['chat_ok']} | "
                     f"{r['tool_call_ok']} | {r['error'] or '—'} |")
    lines += ["", f"All checked endpoints passed: **{all(passed.values()) if passed else False}**"]
    (root / "reports").mkdir(exist_ok=True)
    (root / "reports" / "MODEL_ENDPOINT_CHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/model_config.yaml")
    parser.add_argument("--require", nargs="*", help="alias subset that must pass for exit 0 (default: all checked)")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    passed = run_precheck(root, args.config)
    for alias, ok in passed.items():
        print(alias, "OK" if ok else "FAIL")
    # Hard gate (plan §20/§46): non-zero exit if any required model failed.
    if not all(passed.get(a, False) for a in (args.require or list(passed))):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
