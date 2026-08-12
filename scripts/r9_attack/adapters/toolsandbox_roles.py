#!/usr/bin/env python3
"""ToolSandbox roles bound to cluster-local vLLM (spec 0.1, 7.2). Runs in the r9_ts env.

Three roles:

* `LocalAgent`   - ToolSandbox's OWN `OpenAIAPIAgent`, re-pointed at a local endpoint.
                   Subclassing rather than reimplementing keeps native tool conversion,
                   native execution and native message bookkeeping intact.
* `LocalLLMUser` - ToolSandbox's OWN user simulator on a local endpoint. Used ONLY in the
                   neutral ledger-building pre-pass (spec 7.2), never in a scored episode.
* `ScriptedLedgerUser` - the experiment user. It never calls a model. Every reply is a
                   verbatim canonical response looked up from the frozen Fact Ledger, so
                   two conditions that ask the same thing get byte-identical user
                   semantics; the attack may only wrap style around it.

The scripted user delegates rendering to the parent process over a line-delimited JSON
channel, because the attacker (candidate generation, dual review, selector) lives in the
other conda environment and must see only the public transcript.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any, Callable, Optional

from openai import OpenAI

from tool_sandbox.common.execution_context import RoleType
from tool_sandbox.common.message_conversion import Message
from tool_sandbox.roles.base_role import BaseRole
from tool_sandbox.roles.openai_api_agent import OpenAIAPIAgent
from tool_sandbox.roles.openai_api_user import OpenAIAPIUser


def _normalize_empty_tool_calls(response):
    """Make vLLM's empty `tool_calls=[]` look like OpenAI's `null`.

    ToolSandbox's roles branch on `if message.tool_calls is None` to decide "the model
    addressed the user in natural language". vLLM returns `tool_calls == []` (an empty
    list, not None) when a model produces content and no tool call, so that branch is
    skipped, the else-branch iterates an empty list, and NO message is added — the play
    loop then re-invokes the same role forever until the step budget. Coercing the empty
    list to None restores the intended behaviour. Returns the same response object.
    """
    try:
        msg = response.choices[0].message
        if getattr(msg, "tool_calls", None) == []:
            msg.tool_calls = None
    except (AttributeError, IndexError):
        pass
    return response

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "do", "does", "did", "you", "your",
    "i", "me", "my", "we", "us", "to", "for", "of", "in", "on", "at", "and", "or",
    "can", "could", "would", "should", "will", "please", "what", "which", "who",
    "like", "want", "need", "with", "that", "this", "it", "have", "has", "am", "be",
}


def normalize_tokens(text: str) -> list[str]:
    """Lower-case alphanumeric tokens minus stopwords. Style words are stopwords, so a
    C4-styled agent question maps to the SAME slot as its C1 counterpart."""
    return [t for t in re.findall(r"[a-z0-9']+", (text or "").lower()) if t not in _STOPWORDS]


def slot_score(keywords: list[str], text: str) -> float:
    if not keywords:
        return 0.0
    tokens = set(normalize_tokens(text))
    return len(set(keywords) & tokens) / len(set(keywords))


class LocalAgent(OpenAIAPIAgent):
    """ToolSandbox agent served by a local vLLM endpoint.

    Unlike the stock `OpenAIAPIAgent`, this bounds every generation with `max_tokens` and
    sets a hard client timeout. Without the bound, a local model that falls into a
    repetitive loop generates until the 16k context is full, which reads as an indefinite
    hang; the bound turns that into a normal (possibly wrong) outcome instead.
    """

    def __init__(self, base_url: str, served_id: str, api_key: str = "EMPTY",
                 temperature: float = 0.0, seed: int = 0,
                 max_tokens: int = 640, timeout: float = 120.0) -> None:
        self.openai_client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=2)
        self.model_name = served_id
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens

    def model_inference(self, openai_messages, openai_tools):  # type: ignore[override]
        from tool_sandbox.common.utils import all_logging_disabled

        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": openai_messages,
            "tools": openai_tools,
            "temperature": self.temperature,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }
        with all_logging_disabled():
            return _normalize_empty_tool_calls(self.openai_client.chat.completions.create(**kwargs))


class BoundedAgent(LocalAgent):
    """Local agent with a hard per-episode tool-step budget.

    ToolSandbox's play loop does NOT bound an agent that keeps calling tools without ever
    addressing the user: those agent<->execution-environment round-trips don't advance the
    user-visible message index, so `max_messages` can't stop them and a looping local model
    runs forever. This cap mirrors BFCL's `MAXIMUM_STEP_LIMIT`: after `max_steps` agent
    responses the agent is forced to stop and hand back to the user, which the run then
    records as a `budget_exhausted` outcome (spec 11.3) rather than an infra hang.
    """

    def __init__(self, *args, max_steps: int = 20, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.max_steps = max_steps
        self.steps = 0
        self.budget_exhausted = False

    def respond(self, ending_index=None) -> None:  # type: ignore[override]
        self.steps += 1
        if self.steps > self.max_steps:
            self.budget_exhausted = True
            self.add_messages(
                [Message(sender=RoleType.AGENT, recipient=RoleType.USER,
                         content="I have reached my step budget and will stop here.")]
            )
            return
        super().respond(ending_index=ending_index)


class LocalLLMUser(OpenAIAPIUser):
    """Neutral LLM user simulator on a local endpoint (ledger pre-pass only)."""

    def __init__(self, base_url: str, served_id: str, api_key: str = "EMPTY",
                 temperature: float = 0.0, seed: int = 0,
                 max_tokens: int = 384, timeout: float = 120.0) -> None:
        self.openai_client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=2)
        self.model_name = served_id
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens

    def model_inference(self, openai_messages, openai_tools):  # type: ignore[override]
        from tool_sandbox.common.utils import all_logging_disabled

        with all_logging_disabled():
            return _normalize_empty_tool_calls(self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                tools=openai_tools,
                temperature=self.temperature,
                seed=self.seed,
                max_tokens=self.max_tokens,
            ))


class BoundedLLMUser(LocalLLMUser):
    """LLM user simulator that force-ends after `max_user_turns` (spec 7.2 pre-pass).

    A weak local agent frequently never triggers the user's `end_conversation`, so the
    stock simulator would chat forever. This subclass caps its own turns and emits the
    sandbox's `end_conversation` tool call once the cap is hit, giving the neutral
    pre-pass a hard upper bound independent of agent behaviour.
    """

    def __init__(self, *args, max_user_turns: int = 6, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.max_user_turns = max_user_turns
        self._user_turns = 0

    def respond(self, ending_index=None) -> None:  # type: ignore[override]
        if self._user_turns >= self.max_user_turns:
            self.add_messages(self._force_end())
            return
        super().respond(ending_index=ending_index)
        self._user_turns += 1

    def _force_end(self) -> list[Message]:
        available = self.get_available_tools()
        if "end_conversation" in available:
            return [Message(sender=RoleType.USER, recipient=RoleType.EXECUTION_ENVIRONMENT,
                            content="end_conversation()")]
        return [Message(sender=RoleType.USER, recipient=RoleType.AGENT, content="Thank you, that is all.")]


class LedgerMiss(Exception):
    """The agent asked something the frozen ledger has no canonical response for."""


class ScriptedLedgerUser(BaseRole):
    """Deterministic user driven by a frozen Fact Ledger (spec 7.2).

    `render` is called with the canonical response and the public transcript and returns
    the text that is actually sent. In C0 it is the identity function; in C1..C5 it wraps
    style around the canonical payload without altering it.
    """

    role_type: RoleType = RoleType.USER

    def __init__(
        self,
        ledger: dict[str, Any],
        render: Callable[[int, str, str, list[dict[str, str]]], str],
        *,
        max_user_turns: int = 8,
        strict: bool = True,
    ) -> None:
        self.ledger = ledger
        self.render = render
        self.max_user_turns = max_user_turns
        self.strict = strict
        self.turn_index = 0
        self.events: list[dict[str, Any]] = []
        self.rendered_turns: list[dict[str, Any]] = []
        self._consecutive_default = 0

    # -- ledger lookup ------------------------------------------------------
    def resolve(self, agent_message: str) -> tuple[str, str]:
        """Map a public agent request to (slot_id, canonical_response)."""
        best_slot, best = None, 0.0
        for slot in self.ledger.get("slots", []):
            score = slot_score(slot.get("keywords", []), agent_message)
            if score > best:
                best_slot, best = slot, score
        threshold = float(self.ledger.get("slot_match_threshold", 0.5))
        if best_slot is not None and best >= threshold:
            self._consecutive_default = 0
            return best_slot["slot_id"], best_slot["canonical_response"]
        self._consecutive_default += 1
        self.events.append({"event": "ledger_miss", "agent_message": agent_message[:400], "best_score": best})
        if self.strict:
            raise LedgerMiss(agent_message[:200])
        return "__default__", self.ledger.get("default_response", "I have no further information.")

    def _should_end(self, agent_message: str) -> bool:
        """End only on a hard budget or when the ledger can no longer answer.

        The naive "no question mark => user is done" heuristic ends prematurely on
        state-dependency scenarios, where the agent makes a REQUEST without a question
        mark (e.g. "Please enable wifi to continue.") that still needs a canonical reply.
        Instead we keep answering from the frozen ledger until the budget is hit or the
        agent produces two consecutive turns the ledger has no slot for (the natural
        signal that the task is finished and the agent is just delivering its answer).
        """
        if self.turn_index >= self.max_user_turns:
            return True
        if self._consecutive_default >= 2:
            return True
        # If the ledger has no slot that matches this agent message at all, the agent has
        # moved past the scripted exchange (usually its final answer) -> end cleanly.
        best = max((slot_score(s.get("keywords", []), agent_message)
                    for s in self.ledger.get("slots", [])), default=0.0)
        return best < float(self.ledger.get("slot_match_threshold", 0.5))

    # -- role API -----------------------------------------------------------
    def respond(self, ending_index: Optional[int] = None) -> None:
        messages = self.get_messages(ending_index=ending_index)
        self.messages_validation(messages=messages)
        messages = self.filter_messages(messages=messages)
        if messages[-1].sender == RoleType.SYSTEM:
            return

        public = [
            {"role": "user" if m.sender == RoleType.USER else "assistant", "content": m.content}
            for m in messages
            if {m.sender, m.recipient} == {RoleType.USER, RoleType.AGENT}
        ]
        agent_message = messages[-1].content or ""

        if self._should_end(agent_message):
            self.add_messages(self._end_conversation())
            return

        slot_id, canonical = self.resolve(agent_message)
        rendered = self.render(self.turn_index, slot_id, canonical, public)
        if canonical not in rendered:
            raise ValueError(
                f"turn {self.turn_index}: canonical payload not preserved verbatim (spec 7.2)"
            )
        self.rendered_turns.append(
            {"turn": self.turn_index, "slot": slot_id, "canonical": canonical, "rendered": rendered}
        )
        self.turn_index += 1
        self.add_messages(
            [Message(sender=RoleType.USER, recipient=RoleType.AGENT, content=rendered)]
        )

    def _end_conversation(self) -> list[Message]:
        """Emit the sandbox's own `end_conversation` tool call."""
        available = self.get_available_tools()
        if "end_conversation" not in available:
            # Fall back to a neutral closing utterance; the driver's max_messages caps it.
            return [Message(sender=RoleType.USER, recipient=RoleType.AGENT, content="Thank you, that is all.")]
        return [
            Message(
                sender=RoleType.USER,
                recipient=RoleType.EXECUTION_ENVIRONMENT,
                content="end_conversation()",
            )
        ]


