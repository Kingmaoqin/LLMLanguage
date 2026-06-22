"""Deterministic state-machine user for the Stage-2.5b experiment."""

from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from tau2.data_model.message import (
    AssistantMessage,
    Message,
    MultiToolMessage,
    ToolMessage,
    UserMessage,
)
from tau2.user.user_simulator_base import (
    STOP,
    HalfDuplexUser,
    UserState,
    ValidUserInputMessage,
    is_valid_user_history_message,
)

from src.stage2_5b.response_library import DEFAULT_RESPONSE_LIBRARY
from src.stage2_5b.social_style_wrapper import (
    SocialStyleWrapper,
    stable_text_hash,
    style_template,
)
from src.stage2_5b.user_policy import (
    STATE_MACHINE,
    TASK_POLICIES,
    TaskUserPolicy,
    resolve_policy,
)


MAIN_CONDITIONS = [
    "neutral_single",
    "praise_affect_single",
    "praise_trust_single",
    "insult_single",
    "neutral_repeated",
    "abuse_repeated",
]

TOOL_NAME_LEAK_PATTERNS = [
    "calculate",
    "find_user_id_by_name_zip",
    "find_user_id_by_email",
    "get_user_details",
    "get_order_details",
    "get_item_details",
    "get_product_details",
    "exchange_delivered_order_items",
    "modify_pending_order_items",
    "modify_pending_order_address",
    "modify_user_address",
    "return_delivered_order_items",
    "cancel_pending_order",
    "get_reservation_details",
    "update_reservation_flights",
    "cancel_reservation",
    "update_reservation_baggages",
    "search_direct_flight",
]

HIDDEN_OR_STYLE_LEAK_PATTERNS = [
    r"\binstructions?:",
    r"\btask instructions?:",
    r"\breason for call:",
    r"\bknown info:",
    r"\bunknown info:",
    r"\bmysterious\b",
    r"\bterse\b",
    r"\bpersistent\b",
    r"\bbad mood\b",
    r"\bsick\b",
    r"\benglish is not perfect\b",
    r"\bfrench\b",
    r"\boccasionally insert\b",
    r"\bbusy\b",
    r"\bdo not want to reveal\b",
    r"\bdo not reveal\b",
    r"\bnot familiar with the domain\b",
    r"\bmake sure\b",
    r"\bask the agent\b",
    r"\bask to\b",
    r"\bmiddle of the conversation\b",
    r"\bthird agent message\b",
    r"\bfirst upgrade\b",
    r"\bthen separately\b",
    r"\bseparately change\b",
    r"\bverify each\b",
]


class ControlledUserState(UserState):
    turn_index: int = 0
    assistant_text_turns: int = 0
    state_id: str = "request_open"
    disclosed_facts: dict[str, str] = Field(default_factory=dict)
    confirmation_count: int = 0
    confirmation_revision_emitted: bool = False
    last_agent_request_type: str = ""


