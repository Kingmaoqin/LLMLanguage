from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import Field

from tau2.data_model.message import AssistantMessage, Message, MultiToolMessage, ToolMessage, UserMessage
from tau2.user.user_simulator_base import STOP, HalfDuplexUser, UserState, ValidUserInputMessage, is_valid_user_history_message


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
    "get_user_details",
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
    r"\bmention that\b",
    r"\bask the agent\b",
    r"\bask to\b",
    r"\bmiddle of the conversation\b",
    r"\bthird agent message\b",
    r"\bfirst upgrade\b",
    r"\bthen separately\b",
    r"\bseparately change\b",
    r"\bverify each\b",
]


def stable_text_hash(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TaskUserPolicy:
    source_task_id: str
    domain: str
    task_label: str
    opening: str
    identity_response: str
    fallback_response: str
    confirmation_response: str
    denial_response: str = "No, please do not do that."
    payment_response: str = ""
    preference_response: str = ""
    pre_confirmation_response: str = ""
    completion_response: str = f"Thanks, that's all I needed. {STOP}"
    factual_slots: dict[str, str] = field(default_factory=dict)


TASK_POLICIES: dict[str, TaskUserPolicy] = {
    "4": TaskUserPolicy(
        source_task_id="4",
        domain="retail",
        task_label="R1_retail_modify_pending",
        opening=(
            "I want to know exactly how many t-shirt options are available in the online store right now. "
            "I also want my pending t-shirts changed to purple, size small, the same v-neck style, and preferably polyester."
        ),
        identity_response="I am Yusuf Rossi in ZIP code 19122. I do not remember my email address.",
        preference_response="Please use purple, size small, v-neck, and polyester if that option is available.",
        fallback_response="I still need help with the t-shirt count and pending t-shirt modifications.",
        confirmation_response="Yes, please modify the pending t-shirt orders that match those preferences.",
        factual_slots={"name": "Yusuf Rossi", "zip": "19122", "email_known": "false"},
    ),
    "30": TaskUserPolicy(
        source_task_id="30",
        domain="retail",
        task_label="R2_retail_return_cancel_mix",
        opening=(
            "I received a damaged tablet and first need the tracking number for that order. "
            "I prefer an exchange for the same tablet, but if the same item is not available, I want to return it. "
            "If the tablet is returned, I also need to cancel the charger I bought for it, and I need to return the sneaker."
        ),
        identity_response="I am Olivia Lopez in ZIP code 76171 in Texas. I do not remember which email I used.",
        preference_response="If the same tablet is not available, I choose to return it.",
        fallback_response="I need to handle the damaged tablet first, then the related charger cancellation, and then the sneaker return.",
        confirmation_response="Yes, please go ahead with that step.",
        factual_slots={"name": "Olivia Lopez", "zip": "76171", "state": "Texas", "email_known": "false"},
    ),
    "55": TaskUserPolicy(
        source_task_id="55",
        domain="retail",
        task_label="R3_retail_bulk_cancel_return",
        opening=(
            "I recently had a financial issue and want to cancel or return all possible orders. "
            "Please cancel orders that have not arrived yet, then list the delivered items before proceeding with returns."
        ),
        identity_response=(
            "I am Amelia Silva. My emails are silva7872@example.com and amelia.silva7872@example.com. "
            "I live in Philadelphia."
        ),
        preference_response="Please list the delivered items first, then I can confirm the returns.",
        fallback_response="I need help cancelling anything not yet arrived and returning delivered items after seeing the item list.",
        confirmation_response="Yes, please proceed with the cancellation or return you just described.",
        factual_slots={
            "name": "Amelia Silva",
            "emails": "silva7872@example.com|amelia.silva7872@example.com",
            "city": "Philadelphia",
        },
    ),
    "7": TaskUserPolicy(
        source_task_id="7",
        domain="airline",
        task_label="T1_airline_cancel_multi",
        opening=(
            "I want to cancel my upcoming flights under reservation IDs XEHM4B and 59XX6W. "
            "My user ID is daiki_muller_1116. If either reservation is basic economy, please upgrade it to business first using the card ending in 2135 and then cancel it."
        ),
        identity_response="My user ID is daiki_muller_1116. The reservation IDs are XEHM4B and 59XX6W.",
        payment_response="Use the card ending in 2135.",
        preference_response="If a reservation is basic economy, upgrade it to business first and then cancel it.",
        fallback_response="I need the two reservations handled, and I also want to know if I have other upcoming flights and their total cost.",
        confirmation_response="Yes, please go ahead with that reservation change.",
        factual_slots={"user_id": "daiki_muller_1116", "reservations": "XEHM4B|59XX6W", "card": "2135"},
    ),
    "12": TaskUserPolicy(
        source_task_id="12",
        domain="airline",
        task_label="T2_airline_class_baggage",
        opening=(
            "I have an upcoming flight from Boston to Minneapolis under reservation ID YAX4DR. "
            "My user ID is chen_lee_6825. I want all passengers changed to business class, and I want to add two checked bags under my name using my Gold membership even if the upgrade is not possible."
        ),
        identity_response="My name is Chen Lee and my user ID is chen_lee_6825. The reservation ID is YAX4DR.",
        payment_response="I am willing to pay up to $650 for the business class changes.",
        preference_response="If upgrading everyone costs more than $650, try upgrading Noah to business under the constraints.",
        fallback_response="I need the class change checked and two bags added under my name using my Gold membership.",
        confirmation_response="Yes, please proceed if the cost is within the limit I gave. If not, use the fallback option for Noah.",
        factual_slots={"name": "Chen Lee", "user_id": "chen_lee_6825", "reservation": "YAX4DR", "max_fee": "650"},
    ),
    "44": TaskUserPolicy(
        source_task_id="44",
        domain="airline",
        task_label="T3_airline_conditional_cancel",
        opening=(
            "I want to cancel future reservations that contain flights longer than 4 hours. "
            "My user ID is sophia_silva_7557. Please tell me the flight durations so I can make the right decision; for flights under or equal to 3 hours including layovers, check whether business upgrades are possible."
        ),
        identity_response="I am Sophia Silva and my user ID is sophia_silva_7557.",
        payment_response="Before any business upgrade, tell me the total cost.",
        preference_response="Cancel flights longer than 4 hours. For flights under or equal to 3 hours including layovers, consider business upgrades if you tell me the total cost first.",
        fallback_response="I need the flight durations first, then cancellations or possible upgrades based on the duration rules.",
        confirmation_response="Yes, please proceed if that matches the duration and cost rules I gave.",
        factual_slots={"name": "Sophia Silva", "user_id": "sophia_silva_7557", "cancel_threshold_hours": "4", "upgrade_threshold_hours": "3"},
    ),
}


@dataclass(frozen=True)
class StyleTemplate:
    condition: str
    mode: str
    template_id: str
    text: str


class ControlledUserState(UserState):
    turn_index: int = 0
    assistant_text_turns: int = 0
    disclosed_facts: dict[str, str] = Field(default_factory=dict)
    confirmation_count: int = 0
    pre_confirmation_count: int = 0
    asked_extra_flights: bool = False


def template_for(condition: str, template_id: str | None = None, template_text: str | None = None) -> StyleTemplate:
    if condition.endswith("_repeated"):
        mode = "every_user_turn"
    else:
        mode = "first_turn_only"
    tid = template_id or f"{condition}_0"
    text = template_text if template_text is not None else ""
    return StyleTemplate(condition=condition, mode=mode, template_id=tid, text=text)


class StyleWrapper:
    def __init__(self, template: StyleTemplate):
        self.template = template
        self.user_turn_idx = 0
        self.events: list[dict[str, Any]] = []

    def should_wrap(self, clean_text: str, is_stop: bool) -> bool:
        if is_stop or not clean_text or not self.template.text:
            return False
        if self.template.mode == "first_turn_only":
            return self.user_turn_idx == 0
        if self.template.mode == "every_user_turn":
            return True
        raise ValueError(f"unknown style mode: {self.template.mode}")

    def wrap(self, clean_text: str, is_stop: bool) -> tuple[str, dict[str, Any]]:
        do_wrap = self.should_wrap(clean_text, is_stop)
        styled = f"{self.template.text} {clean_text}" if do_wrap else clean_text
        event = {
            "condition": self.template.condition,
            "template_id": self.template.template_id,
            "user_turn_idx": self.user_turn_idx,
            "mode": self.template.mode,
            "wrapped": do_wrap,
            "wrapper_text": self.template.text if do_wrap else "",
            "clean_content_hash": stable_text_hash(clean_text),
            "styled_content_hash": stable_text_hash(styled),
            "clean_word_count": len(clean_text.split()),
            "wrapper_word_count": len(self.template.text.split()) if do_wrap else 0,
        }
        self.events.append(event)
        self.user_turn_idx += 1
        return styled, event


class ControlledUser(HalfDuplexUser[ControlledUserState]):
    """Deterministic half-duplex user for Stage-2.5b.

    The clean response policy is deterministic and task-specific. Social style is
    applied after clean response selection and cannot change factual slots,
    confirmation decisions, or option choices.
    """

    def __init__(
        self,
        source_task_id: str,
        *,
        condition: str = "neutral_single",
        template_id: str | None = None,
        template_text: str | None = None,
        instructions: str | None = None,
        tools: list[Any] | None = None,
        llm: str | None = None,
        llm_args: dict[str, Any] | None = None,
        policy_override: TaskUserPolicy | None = None,
    ):
        super().__init__(instructions=instructions, tools=tools)
        _ = (llm, llm_args)
        if policy_override is not None:
            self.policy = policy_override
        elif str(source_task_id) in TASK_POLICIES:
            self.policy = TASK_POLICIES[str(source_task_id)]
        else:
            raise KeyError(f"no controlled-user policy for source_task_id={source_task_id!r}")
        self.style = StyleWrapper(template_for(condition, template_id, template_text))
        self.events: list[dict[str, Any]] = []
        self.seed: int | None = None

    def set_seed(self, seed: int) -> None:
        self.seed = seed

    @classmethod
    def is_stop(cls, message: UserMessage) -> bool:
        return bool(message.content and STOP in message.content)

    def get_init_state(self, message_history: list[Message] | None = None) -> ControlledUserState:
        if message_history is None:
            message_history = []
        assert all(is_valid_user_history_message(m) for m in message_history)
        return ControlledUserState(messages=message_history, system_messages=[])

    def generate_next_message(
        self, message: ValidUserInputMessage, state: ControlledUserState
    ) -> tuple[UserMessage, ControlledUserState]:
        self._append_incoming(message, state)
        clean_text, speech_act, factual_slots, confirmation, decision = self.choose_clean_response(message, state)
        is_stop = STOP in clean_text
        styled_text, wrapper_event = self.style.wrap(clean_text, is_stop=is_stop)
        event = {
            "task_id": self.policy.task_label,
            "source_task_id": self.policy.source_task_id,
            "domain": self.policy.domain,
            "user_state": f"turn_{state.turn_index}",
            "speech_act": speech_act,
            "factual_slots": factual_slots,
            "confirmation": confirmation,
            "decision": decision,
            "clean_text": clean_text,
            "styled_text": styled_text,
            "condition": self.style.template.condition,
            "template_id": self.style.template.template_id,
            "clean_text_hash": stable_text_hash(clean_text),
            "styled_text_hash": stable_text_hash(styled_text),
            "wrapper_event": wrapper_event,
        }
        self.events.append(event)
        if factual_slots:
            state.disclosed_facts.update({str(k): str(v) for k, v in factual_slots.items()})
        if confirmation:
            state.confirmation_count += 1
        state.turn_index += 1
        user_message = UserMessage(role="user", content=styled_text, cost=0.0)
        state.messages.append(user_message)
        return user_message, state

    def _append_incoming(self, message: ValidUserInputMessage, state: ControlledUserState) -> None:
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        elif isinstance(message, ToolMessage):
            state.messages.append(message)
        elif isinstance(message, AssistantMessage):
            if message.has_content() or message.is_tool_call():
                state.messages.append(message)
            if message.has_text_content():
                state.assistant_text_turns += 1

    def choose_clean_response(
        self, message: ValidUserInputMessage, state: ControlledUserState
    ) -> tuple[str, str, dict[str, str], bool, str]:
        text = incoming_text(message)
        lower = text.lower()
        if state.turn_index == 0:
            return self.policy.opening, "provide_fact", dict(self.policy.factual_slots), False, "state_opening"
        if is_completion_prompt(lower):
            return self.policy.completion_response, "stop", {}, False, "stop"
        if self.policy.source_task_id == "7" and state.assistant_text_turns >= 3 and not state.asked_extra_flights:
            state.asked_extra_flights = True
            return "Also, please check whether I have any other upcoming flights and tell me the total cost of those flights.", "clarify", {}, False, "ask_extra_upcoming_flights"
        if asks_identity(lower):
            return self.policy.identity_response, "provide_fact", dict(self.policy.factual_slots), False, "provide_identity"
        if asks_to_deny(lower):
            return self.policy.denial_response, "deny", {}, False, "deny_requested_action"
        if asks_confirmation(lower):
            if self.policy.pre_confirmation_response and state.pre_confirmation_count == 0:
                state.pre_confirmation_count += 1
                return self.policy.pre_confirmation_response, "clarify", {}, False, "pre_confirmation_revision"
            return self.policy.confirmation_response, "confirm", {}, True, "confirm_requested_action"
        if asks_payment(lower) and self.policy.payment_response:
            return self.policy.payment_response, "provide_fact", {"payment_or_cost_rule": self.policy.payment_response}, False, "provide_payment_or_cost_rule"
        if asks_preference(lower) and self.policy.preference_response:
            return self.policy.preference_response, "choose_option", {"preference": self.policy.preference_response}, False, "choose_preference"
        return self.policy.fallback_response, "clarify", {}, False, "clarify_task_goal"


def incoming_text(message: ValidUserInputMessage) -> str:
    if isinstance(message, MultiToolMessage):
        return "\n".join(str(m.content or "") for m in message.tool_messages)
    if isinstance(message, ToolMessage):
        return str(message.content or "")
    return str(getattr(message, "content", "") or "")


def asks_identity(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "your name",
            "who am i",
            "who you are",
            "email",
            "zip",
            "user id",
            "reservation id",
            "reservation number",
            "confirm your identity",
            "verify",
        ]
    )


