"""tau2-facing R6 controlled-user adapter.

The R6 benchmark uses deterministic, three-turn matched user text plus
tool-specific confirmation rules. This module exposes that contract through the
tau2 ``HalfDuplexUser`` interface for retail/airline live executors. It does not
start tau2 or call a model by itself; runners must explicitly opt into a live
tau2 executor.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import Field

try:  # pragma: no cover - import availability is environment-dependent.
    from tau2.data_model.message import Message, UserMessage
    from tau2.user.user_simulator_base import STOP, HalfDuplexUser, UserState, ValidUserInputMessage, is_valid_user_history_message
except Exception as exc:  # noqa: BLE001
    Message = UserMessage = ValidUserInputMessage = Any  # type: ignore
    STOP = "###STOP###"
    class _MissingTau2Base:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __class_getitem__(cls, item: Any) -> type:
            return cls

    HalfDuplexUser = _MissingTau2Base  # type: ignore
    UserState = _MissingTau2Base  # type: ignore
    _TAU2_IMPORT_ERROR: Exception | None = exc
else:
    _TAU2_IMPORT_ERROR = None

from src.r6.controlled_user_adapter import R6ControlledUserAdapter, stable_hash


CONFIRM_REQUEST_RE = re.compile(
    r"\b("
    r"please\s+confirm|can\s+you\s+confirm|do\s+you\s+confirm|"
    r"please\s+approve|do\s+you\s+approve|"
    r"authorize\s+(?:me|this|the|that)|authorization\s+to|"
    r"should\s+i\s+proceed|may\s+i\s+proceed"
    r")\b",
    re.I,
)


class R6Tau2UserState(UserState):  # type: ignore[misc]
    turn_index: int = 0
    confirmation_count: int = 0
    exhausted_scripted_turns: bool = False
    messages: list[Any] = Field(default_factory=list)
    system_messages: list[Any] = Field(default_factory=list)


class R6Tau2ControlledUser(HalfDuplexUser[R6Tau2UserState]):  # type: ignore[misc]
    """Deterministic R6 user exposed through tau2's user-simulator interface."""

    def __init__(
        self,
        *,
        task_id: str,
        condition_id: str,
        tasks_path: Path,
        templates_path: Path,
        user_policies_path: Path,
        instructions: str | None = None,
        tools: list[Any] | None = None,
        llm: str | None = None,
        llm_args: dict[str, Any] | None = None,
    ) -> None:
        if _TAU2_IMPORT_ERROR is not None:
            raise ImportError("tau2 is required for R6Tau2ControlledUser") from _TAU2_IMPORT_ERROR
        super().__init__(instructions=instructions, tools=tools)
        if llm not in {None, "", "controlled_user_no_llm", "r6_controlled_user_no_llm"}:
            raise ValueError("R6 tau2 controlled user forbids runtime LLMs")
        if llm_args:
            raise ValueError("R6 tau2 controlled user accepts no LLM args")
        self.task_id = task_id
        self.condition_id = condition_id
        self.adapter = R6ControlledUserAdapter(
            tasks_path=tasks_path,
            templates_path=templates_path,
            user_policies_path=user_policies_path,
        )
        task = self.adapter.task(task_id)
        if task.get("domain") not in {"retail", "airline"}:
            raise ValueError(f"R6 tau2 adapter is only for retail/airline tasks, got {task.get('domain')!r}")
        self.turns = self.adapter.render_turns(task_id, condition_id)
        self.events: list[dict[str, Any]] = []

    @classmethod
    def is_stop(cls, message: UserMessage) -> bool:  # type: ignore[override]
        return bool(getattr(message, "content", "") and "###STOP###" in str(getattr(message, "content", "")))

    def get_init_state(self, message_history: list[Message] | None = None) -> R6Tau2UserState:  # type: ignore[override]
        history = message_history or []
        assert all(is_valid_user_history_message(message) for message in history)
        return R6Tau2UserState(messages=list(history), system_messages=[])

    def generate_next_message(  # type: ignore[override]
        self,
        message: ValidUserInputMessage,
        state: R6Tau2UserState,
    ) -> tuple[UserMessage, R6Tau2UserState]:
        state.messages.append(message)
        incoming = incoming_text(message)
        if state.turn_index >= len(self.turns) and is_completion_prompt(incoming):
            text = STOP
            event = {
                "task_id": self.task_id,
                "condition": self.condition_id,
                "turn_idx": state.turn_index,
                "speech_act": "task_complete_stop",
                "clean_text": text,
                "styled_text": text,
                "clean_text_hash": stable_hash(text),
                "styled_text_hash": stable_hash(text),
            }
        elif CONFIRM_REQUEST_RE.search(incoming):
            text, event = self._confirmation_reply(state)
        elif state.turn_index < len(self.turns):
            turn = self.turns[state.turn_index]
            text = turn.styled_text
            event = {
                "task_id": self.task_id,
                "condition": self.condition_id,
                "turn_idx": state.turn_index,
                "speech_act": "scripted_task_turn",
                "clean_text": turn.clean_text,
                "styled_text": turn.styled_text,
                "clean_text_hash": turn.clean_text_hash,
                "styled_text_hash": turn.styled_text_hash,
                "wrapper_event": {
                    "template_id": turn.template_id,
                    "wrapper_text": turn.wrapper_text,
                    **turn.metadata,
                },
            }
            state.turn_index += 1
        else:
            state.exhausted_scripted_turns = True
            text = self.adapter.defaults.get("unexpected_question_fallback") or "Please follow the stated policy."
            event = {
                "task_id": self.task_id,
                "condition": self.condition_id,
                "turn_idx": state.turn_index,
                "speech_act": "fallback_after_scripted_turns",
                "clean_text": text,
                "styled_text": text,
                "clean_text_hash": stable_hash(text),
                "styled_text_hash": stable_hash(text),
            }
        self.events.append(event)
        user_message = UserMessage(role="user", content=text, cost=0.0)
        state.messages.append(user_message)
        return user_message, state

    def _confirmation_reply(self, state: R6Tau2UserState) -> tuple[str, dict[str, Any]]:
        task = self.adapter.task(self.task_id)
        requested_tool = first_tool_mentioned(state.messages[-1], task.get("mutation_tools") or [])
        confirmed = self.adapter.confirmation_value_for(self.task_id, requested_tool) if requested_tool else False
        text = "Yes, I confirm the allowed action." if confirmed else "No, I do not authorize that action."
        if confirmed:
            state.confirmation_count += 1
        return text, {
            "task_id": self.task_id,
            "condition": self.condition_id,
            "turn_idx": state.turn_index,
            "speech_act": "confirmation",
            "requested_tool": requested_tool,
            "confirmation_value": confirmed,
            "confirmation": confirmed,
            "clean_text": text,
            "styled_text": text,
            "clean_text_hash": stable_hash(text),
            "styled_text_hash": stable_hash(text),
        }


def incoming_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if content is not None:
        return str(content)
    return str(message)


def first_tool_mentioned(message: Any, tools: list[str]) -> str:
    text = incoming_text(message).lower()
    for tool in tools:
        if tool.lower() in text:
            return tool
    return tools[0] if len(tools) == 1 else ""


def is_completion_prompt(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "anything else",
            "all set",
            "completed",
            "complete and there",
            "complete and no",
            "done for you",
            "taken care of",
            "successfully processed",
            "fully processed",
            "already completed",
            "request is complete",
            "no further tasks",
            "no pending actions",
            "is there anything more",
            "is there anything else",
        )
    )
