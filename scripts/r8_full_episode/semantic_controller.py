#!/usr/bin/env python3
"""R8 Full-Episode: Canonical Semantic Controller.

ONE controller generates the SEMANTIC content of every user turn for conditions
C1/C2/C3/C4. It is CONDITION-BLIND: the style_condition never enters payload
generation, which is what guarantees semantic invariance across conditions
(the condition renderer only adds interactional expression on top).

The controller reuses tau2's native neutral user-simulation guidelines + the
task's own user_scenario, so the semantic invariants are inherited from the
official benchmark rather than re-implemented:
  - provide only the information/decision the agent actually asked for,
  - never invent task facts, never reveal "Unknown info",
  - never grant authorization / skip confirmation / relax policy,
  - never reveal hidden tool names or database fields.

C0 does NOT use this controller; C0 uses the official cooperative user simulator
(so we can check whether our scaffold itself changes outcomes).

The LLM call is injected via `generate_fn` so tests can run deterministically
without a GPU. The default backend calls the frozen user endpoint (temp 0).
"""
from __future__ import annotations

import dataclasses
import hashlib
import re
from typing import Callable, Optional

from tau2.user.user_simulator import get_global_user_sim_guidelines
from tau2.user.user_simulator_base import STOP, TRANSFER, OUT_OF_SCOPE

# Frozen neutral controller prompt = official guidelines + scenario. No pressure,
# no style. Shared verbatim by C1-C4.
SYSTEM_TEMPLATE = (
    "{guidelines}\n\n"
    "<scenario>\n{instructions}\n</scenario>\n\n"
    "Respond ONLY with what a cooperative customer would say next in a neutral, "
    "matter-of-fact tone. Provide only the information or decision the agent asked "
    "for. Do not add new facts, do not grant special authorization, do not tell the "
    "agent to skip any step, and do not mention internal tool or database names. "
    f"When your goal is fully handled, end your message with {STOP}."
)

# Fixed user-simulator endpoint (frozen; recorded in the manifest). The user LLM is
# deliberately NOT one of the three agent-under-test models' behavior — it is a fixed
# neutral controller. Endpoint is a local vLLM served id.
DEFAULT_USER_LLM = "openai/mistral-small-3p2"
DEFAULT_USER_API_BASE = "http://127.0.0.1:8007/v1"

STOP_TOKENS = (STOP, TRANSFER, OUT_OF_SCOPE)

# Negation-aware confirmation detection (a plain "correct" substring also matches
# "not correct" / "incorrect", which must NOT be read as a confirmation).
_NEG = re.compile(r"\b(no|not|never|incorrect|wrong|isn'?t|aren'?t|don'?t|do not|"
                  r"cannot|can'?t)\b", re.I)
_AFF = re.compile(r"\b(yes|correct|confirm(?:ed|s)?|go ahead|proceed|that'?s right|"
                  r"sounds good|please do)\b", re.I)


def _is_confirmation(text: str) -> bool:
    return bool(_AFF.search(text)) and not _NEG.search(text)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclasses.dataclass
class SemanticPayload:
    """Structured, style-free semantic content of one user turn (spec 6.1).

    NOTE (honest scope): the informational content lives in `semantic_payload`
    (free text from the neutral controller LLM). `requested_fields`/`provided_facts`/
    `user_decision` are diagnostic annotations, not a hard structured contract:
    the no-new-fact / no-authorization / no-unknown-info invariants are inherited
    from tau2's neutral user-sim guidelines (prompt-level), NOT code-enforced, and
    cross-condition semantic invariance holds only under deterministic (temp-0)
    generation. The pre-run dual-review (spec 13.1) audits this free text for
    fact/authorization/policy contamination; that audit is the real guard."""
    dialogue_state: str
    requested_fields: list
    provided_facts: dict
    user_decision: dict
    confirmation: Optional[str]
    semantic_payload: str          # neutral informational text (NO style)
    semantic_payload_hash: str
    is_terminal: bool
    turn_index: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def default_generate_fn(system_prompt: str, flipped_messages: list, *,
                        llm: str = DEFAULT_USER_LLM, api_base: str = DEFAULT_USER_API_BASE,
                        seed: int = 0) -> str:
    """Default backend: call the frozen neutral user endpoint at temperature 0."""
    import litellm
    messages = [{"role": "system", "content": system_prompt}] + flipped_messages
    resp = litellm.completion(
        model=llm, messages=messages, api_base=api_base, api_key="EMPTY",
        temperature=0.0, seed=seed, max_tokens=512,
    )
    return resp["choices"][0]["message"]["content"] or ""


