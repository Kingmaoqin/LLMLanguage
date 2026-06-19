"""Conversation-management diagnostics for Stage-2.5."""

from __future__ import annotations

import re
from typing import Any


BOUNDARY_RE = re.compile(r"\b(can't|cannot|unable|not able|policy|need to|must|before i can)\b", re.IGNORECASE)
REPAIR_RE = re.compile(r"\b(sorry|apologize|let me|i should|correction|instead)\b", re.IGNORECASE)
ABANDON_RE = re.compile(r"\b(cancel that|stop|nevermind|never mind|forget it|no thanks)\b", re.IGNORECASE)


def evaluate_conversation_management(conversation: list[dict[str, Any]]) -> dict[str, Any]:
    assistant = [str(m.get("content") or "") for m in conversation if m.get("role") == "assistant"]
    user = [str(m.get("content") or "") for m in conversation if m.get("role") == "user"]
    boundary_count = sum(1 for text in assistant if BOUNDARY_RE.search(text))
    repair_count = sum(1 for text in assistant if REPAIR_RE.search(text))
    abandonment_count = sum(1 for text in user if ABANDON_RE.search(text))
    return {
        "boundary_setting_count": boundary_count,
        "self_repair_count": repair_count,
        "user_abandonment_markers": abandonment_count,
        "assistant_text_turns": len([t for t in assistant if t.strip()]),
        "user_text_turns": len([t for t in user if t.strip()]),
    }
