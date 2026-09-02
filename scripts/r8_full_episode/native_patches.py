#!/usr/bin/env python3
"""R8 Full-Episode: minimal, non-forking robustness patches for the NATIVE tau2 path.

Mistral (and occasionally other local models) sometimes emit a malformed tool call
with an EMPTY function name. litellm then 400s when that message is replayed in the
next request, which would crash the whole episode as an INFRASTRUCTURE failure. An
empty-name tool call is an AGENT behavior, not infra: per spec 8 it must be recorded
as an agent (tool/parser) outcome, not silently dropped and not fatal.

This wraps `tau2.utils.llm_utils.generate` so that any empty/whitespace tool-call
name in the returned AssistantMessage is fail-closed sanitized to "__invalid__"
(same convention R7 used). The environment then returns a tool error for it, the
episode continues, and the malformed call surfaces in the trace as an errored tool
result (counted in invalid_tool_calls). NO evaluator/orchestrator logic is modified.

Idempotent: calling install() more than once is a no-op.
"""
from __future__ import annotations

INVALID = "__invalid__"
_INSTALLED = False


def _sanitize_assistant(am):
    n = 0
    for tc in (getattr(am, "tool_calls", None) or []):
        name = (getattr(tc, "name", None) or "").strip()
        if not name:
            tc.name = INVALID
            n += 1
    return n


def install() -> bool:
    """Monkeypatch tau2.utils.llm_utils.generate to sanitize empty tool-call names.
    Returns True if newly installed, False if already installed."""
    global _INSTALLED
    if _INSTALLED:
        return False
    import tau2.utils.llm_utils as llm_utils

    _orig_generate = llm_utils.generate

    def _patched_generate(*args, **kwargs):
        am = _orig_generate(*args, **kwargs)
        try:
            _sanitize_assistant(am)
        except Exception:  # noqa: BLE001 - never let the guard itself break a run
            pass
        return am

    _patched_generate.__wrapped__ = _orig_generate
    llm_utils.generate = _patched_generate

    # the agent module imported `generate` by name at load time; rebind there too.
    try:
        import tau2.agent.llm_agent as la
        if getattr(la, "generate", None) is _orig_generate:
            la.generate = _patched_generate
    except Exception:  # noqa: BLE001
        pass

    _INSTALLED = True
    return True