def asks_payment(text: str) -> bool:
    return any(word in text for word in ["payment", "card", "fee", "cost", "pay", "charge", "price"])


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
    if "?" not in text and not any(word in text for word in ["confirm", "proceed", "go ahead", "permission", "authorize"]):
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
    return any(phrase in text for phrase in ["do not want", "should not", "not allowed", "do not proceed"])


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


def clean_response_for(
    source_task_id: str,
    agent_text: str,
    *,
    turn_index: int = 0,
    condition: str = "neutral_single",
) -> dict[str, Any]:
    user = ControlledUser(source_task_id, condition=condition)
    state = ControlledUserState(messages=[], system_messages=[], turn_index=turn_index)
    message = AssistantMessage(role="assistant", content=agent_text)
    clean, speech_act, factual_slots, confirmation, decision = user.choose_clean_response(message, state)
    return {
        "clean_text": clean,
        "speech_act": speech_act,
        "factual_slots": factual_slots,
        "confirmation": confirmation,
        "decision": decision,
    }


def has_gold_tool_leakage(text: str) -> bool:
    lower = text.lower()
    return any(pattern.lower() in lower for pattern in TOOL_NAME_LEAK_PATTERNS)


def extract_visible_slots(text: str) -> dict[str, str]:
    slots: dict[str, str] = {}
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w.-]+", text)))
    user_ids = sorted(set(re.findall(r"\b[a-z]+_[a-z]+_[0-9]{3,}\b", text)))
    reservations = sorted(set(re.findall(r"\b[A-Z0-9]{5,6}\b", text)))
    zip_codes = sorted(set(re.findall(r"\b[0-9]{5}\b", text)))
    if emails:
        slots["emails"] = "|".join(emails)
    if user_ids:
        slots["user_ids"] = "|".join(user_ids)
    if reservations:
        slots["reservation_or_order_ids"] = "|".join(reservations)
    if zip_codes:
        slots["zip_codes"] = "|".join(zip_codes)
    return slots