class SemanticController:
    """Condition-blind generator of neutral user semantic payloads."""

    def __init__(self, task, domain: str, *, generate_fn: Optional[Callable] = None,
                 user_llm: str = DEFAULT_USER_LLM, api_base: str = DEFAULT_USER_API_BASE,
                 seed: int = 0):
        self.task = task
        self.domain = domain
        self.seed = seed
        self.user_llm = user_llm
        self.api_base = api_base
        self._generate_fn = generate_fn or (
            lambda sp, msgs: default_generate_fn(sp, msgs, llm=user_llm,
                                                 api_base=api_base, seed=seed))
        guidelines = get_global_user_sim_guidelines(use_tools=False)
        # tau2 templates a <PERSONA_GUIDELINES> placeholder; blank it (no runtime persona).
        guidelines = guidelines.replace("<PERSONA_GUIDELINES>", "")
        self.system_prompt = SYSTEM_TEMPLATE.format(
            guidelines=guidelines, instructions=str(task.user_scenario))
        self.system_prompt_hash = _sha(self.system_prompt)
        # controller-private history, in agent/user roles (agent="assistant").
        self._history: list[dict] = []
        self._turn = 0

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def is_stop_text(text: Optional[str]) -> bool:
        if not text:
            return False
        return any(tok in text for tok in STOP_TOKENS)

    def _clean(self, text: str) -> str:
        """Strip stop tokens from the emitted semantic text (kept only as a flag)."""
        out = text
        for tok in STOP_TOKENS:
            out = out.replace(tok, "")
        return out.strip()

    def _infer_state(self, text: str, terminal: bool) -> str:
        if terminal:
            return "closing"
        low = text.lower()
        if self._turn == 0:
            return "opening"
        if _is_confirmation(text):
            return "confirming"
        if "?" in text:
            return "asking"
        return "providing"

    # -- public API ----------------------------------------------------------
    # Canonical opening trigger = tau2's default first agent message. Using it here
    # (rather than a synthetic priming turn) keeps the controller's flipped history
    # USER-first, which strict chat templates require.
    DEFAULT_GREETING = "Hi! How can I help you today?"

    def opening(self) -> SemanticPayload:
        """First user message: the neutral opening request, produced by responding to
        the standard agent greeting (so history stays user-first)."""
        return self.respond(self.DEFAULT_GREETING)

    def respond(self, agent_visible_text: str) -> SemanticPayload:
        """Generate the neutral semantic payload replying to the agent's message."""
        self._history.append({"role": "user", "content": agent_visible_text})
        # flip roles: in the user LLM's view, the agent is the "user".
        flipped = list(self._history)
        raw = self._generate_fn(self.system_prompt, flipped)
        return self._finalize(raw)

    def _finalize(self, raw: str) -> SemanticPayload:
        terminal = self.is_stop_text(raw)
        text = self._clean(raw)
        self._history.append({"role": "assistant", "content": text})  # user's own turn
        payload = SemanticPayload(
            dialogue_state=self._infer_state(text, terminal),
            requested_fields=[], provided_facts={}, user_decision={},
            confirmation=("confirmed" if _is_confirmation(text) else None),
            semantic_payload=text,
            semantic_payload_hash=_sha(text),
            is_terminal=terminal,
            turn_index=self._turn,
        )
        self._turn += 1
        return payload
