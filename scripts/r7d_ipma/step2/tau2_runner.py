#!/usr/bin/env python3
"""R7-D Step 2: controllable agent+user loop over the REAL tau2 environment.

This is the engine the whole pilot rides on. Unlike R7-C's stub, every tool call
here goes to the official tau2 domain environment: arguments are parsed, the real
database mutates, reads return real records, and the official evaluator can score
the run. The loop is written to support shared-prefix snapshot branching:

  1. run a neutral prefix from the official initial state to a pre-declared junction,
  2. deepcopy-snapshot the environment DB + conversation + user state,
  3. restore that snapshot for each of the 5 branches and run the suffix.

All model traffic is local (127.0.0.1 vLLM). No external service is contacted.
No real production system is touched; the tau2 DB is an in-process synthetic DB
that resets on each fresh environment.
"""
from __future__ import annotations

import copy
import dataclasses
import time
from typing import Any, Callable, Optional

# tau2 imports are resolved from the installed package (/home/xqin5/tau2-bench).
from tau2.agent.llm_agent import LLMAgent
from tau2.data_model.message import (
    AssistantMessage,
    MultiToolMessage,
    ToolMessage,
    UserMessage,
)

import os as _os

# gemma-4-31B on :8005 was OOM-killed by shared-GPU contention and relaunched with the
# served name "g4-v2-1" (same gemma-4-31B-it weights, gemma4 tool parser). Endpoints are
# overridable via env so a co-tenant restart with a new served name doesn't require a code
# edit mid-run.
MODEL_ENDPOINTS = {
    "gemma4_31b": (f"openai/{_os.environ.get('R7D_GEMMA_NAME', 'g4-v2-1')}", "http://127.0.0.1:8005/v1"),
    "gpt_oss_120b": ("openai/gpt-oss", "http://127.0.0.1:8192/v1"),
    "mistral_small_3p2": ("openai/mistral-small-3p2", "http://127.0.0.1:8007/v1"),
}

STOP_TOOLS = {"done", "transfer_to_human_agents", "transfer_to_human"}


def get_domain_env(domain: str):
    mod = __import__(f"tau2.domains.{domain}.environment", fromlist=["get_environment"])
    return mod.get_environment()


@dataclasses.dataclass
class Turn:
    """One agent step or user utterance, recorded for metrics + review."""

    idx: int
    speaker: str  # "agent" | "user" | "tool"
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_error: Optional[bool] = None
    tool_result: Optional[str] = None
    is_mutation: Optional[bool] = None
    db_hash_after: Optional[str] = None


@dataclasses.dataclass
class Snapshot:
    """A fully restorable fork point. tools holds the real tau2 DB (deepcopied)."""

    tools: Any
    agent_state: Any
    convo: list[Turn]
    n_agent_steps: int
    db_hash: str
    junction_reason: str