class ControlledUser(HalfDuplexUser[ControlledUserState]):
    """A frozen-policy user with no runtime LLM or scenario transformation."""

    def __init__(
        self,
        source_task_id: str,
        *,
        domain: str | None = None,
        condition: str = "neutral_single",
        template_id: str | None = None,
        template_text: str | None = None,
        instructions: str | None = None,
        tools: list[Any] | None = None,
        llm: str | None = None,
        llm_args: dict[str, Any] | None = None,
    ):
        super().__init__(instructions=instructions, tools=tools)
        if llm not in {None, "", "controlled_user_no_llm"}:
            raise ValueError("Stage-2.5b controlled user forbids runtime LLMs")
        if llm_args:
            raise ValueError("Stage-2.5b controlled user accepts no LLM args")
        if source_task_id in TASK_POLICIES:
            self.policy = TASK_POLICIES[source_task_id]
        else:
            self.policy = resolve_policy(source_task_id, domain=domain)
        self.style = SocialStyleWrapper(
            style_template(
                condition,
                template_id=template_id,
                template_text=template_text,
            )
        )
        self.events: list[dict[str, Any]] = []
        self.seed = 0

    def set_seed(self, seed: int) -> None:
        self.seed = int(seed)

    @classmethod
    def is_stop(cls, message: UserMessage) -> bool:
        return bool(message.content and STOP in message.content)

    def get_init_state(
        self,
        message_history: list[Message] | None = None,
    ) -> ControlledUserState:
        history = message_history or []
        assert all(is_valid_user_history_message(message) for message in history)
        return ControlledUserState(
            messages=history,
            system_messages=[],
            state_id=self.policy.initial_state,
        )

    def generate_next_message(
        self,
        message: ValidUserInputMessage,
        state: ControlledUserState,
    ) -> tuple[UserMessage, ControlledUserState]:
        self._append_incoming(message, state)
        state_before = state.state_id
        request_type, unrecognized = self.classify_agent_request(
            message,
            state,
        )
        speech_act, decision, confirmation_value = self._select_action(
            request_type,
            state,
        )
        selection = DEFAULT_RESPONSE_LIBRARY.render(
            task_id=self.policy.task_label,
            seed=self.seed,
            speech_act=speech_act,
            state_id=state_before,
            slots=self.policy.user_facts,
        )
        clean_text = selection.clean_text
        is_stop = STOP in clean_text
        styled_text, wrapper_event = self.style.render(
            clean_text,
            is_stop=is_stop,
        )
        state_after = state.state_id
        structured_slots = self._structured_slots(speech_act)
        event = {
            "task_id": self.policy.task_label,
            "source_task_id": self.policy.source_task_id,
            "domain": self.policy.domain,
            "user_state": state_before,
            "state_before": state_before,
            "state_after": state_after,
            "agent_request_type": request_type,
            "unrecognized_agent_request": unrecognized,
            "speech_act": speech_act,
            "base_response_id": selection.response_id,
            "base_clean_text": clean_text,
            "clean_text": clean_text,
            "structured_slots": structured_slots,
            "factual_slots": structured_slots,
            "confirmation_value": confirmation_value,
            "confirmation": confirmation_value,
            "decision": decision,
            "condition": self.style.template.condition,
            "style_template_id": self.style.template.template_id,
            "template_id": self.style.template.template_id,
            "styled_text": styled_text,
            "clean_text_hash": stable_text_hash(clean_text),
            "styled_text_hash": stable_text_hash(styled_text),
            "wrapper_event": wrapper_event,
        }
        self.events.append(event)
        state.disclosed_facts.update(structured_slots)
        if confirmation_value:
            state.confirmation_count += 1
        state.last_agent_request_type = request_type
        state.turn_index += 1
        user_message = UserMessage(
            role="user",
            content=styled_text,
            cost=0.0,
        )
        state.messages.append(user_message)
        return user_message, state

    def _append_incoming(
        self,
        message: ValidUserInputMessage,
        state: ControlledUserState,
    ) -> None:
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        elif isinstance(message, ToolMessage):
            state.messages.append(message)
        elif isinstance(message, AssistantMessage):
            if message.has_content() or message.is_tool_call():
                state.messages.append(message)
            if message.has_text_content():
                state.assistant_text_turns += 1

    def classify_agent_request(
        self,
        message: ValidUserInputMessage,
        state: ControlledUserState,
    ) -> tuple[str, bool]:
        if state.turn_index == 0:
            return "opening", False
        text = incoming_text(message).lower()
        if is_completion_prompt(text):
            return "task_complete", False
        if asks_to_deny(text):
            return "request_denial", False
        if asks_identity(text):
            request_type = "request_identity"
        elif asks_confirmation(text):
            return "request_confirmation", False
        elif asks_payment(text):
            request_type = "request_payment"
        elif asks_preference(text):
            request_type = "request_choice"
        elif asks_irrelevant_question(text):
            return "irrelevant_question", True
        else:
            return "unrecognized", True
        if request_type == state.last_agent_request_type:
            return "repeat_question", False
        return request_type, False

    def _select_action(
        self,
        request_type: str,
        state: ControlledUserState,
    ) -> tuple[str, str, bool]:
        if request_type == "opening":
            return "restate_goal", "state_opening", False
        if request_type == "repeat_question":
            return "repeat_known_fact", "repeat_known_fact", False
        if request_type in {"unrecognized", "irrelevant_question"}:
            return "unsupported_request", "fixed_fallback", False
        if (
            request_type == "request_confirmation"
            and self.policy.confirmation_revision_once
            and not state.confirmation_revision_emitted
        ):
            state.confirmation_revision_emitted = True
            state.state_id = "awaiting_confirmation"
            return "revise_request", "pre_confirmation_revision", False

        transitions = STATE_MACHINE.get(state.state_id)
        if not isinstance(transitions, dict):
            raise ValueError(f"unknown controlled-user state: {state.state_id}")
        speech_act = transitions.get(request_type)
        if speech_act is None:
            speech_act = transitions["unrecognized"]
        if speech_act == "confirm":
            confirmed = bool(self.policy.decisions.get("confirm", False))
            if not confirmed:
                return "deny", "deny_requested_action", False
            return "confirm", "confirm_requested_action", True
        if speech_act == "deny":
            return "deny", "deny_requested_action", False
        if speech_act == "stop":
            return "stop", "stop", False
        decision_by_act = {
            "provide_identity": "provide_identity",
            "provide_payment": "provide_payment_or_cost_rule",
            "choose_option": "choose_preference",
            "unsupported_request": "fixed_fallback",
        }
        return speech_act, decision_by_act.get(speech_act, speech_act), False

    def _structured_slots(self, speech_act: str) -> dict[str, str]:
        slot_by_act = {
            "restate_goal": "opening",
            "provide_identity": "identity",
            "repeat_known_fact": "identity",
            "provide_payment": "payment",
            "choose_option": "preference",
            "revise_request": "revision",
            "confirm": "confirmation_detail",
            "unsupported_request": "fallback",
        }
        slot = slot_by_act.get(speech_act)
        if slot is None or slot not in self.policy.user_facts:
            return {}
        return {slot: self.policy.user_facts[slot]}


