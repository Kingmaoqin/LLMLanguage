"""Per-tool-call state instrumentation for tau2 (plan §30).

Wraps `environment.get_response` (the single point where every tool call hits the domain DB,
orchestrator.py:325) to capture, for each call, the DB-state hash before and after — giving
true per-event `state_before_hash`/`state_after_hash`/`mutated` that message parsing alone
cannot. No tau2 source edit; coexists with the valence overlay (which wraps different methods).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolEventRecorder:
    """Records (in execution order) per-call DB hashes and mutation flags."""

    records: list[dict[str, Any]] = field(default_factory=list)

    def attach(self, orchestrator: Any) -> None:
        env = orchestrator.environment
        orig_get_response = env.get_response

        def get_response(message):  # message: ToolCall
            before = env.get_db_hash()
            tool_message = orig_get_response(message)
            after = env.get_db_hash()
            self.records.append({
                "tool_call_id": message.id,
                "tool_name": message.name,
                "requestor": message.requestor,
                "state_before_hash": before,
                "state_after_hash": after,
                "mutated": before != after,
                "error": bool(getattr(tool_message, "error", False)),
            })
            return tool_message

        env.get_response = get_response

    def agent_records(self) -> list[dict[str, Any]]:
        """Records for agent-issued calls only, in execution order."""
        return [r for r in self.records if r["requestor"] == "assistant"]