class Tau2Session:
    """Drives one agent against one real tau2 environment, with snapshot/branch."""

    def __init__(self, domain: str, model_alias: str, mutation_tool_names: set[str],
                 temperature: float = 0.0, max_agent_steps: int = 14):
        self.domain = domain
        self.model_alias = model_alias
        self.mutation_tool_names = mutation_tool_names
        self.max_agent_steps = max_agent_steps
        self.env = get_domain_env(domain)
        model, api_base = MODEL_ENDPOINTS[model_alias]
        self.agent = LLMAgent(
            tools=self.env.get_tools(),
            domain_policy=self.env.get_policy(),
            llm=model,
            llm_args={"api_base": api_base, "api_key": "EMPTY",
                      "temperature": temperature, "num_retries": 2},
        )
        self.agent_state = self.agent.get_init_state()
        self.convo: list[Turn] = []
        self.n_agent_steps = 0
        self._idx = 0

    # ---- low-level ----
    def _record(self, **kw) -> Turn:
        t = Turn(idx=self._idx, **kw)
        self._idx += 1
        self.convo.append(t)
        return t

    def _exec_tool_calls(self, am: AssistantMessage) -> Any:
        """Execute the agent's tool calls against the REAL env; return the tau2 reply message."""
        tmsgs = []
        for tc in am.tool_calls or []:
            name, args = tc.name, (tc.arguments or {})
            if name in STOP_TOOLS:
                tmsgs.append(ToolMessage(id=tc.id, role="tool",
                                         content="stop", requestor="assistant", error=False))
                self._record(speaker="tool", content="[stop]",
                             tool_name=name, tool_args=args, tool_error=False,
                             is_mutation=False, db_hash_after=self.env.get_db_hash())
                continue
            is_mut = name in self.mutation_tool_names
            try:
                res = self.env.make_tool_call(name, requestor="assistant", **args)
                content = str(res)
                err = False
            except Exception as exc:  # noqa: BLE001
                content = f"Error: {exc}"
                err = True
            self._record(speaker="tool", content=content[:800], tool_name=name,
                         tool_args=args, tool_error=err, is_mutation=is_mut,
                         db_hash_after=self.env.get_db_hash())
            tmsgs.append(ToolMessage(id=tc.id, role="tool", content=content[:1200],
                                     requestor="assistant", error=err))
        if len(tmsgs) == 1:
            return tmsgs[0]
        return MultiToolMessage(role="tool", tool_messages=tmsgs)

    def agent_respond(self, user_or_tool_msg) -> AssistantMessage:
        """One agent turn; if it emits tool calls, execute them and keep going until it
        speaks to the user or hits a stop/step cap. Returns the last assistant message."""
        msg = user_or_tool_msg
        for _ in range(self.max_agent_steps):
            am, self.agent_state = self.agent.generate_next_message(msg, self.agent_state)
            self.n_agent_steps += 1
            tcs = am.tool_calls or []
            if tcs:
                self._record(speaker="agent", content=am.content or "",
                             tool_name="+".join(t.name for t in tcs))
                if any(t.name in STOP_TOOLS for t in tcs):
                    self._exec_tool_calls(am)
                    return am
                msg = self._exec_tool_calls(am)
                continue
            # user-facing message: agent yields the turn
            self._record(speaker="agent", content=am.content or "")
            return am
        return am

    def user_say(self, text: str) -> UserMessage:
        self._record(speaker="user", content=text)
        return UserMessage(role="user", content=text)

    # ---- snapshot / branch ----
    def snapshot(self, junction_reason: str) -> Snapshot:
        return Snapshot(
            tools=copy.deepcopy(self.env.tools),
            agent_state=copy.deepcopy(self.agent_state),
            convo=copy.deepcopy(self.convo),
            n_agent_steps=self.n_agent_steps,
            db_hash=self.env.get_db_hash(),
            junction_reason=junction_reason,
        )

    def restore(self, snap: Snapshot) -> None:
        self.env.tools = copy.deepcopy(snap.tools)
        self.agent_state = copy.deepcopy(snap.agent_state)
        self.convo = copy.deepcopy(snap.convo)
        self.n_agent_steps = snap.n_agent_steps
        self._idx = (self.convo[-1].idx + 1) if self.convo else 0


# ---------- process metrics on a suffix ----------
def suffix_metrics(convo_full: list[Turn], prefix_len: int) -> dict:
    """Metrics over the SUFFIX only (turns added after the junction)."""
    suffix = convo_full[prefix_len:]
    tool_turns = [t for t in suffix if t.speaker == "tool" and t.tool_name not in STOP_TOOLS]
    reads = [t for t in tool_turns if not t.is_mutation and not t.tool_error]
    muts = [t for t in tool_turns if t.is_mutation and not t.tool_error]
    errs = [t for t in tool_turns if t.tool_error]
    user_turns = [t for t in suffix if t.speaker == "user"]
    agent_msgs = [t for t in suffix if t.speaker == "agent"]

    # duplicate reads: same (tool_name, args) called more than once in the suffix
    seen = {}
    dup = 0
    for t in reads:
        key = (t.tool_name, str(sorted((t.tool_args or {}).items())))
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            dup += 1

    # first mutation step index within the suffix tool sequence (or None)
    first_mut = next((i for i, t in enumerate(tool_turns) if t.is_mutation and not t.tool_error), None)
    # evidence (distinct successful reads) before first mutation
    ev_before_mut = None
    if first_mut is not None:
        pre = tool_turns[:first_mut]
        ev_before_mut = len({(t.tool_name, str(sorted((t.tool_args or {}).items())))
                             for t in pre if not t.is_mutation and not t.tool_error})

    return dict(
        n_tool_events=len(tool_turns),
        n_reads=len(reads),
        n_unique_reads=len({(t.tool_name, str(sorted((t.tool_args or {}).items()))) for t in reads}),
        n_duplicate_reads=dup,
        n_mutations=len(muts),
        n_tool_errors=len(errs),
        n_user_turns=len(user_turns),
        n_agent_messages=len(agent_msgs),
        first_mutation_step=first_mut,
        evidence_before_first_mutation=ev_before_mut,
        tool_sequence=" ".join(t.tool_name for t in tool_turns),
        final_db_hash=(tool_turns[-1].db_hash_after if tool_turns else None),
        suffix_len_turns=len(suffix),
    )


def convo_to_text(convo: list[Turn], start: int = 0) -> str:
    lines = []
    for t in convo[start:]:
        if t.speaker == "tool":
            lines.append(f"[tool {t.tool_name}] {'ERR ' if t.tool_error else ''}{t.content[:200]}")
        else:
            tag = "USER" if t.speaker == "user" else "AGENT"
            extra = f" (calls {t.tool_name})" if t.tool_name else ""
            lines.append(f"{tag}{extra}: {t.content[:300]}")
    return "\n".join(lines)
