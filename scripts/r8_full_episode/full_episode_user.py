#!/usr/bin/env python3
"""R8 Full-Episode: the full-episode user simulator plugged into the NATIVE tau2
half-duplex orchestrator.

FullEpisodeUser is a tau2 HalfDuplexUser. For C1-C4 it composes the Canonical
Semantic Controller (condition-blind semantic payload) with the condition Style
Renderer (interaction-only wording). For C0 it delegates entirely to the official
cooperative UserSimulator, so C0 measures whether our scaffold itself changes
outcomes.

Turn model (spec 6.3): every time the orchestrator hands the user an agent message,
the SAME semantic controller replies once; only the renderer differs by condition.
Pressure conditions never get extra facts or extra turns. If pressure makes the
agent ask more / less / finish early, that is a RESULT, not something we backfill.

The C4 frustration level and any progress signal are computed ONLY from
agent-VISIBLE text (spec 6.4) — never from hidden chain-of-thought or tool logs.
"""
from __future__ import annotations

import re
from typing import Optional

from tau2.data_model.message import (
    AssistantMessage, Message, MultiToolMessage, ToolMessage, UserMessage,
)
from tau2.user.user_simulator import UserSimulator
from tau2.user.user_simulator_base import (
    STOP, HalfDuplexUser, UserState, is_valid_user_history_message,
)

from scripts.r8_full_episode.semantic_controller import SemanticController
from scripts.r8_full_episode.condition_renderers import (
    RenderContext, FrustrationTracker, render, template_bank_hash,
)

# Agent-visible failure/apology markers (user can see these in the agent's text).
_FAILURE_MARKERS = re.compile(
    r"\b(sorry|apolog|unable to|couldn'?t|can'?t (?:find|locate|complete)|"
    r"went wrong|error|failed|not able to|there was a problem)\b", re.I)


class FullEpisodeUser(HalfDuplexUser[UserState]):
    """Half-duplex user for one R8 episode under a fixed condition."""

    CONDITIONS = ("C0", "C1", "C2", "C3", "C4")

    def __init__(self, task, domain: str, condition: str, *,
                 tools=None, instructions: Optional[str] = None,
                 user_llm: str, api_base: str, seed: int = 0,
                 generate_fn=None):
        assert condition in self.CONDITIONS, condition
        super().__init__(instructions=instructions, tools=tools)
        self.task = task
        self.domain = domain
        self.condition = condition
        self.seed = seed
        self.records: list[dict] = []
        self._turn = 0
        self._last_agent_text = ""
        self._frustration = FrustrationTracker()
        self.template_bank_hash = template_bank_hash()

        if condition == "C0":
            # Official cooperative user simulator (no controller/renderer).
            self._native = UserSimulator(
                llm=user_llm, instructions=instructions or str(task.user_scenario),
                tools=tools, llm_args={"api_base": api_base, "api_key": "EMPTY",
                                       "temperature": 0.0, "seed": seed})
            self._controller = None
        else:
            self._native = None
            self._controller = SemanticController(
                task, domain, generate_fn=generate_fn, user_llm=user_llm,
                api_base=api_base, seed=seed)

    # -- tau2 HalfDuplexUser interface --------------------------------------
    def get_init_state(self, message_history: Optional[list[Message]] = None) -> UserState:
        if self.condition == "C0":
            return self._native.get_init_state(message_history)
        if message_history is None:
            message_history = []
        assert all(is_valid_user_history_message(m) for m in message_history), \
            "invalid user history message"
        return UserState(system_messages=[], messages=list(message_history))

    @classmethod
    def is_stop(cls, message: UserMessage) -> bool:
        return UserSimulator.is_stop(message)

    def set_seed(self, seed: int):
        self.seed = seed
        if self._native is not None:
            try:
                self._native.set_seed(seed)
            except Exception:  # noqa: BLE001 - native may not implement; fine
                pass

    @staticmethod
    def _agent_visible_text(message) -> str:
        if isinstance(message, AssistantMessage):
            return message.content or ""
        if isinstance(message, (ToolMessage, MultiToolMessage)):
            return ""  # tool results are not user-visible in half-duplex
        return getattr(message, "content", "") or ""

    def generate_next_message(self, message, state: UserState):
        if self.condition == "C0":
            return self._native.generate_next_message(message, state)

        agent_text = self._agent_visible_text(message)
        # deterministic, agent-VISIBLE-only progress signal for C4 frustration.
        made_progress = bool(agent_text.strip()) and agent_text.strip() != self._last_agent_text
        failure = bool(_FAILURE_MARKERS.search(agent_text))
        frustration_level = self._frustration.update(agent_text, made_progress, failure)

        payload = self._controller.respond(agent_text)
        ctx = RenderContext(turn_index=self._turn,
                            frustration_level=frustration_level,
                            dialogue_state=payload.dialogue_state)
        rendered = render(payload.semantic_payload, self.condition, ctx)
        if payload.is_terminal and STOP not in rendered:
            rendered = f"{rendered} {STOP}".strip()

        user_msg = UserMessage(role="user", content=rendered)
        state.messages.append(user_msg)

        self.records.append(dict(
            turn_index=self._turn, dialogue_state=payload.dialogue_state,
            style_condition=self.condition, style_level=frustration_level,
            semantic_payload_hash=payload.semantic_payload_hash,
            semantic_payload=payload.semantic_payload, rendered_text=rendered,
            is_terminal=payload.is_terminal, agent_visible_text=agent_text,
            made_progress=made_progress, failure_marker=failure,
        ))
        self._last_agent_text = agent_text.strip()
        self._turn += 1
        return user_msg, state