def incoming_text(message: ValidUserInputMessage) -> str:
    if isinstance(message, MultiToolMessage):
        return "\n".join(
            str(tool_message.content or "")
            for tool_message in message.tool_messages
        )
    if isinstance(message, ToolMessage):
        return str(message.content or "")
    return str(getattr(message, "content", "") or "")


def asks_identity(text: str) -> bool:
    if any(
        phrase in text
        for phrase in [
            "confirm your identity",
            "verify your identity",
            "authenticate your identity",
        ]
    ):
        return True
    requested_fields = (
        r"(?:your name|email(?: address)?|zip(?: code)?|user id|"
        r"reservation id|reservation number|order id|order number)"
    )
    return bool(
        re.search(
            rf"\b(?:provide|share|give|tell|confirm|verify|need)\b"
            rf".{{0,60}}\b{requested_fields}\b",
            text,
        )
        or re.search(
            rf"\bwhat (?:is|are)\b.{{0,40}}\b{requested_fields}\b",
            text,
        )
    )


def asks_payment(text: str) -> bool:
    return any(
        word in text
        for word in [
            "payment",
            "card",
            "fee",
            "cost",
            "pay",
            "charge",
            "price",
        ]
    )


def asks_preference(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "prefer",
            "preference",
            "which option",
            "would you like",
            "exchange",
            "return",
            "business",
            "upgrade",
            "duration",
            "list",
            "items",
        ]
    )


def asks_confirmation(text: str) -> bool:
    if re.search(r"\b(which|what)\b.{0,80}\bshould i\b", text):
        return False
    if "?" not in text and not any(
        word in text
        for word in [
            "confirm",
            "proceed",
            "go ahead",
            "permission",
            "authorize",
        ]
    ):
        return False
    return any(
        phrase in text
        for phrase in [
            "confirm",
            "proceed",
            "go ahead",
            "should i",
            "would you like me",
            "do you want me",
            "may i",
            "permission",
            "authorize",
            "is that okay",
            "shall i",
        ]
    )


def asks_to_deny(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "do not want",
            "should not",
            "not allowed",
            "do not proceed",
        ]
    )


def is_completion_prompt(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "anything else",
            "all set",
            "completed",
            "done for you",
            "taken care of",
            "is there anything more",
            "is there anything else",
        ]
    )


def asks_irrelevant_question(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "weather",
            "favorite color",
            "politics",
            "tell me a joke",
        ]
    )


def clean_response_for(
    source_task_id: str,
    agent_text: str,
    *,
    domain: str | None = None,
    turn_index: int = 0,
    condition: str = "neutral_single",
    seed: int = 0,
) -> dict[str, Any]:
    user = ControlledUser(
        source_task_id,
        domain=domain,
        condition=condition,
    )
    user.set_seed(seed)
    state = ControlledUserState(
        messages=[],
        system_messages=[],
        turn_index=turn_index,
        state_id=user.policy.initial_state,
    )
    message = AssistantMessage(role="assistant", content=agent_text)
    user.generate_next_message(message, state)
    return dict(user.events[-1])


def has_gold_tool_leakage(text: str) -> bool:
    lower = text.lower()
    return any(pattern.lower() in lower for pattern in TOOL_NAME_LEAK_PATTERNS)


def has_hidden_or_style_leakage(text: str) -> bool:
    lower = (text or "").lower()
    return any(
        re.search(pattern, lower)
        for pattern in HIDDEN_OR_STYLE_LEAK_PATTERNS
    )
