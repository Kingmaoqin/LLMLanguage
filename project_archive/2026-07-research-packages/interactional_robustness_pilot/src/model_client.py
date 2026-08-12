from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ChatResult:
    ok: bool
    message: Dict[str, Any]
    usage: Dict[str, Any]
    latency_ms: int
    raw: Dict[str, Any]
    error: str = ""


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str = "EMPTY", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def list_models(self) -> Dict[str, Any]:
        return self._request("GET", "/models", None)

    def model_ids(self) -> List[str]:
        payload = self.list_models()
        ids = []
        for item in payload.get("data", []):
            model_id = item.get("id")
            if model_id:
                ids.append(model_id)
        return ids

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        top_p: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> ChatResult:
        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        if tools is not None:
            body["tools"] = tools
            body["tool_choice"] = tool_choice or "auto"
        if seed is not None:
            body["seed"] = seed

        start = time.time()
        try:
            raw = self._request("POST", "/chat/completions", body)
            latency_ms = int((time.time() - start) * 1000)
            choices = raw.get("choices") or []
            message = choices[0].get("message", {}) if choices else {}
            usage = raw.get("usage") or {}
            return ChatResult(ok=True, message=message, usage=usage, latency_ms=latency_ms, raw=raw)
        except Exception as exc:
            latency_ms = int((time.time() - start) * 1000)
            return ChatResult(ok=False, message={}, usage={}, latency_ms=latency_ms, raw={}, error=str(exc))

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"URL error {url}: {exc.reason}") from exc


def extract_native_tool_calls(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        calls.append(
            {
                "id": call.get("id"),
                "name": function.get("name", ""),
                "arguments": function.get("arguments", "{}"),
            }
        )
    return calls


def usage_counts(usages: List[Dict[str, Any]]) -> Dict[str, int]:
    total = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}
    for usage in usages:
        total["total_tokens"] += int(usage.get("total_tokens") or usage.get("total") or 0)
        total["input_tokens"] += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        total["output_tokens"] += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return total

