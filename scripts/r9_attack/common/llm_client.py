#!/usr/bin/env python3
"""R9 local model client (spec 0.1, 17).

All inference goes through cluster-local, OpenAI-compatible vLLM endpoints. Deliberately
implemented on `urllib` rather than the `openai` SDK so that the agent driver, the
attacker, the reviewers and the ToolSandbox worker all share one wire format even though
they run in two different conda environments with different SDK pins.

Spec 17 reproduction settings are enforced here, not left to callers:
  temperature = 0, concurrency = 1, fixed served-name, fixed max context.

Failure taxonomy (spec 17): transport/HTTP/timeouts are INFRASTRUCTURE failures and are
raised as `InfraFailure` so the driver can re-run the whole block from a clean state. A
model that refuses, no-ops, emits a broken tool call or exhausts its budget is an
OUTCOME and is returned normally.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


class InfraFailure(RuntimeError):
    """Transport-level failure: whole block must be re-run from a clean state."""


class NonLocalEndpoint(RuntimeError):
    """Raised when a configured endpoint is not cluster-local (spec 0.1)."""


def assert_local_endpoint(base_url: str) -> str:
    host = urlparse(base_url).hostname or ""
    if host in LOCAL_HOSTS:
        return host
    # Allow RFC1918 cluster-internal addresses; reject anything publicly routable.
    import ipaddress

    try:
        ip = ipaddress.ip_address(host)
    except ValueError as exc:
        raise NonLocalEndpoint(f"endpoint host {host!r} is not an IP literal") from exc
    if ip.is_private or ip.is_loopback:
        return host
    raise NonLocalEndpoint(f"endpoint {base_url} is not cluster-local")


@dataclass
class Endpoint:
    """One served model. `alias` is the R9-facing name, `served_id` the vLLM name."""

    alias: str
    served_id: str
    base_url: str
    api_key: str = "EMPTY"
    max_model_len: int = 16384
    max_tokens_per_turn: int = 512
    request_timeout_seconds: int = 180

    def host(self) -> str:
        return assert_local_endpoint(self.base_url)


@dataclass
class ChatResult:
    """One completion. `tool_calls` is normalised to [{id,name,arguments(dict|str)}]."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


def _post(url: str, payload: dict, api_key: str, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(
    endpoint: Endpoint,
    messages: list[dict[str, Any]],
    *,
    tools: Optional[list[dict]] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.0,
    retries: int = 3,
    seed: Optional[int] = 0,
) -> ChatResult:
    """One chat completion against a local vLLM endpoint.

    `tools=None` means the callee gets NO tool access at all — this is how spec 0.2
    `attacker/reviewer tool access = none` is enforced structurally rather than by prompt.
    """
    endpoint.host()  # raises NonLocalEndpoint before any socket is opened
    payload: dict[str, Any] = {
        "model": endpoint.served_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens or endpoint.max_tokens_per_turn,
        "n": 1,
        "stream": False,
    }
    if seed is not None:
        payload["seed"] = seed
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    url = endpoint.base_url.rstrip("/") + "/chat/completions"
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        t0 = time.time()
        try:
            body = _post(url, payload, endpoint.api_key, endpoint.request_timeout_seconds)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:500]
            except Exception:
                pass
            # 4xx other than 429 is a *request* bug (e.g. context overflow) -> still
            # infra for accounting purposes, but never silently retried into a result.
            last_exc = InfraFailure(f"HTTP {exc.code} from {url}: {detail}")
            if exc.code not in (429, 500, 502, 503, 504):
                raise last_exc from exc
        except Exception as exc:  # timeout, connection reset, malformed JSON
            last_exc = InfraFailure(f"{type(exc).__name__}: {exc}")
        else:
            return _parse(body, time.time() - t0)
        time.sleep(min(2 ** attempt, 8))
    raise InfraFailure(f"endpoint {endpoint.alias} unreachable after {retries} attempts: {last_exc}")


def _parse(body: dict, latency: float) -> ChatResult:
    try:
        choice = body["choices"][0]
    except (KeyError, IndexError) as exc:
        raise InfraFailure(f"malformed completion body: {str(body)[:300]}") from exc
    msg = choice.get("message") or {}
    calls: list[dict[str, Any]] = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args_raw = fn.get("arguments")
        if isinstance(args_raw, str):
            try:
                args = json.loads(args_raw) if args_raw.strip() else {}
            except json.JSONDecodeError:
                # A malformed argument string is a MODEL outcome (parser failure), not
                # infra: keep the raw text so extract_metrics can classify the episode.
                args = {"__unparsed__": args_raw}
        elif isinstance(args_raw, dict):
            args = args_raw
        else:
            args = {}
        calls.append({"id": tc.get("id") or "", "name": fn.get("name") or "", "arguments": args})
    usage = body.get("usage") or {}
    return ChatResult(
        content=msg.get("content") or "",
        tool_calls=calls,
        finish_reason=choice.get("finish_reason") or "",
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        latency_s=latency,
        raw=body,
    )


def probe(endpoint: Endpoint, timeout: int = 10) -> dict[str, Any]:
    """Liveness + served-name check used by the preflight and the safety audit."""
    endpoint.host()
    url = endpoint.base_url.rstrip("/") + "/models"
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {endpoint.api_key}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"alias": endpoint.alias, "alive": False, "error": f"{type(exc).__name__}: {exc}"}
    served = [m.get("id") for m in body.get("data", [])]
    return {
        "alias": endpoint.alias,
        "alive": True,
        "served_ids": served,
        "served_id_matches": endpoint.served_id in served,
        "max_model_len": next(
            (m.get("max_model_len") for m in body.get("data", []) if m.get("id") == endpoint.served_id),
            None,
        ),
    }


def load_endpoints(path) -> dict[str, Endpoint]:
    """Load the R9 model roster (configs/r9_attack/models.json)."""
    import pathlib

    raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    out: dict[str, Endpoint] = {}
    for entry in raw["models"]:
        out[entry["alias"]] = Endpoint(**entry)
    return out