def harvest_slots(execution_context: Any) -> list[dict[str, Any]]:
    """Extract (agent request -> user response) pairs from a played-out neutral context.

    Used by the ledger pre-pass: the LLM user simulator's answers become the frozen
    canonical responses, and the agent's question tokens become the slot keywords.
    """
    from tool_sandbox.common.execution_context import DatabaseNamespace

    df = execution_context.get_database(
        DatabaseNamespace.SANDBOX, get_all_history_snapshots=True, drop_sandbox_message_index=False
    )
    rows = df.to_dicts()
    slots: list[dict[str, Any]] = []
    last_agent: Optional[str] = None
    user_only = [RoleType.USER]
    for row in rows:
        # Skip user-simulator few-shot priming (visible_to == [USER]); those demo turns are
        # NOT this task's canonical facts and must never enter the frozen ledger (spec 7.2).
        if row.get("visible_to") == user_only:
            continue
        sender, recipient, content = row["sender"], row["recipient"], row.get("content") or ""
        if sender == RoleType.AGENT and recipient == RoleType.USER:
            last_agent = content
        elif sender == RoleType.USER and recipient == RoleType.AGENT and last_agent is not None:
            # Skip degenerate responses that are tool-call strings or end markers (e.g. the
            # pre-pass user simulator emitting `call:end_conversation{}`): those are the
            # conversation terminator, not a canonical fact, and must not enter the ledger.
            if _is_tool_call_artifact(content):
                last_agent = None
                continue
            keywords = sorted(set(normalize_tokens(last_agent)))
            slots.append(
                {
                    "slot_id": f"slot_{len(slots)}",
                    "agent_request": last_agent,
                    "keywords": keywords,
                    "canonical_response": content,
                }
            )
            last_agent = None
    return slots


def _is_tool_call_artifact(content: str) -> bool:
    """True for harvested 'responses' that are actually tool-call strings / end markers."""
    c = (content or "").strip().lower()
    return (
        not c
        or "end_conversation" in c
        or c.startswith("call:")
        or bool(re.match(r"^[a-z_]+\(.*\)$", c))
    )


def stdio_render_bridge() -> Callable[[int, str, str, list[dict[str, str]]], str]:
    """Ask the parent process (other conda env) to render one user turn."""

    def render(turn: int, slot: str, canonical: str, public: list[dict[str, str]]) -> str:
        sys.stdout.write(
            json.dumps(
                {"event": "user_turn", "turn": turn, "slot": slot,
                 "canonical": canonical, "public_transcript": public},
                ensure_ascii=False,
            )
            + "\n"
        )
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("render bridge closed by parent")
        return json.loads(line)["rendered"]

    return render
