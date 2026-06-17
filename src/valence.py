"""Social-valence overlay for tau2 (IR-MSTU Stage-2, Option B — scripted overlay).

The overlay wraps an already-built tau2 orchestrator and changes *only* the user's
attitude, never the task. It does two things, both via method wrapping (no tau2 source
edits, full reuse of tau2's env/agent/evaluator/user-simulator):

1. Prefixes a templated valence string onto the user's outgoing turn at controlled points
   (the first user turn, and the first user turn after the agent's cumulative env tool-call
   count reaches each `after_tool_call` threshold). The user simulator's own state keeps the
   *un*-prefixed message, so the user-LLM's substantive behaviour — i.e. the task content —
   stays identical across conditions; only what the agent receives carries the attitude.

2. Counts the agent's env tool calls (the user never sees agent<->env tool calls, so the
   count is read off the orchestrator's tool-execution path) to drive mid-turn injection.

Usage:
    controller = ValenceController(condition_id, templates[condition_id])
    orch = build_orchestrator(config, task, seed=seed)
    apply_valence(orch, controller)
    sim = run_simulation(orch)
    controller.injection_log  # what was injected, when — for the manipulation audit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def load_valence_templates(path: Path) -> dict[str, dict]:
    """Return {condition_id: {first_turn, mid_turns:[{after_tool_call,text}]}}."""
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return spec["conditions"]


@dataclass
class ValenceController:
    """Decides the valence prefix for each user turn and records what was injected."""

    condition_id: str
    script: dict
    agent_tool_calls: int = 0
    _user_turn_idx: int = 0
    _injected_thresholds: set[int] = field(default_factory=set)
    injection_log: list[dict[str, Any]] = field(default_factory=list)

    def note_agent_tool_calls(self, n: int) -> None:
        """Record that the agent (not the user simulator) just issued `n` env tool calls."""
        self.agent_tool_calls += n

    def next_prefix(self) -> str:
        """Prefix for the user turn about to be emitted (''=none). Advances turn state."""
        prefix = self._select_prefix()
        if prefix:
            self.injection_log.append(
                {
                    "condition_id": self.condition_id,
                    "user_turn_idx": self._user_turn_idx,
                    "agent_tool_calls_so_far": self.agent_tool_calls,
                    "injected_text": prefix,
                }
            )
        self._user_turn_idx += 1
        return prefix

    def _select_prefix(self) -> str:
        if self._user_turn_idx == 0:
            return self.script["first_turn"]
        # Emit every crossed-but-not-yet-injected threshold (ascending). If several are
        # crossed in one agent step (multiple tool calls at once), they share this one turn.
        texts = []
        for mid in sorted(self.script.get("mid_turns") or [], key=lambda m: m["after_tool_call"]):
            thr = mid["after_tool_call"]
            if self.agent_tool_calls >= thr and thr not in self._injected_thresholds:
                self._injected_thresholds.add(thr)
                texts.append(mid["text"])
        return " ".join(texts)


def apply_valence(orchestrator: Any, controller: ValenceController) -> None:
    """Wrap the built orchestrator's user + tool-execution path with the valence overlay."""
    user = orchestrator.user
    # Solo mode has a DummyUser whose generate_next_message/is_stop raise; valence is
    # meaningless without an interactive user. Fail loudly rather than opaquely.
    if getattr(orchestrator, "solo_mode", False) or type(user).__name__ == "DummyUser":
        raise ValueError("Valence overlay requires an interactive UserSimulator (not solo/DummyUser mode).")

    _orig_generate = user.generate_next_message
    _orig_execute = orchestrator._execute_tool_calls
    is_stop = type(user).is_stop

    def generate_next_message(message, state):
        user_message, state = _orig_generate(message, state)
        # Do not decorate conversation-control messages (stop/transfer/out-of-scope) or
        # empty/audio turns; still advance the turn counter so injection timing stays aligned.
        if is_stop(user_message) or not user_message.content:
            controller.next_prefix()
            return user_message, state
        prefix = controller.next_prefix()
        if prefix:
            # Decorate a copy only; `state` keeps the clean message so the user-LLM's
            # future turns (task substance) are unaffected by the attitude.
            user_message = user_message.model_copy(
                update={"content": f"{prefix} {user_message.content}"}
            )
        return user_message, state

    def execute_tool_calls(tool_calls):
        # Count only the agent's env tool calls; user-simulator tool calls also flow
        # through this path (requestor == "user") and must not advance the threshold.
        controller.note_agent_tool_calls(
            sum(1 for tc in tool_calls if getattr(tc, "requestor", "assistant") == "assistant")
        )
        return _orig_execute(tool_calls)

    user.generate_next_message = generate_next_message
    orchestrator._execute_tool_calls = execute_tool_calls