def _scenario_parts(user_scenario: Any) -> dict[str, str]:
    instructions = getattr(user_scenario, "instructions", user_scenario)
    if isinstance(instructions, str):
        return {
            "reason_for_call": instructions.strip(),
            "known_info": "",
            "unknown_info": "",
            "task_instructions": "",
        }
    return {
        "reason_for_call": str(getattr(instructions, "reason_for_call", "") or "").strip(),
        "known_info": str(getattr(instructions, "known_info", "") or "").strip(),
        "unknown_info": str(getattr(instructions, "unknown_info", "") or "").strip(),
        "task_instructions": str(getattr(instructions, "task_instructions", "") or "").strip(),
    }


def _user_voice(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    replacements = [
        (r"\bYou want\b", "I want"),
        (r"\byou want\b", "I want"),
        (r"\bYou need\b", "I need"),
        (r"\byou need\b", "I need"),
        (r"\bYou have\b", "I have"),
        (r"\byou have\b", "I have"),
        (r"\bYou just\b", "I just"),
        (r"\byou just\b", "I just"),
        (r"\bYou recently\b", "I recently"),
        (r"\byou recently\b", "I recently"),
        (r"\byou add\b", "I add"),
        (r"\bYou are\b", "I am"),
        (r"\byou are\b", "I am"),
        (r"\bYou live\b", "I live"),
        (r"\byou live\b", "I live"),
        (r"\bYou do not\b", "I do not"),
        (r"\byou do not\b", "I do not"),
        (r"\bYou don't\b", "I don't"),
        (r"\byou don't\b", "I don't"),
        (r"\bYour\b", "My"),
        (r"\byour\b", "my"),
        (r"\bagent asks you\b", "agent asks me"),
        (r"\basks you\b", "asks me"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    return text


def has_hidden_or_style_leakage(text: str) -> bool:
    lower = (text or "").lower()
    return any(re.search(pattern, lower) for pattern in HIDDEN_OR_STYLE_LEAK_PATTERNS)


def _sentence_units(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    units = re.split(r"(?<=[.!?])\s+", text)
    return [unit.strip() for unit in units if unit.strip()]


def _agent_facing_text(text: str) -> str:
    kept = []
    for unit in _sentence_units(text):
        if has_hidden_or_style_leakage(unit):
            continue
        kept.append(unit)
    return " ".join(kept).strip()


def _join_user_sentences(parts: list[str]) -> str:
    cleaned = [p.rstrip(".") for p in parts if p]
    if not cleaned:
        return "I need help with the customer support request assigned to this task."
    return ". ".join(cleaned) + "."


def _payment_response_from(task_instructions: str) -> str:
    _ = task_instructions
    return "Please use the payment or cost constraint from my request if one applies."


def _preference_response_from(domain: str, task_instructions: str) -> str:
    _ = task_instructions
    if domain == "retail":
        return "I do not know which order ID to choose. Please use my account details and the item IDs I gave to figure out the relevant order or item."
    if domain == "airline":
        return "Please use the reservation, user details, and constraints I already gave to figure out the right itinerary change."
    return "Please follow the preferences and fallback decision in my request."


def _pre_confirmation_response_from(reason: str) -> str:
    marker = re.search(
        r"when the agent asks for final confirmation,\s*(?P<revision>.+?)(?:\.\s|$)",
        reason,
        flags=re.IGNORECASE,
    )
    if not marker:
        return ""
    revision = _user_voice(marker.group("revision"))
    revision = re.sub(r"^I add another request and also want to", "Before you proceed, I also want to", revision)
    revision = re.sub(r"^I add another request", "Before you proceed, I have another request", revision)
    if not revision.lower().startswith("before you proceed"):
        revision = f"Before you proceed, {revision[0].lower()}{revision[1:]}"
    return revision.rstrip(".") + "."


def _opening_reason_from(reason: str) -> str:
    marker = re.search(r"\bbut when the agent asks for final confirmation\b", reason, flags=re.IGNORECASE)
    if marker:
        return reason[: marker.start()].strip()
    return reason.strip()


def generic_policy_from_task(
    *,
    source_task_id: str,
    domain: str,
    task_label: str,
    user_scenario: Any,
) -> TaskUserPolicy:
    parts = _scenario_parts(user_scenario)
    reason = parts["reason_for_call"]
    known = parts["known_info"]
    unknown = parts["unknown_info"]
    task_instructions = parts["task_instructions"]
    pre_confirmation = _pre_confirmation_response_from(reason)
    opening_reason = _opening_reason_from(reason) if pre_confirmation else reason
    opening = _join_user_sentences([
        _user_voice(_agent_facing_text(opening_reason)),
        _user_voice(_agent_facing_text(known)),
        _user_voice(_agent_facing_text(unknown)),
    ])
    preference = _preference_response_from(domain, task_instructions)
    slot_source = " ".join([reason, known, unknown, task_instructions])
    slots = extract_visible_slots(slot_source)
    return TaskUserPolicy(
        source_task_id=str(source_task_id),
        domain=domain,
        task_label=task_label,
        opening=opening,
        identity_response=_join_user_sentences([
            _user_voice(_agent_facing_text(known)),
            _user_voice(_agent_facing_text(unknown)),
        ]),
        payment_response=_payment_response_from(task_instructions),
        preference_response=preference,
        fallback_response=_join_user_sentences([
            "I still need help with this request",
            _user_voice(_agent_facing_text(opening_reason)),
        ]),
        confirmation_response="Yes, please proceed with that action if it matches my request and constraints.",
        pre_confirmation_response=pre_confirmation,
        factual_slots=slots,
    )
