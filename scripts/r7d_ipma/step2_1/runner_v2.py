#!/usr/bin/env python3
"""R7-D Step 2.1 runner v2: real-message snapshot/branch runner over tau2, scorable.

Two fixes over the Step-2 runner, both required for identification closure:
  1. It preserves the EXACT tau2 Message objects — real AssistantMessage(.tool_calls)
     and real ToolMessage from env.get_response (id == tool_call.id) — so the full
     trajectory is replayable by the official evaluate_simulation (Gate G1).
  2. It stops the neutral prefix at a FAMILY-SPECIFIC junction with an explicit,
     machine-checkable proof (Gate G2), instead of "the agent's first message".

Branches supported here: N0 (exact neutral repeat), N1 (matched neutral), P (explicit
process positive control). Adaptive treatment A is NOT run in Step 2.1.

All model traffic is local vLLM; the tau2 DB is in-process synthetic.
"""
from __future__ import annotations

import copy
import dataclasses
from typing import Any, Optional

from tau2.agent.llm_agent import LLMAgent
from tau2.data_model.message import (
    AssistantMessage, MultiToolMessage, ToolMessage, UserMessage,
)

MODEL_ENDPOINTS = {
    "gemma4_31b": ("openai/g4-v2-1", "http://127.0.0.1:8005/v1"),
    "gpt_oss_120b": ("openai/gpt-oss", "http://127.0.0.1:8192/v1"),
    "mistral_small_3p2": ("openai/mistral-small-3p2", "http://127.0.0.1:8007/v1"),
}
STOP_TOOLS = {"done", "transfer_to_human_agents", "transfer_to_human"}
CONFIRM_CUES = ("confirm", "shall i", "should i", "would you like", "do you want",
                "can i proceed", "may i", "is that correct", "to proceed", "go ahead",
                "please confirm", "would you like me to")


def get_env(domain: str):
    mod = __import__(f"tau2.domains.{domain}.environment", fromlist=["get_environment"])
    return mod.get_environment()


@dataclasses.dataclass
class Snapshot:
    tools: Any
    agent_state: Any
    messages: list          # real tau2 Message objects (user/assistant/tool), in order
    db_hash: str
    reads_done: int
    mutations_done: int
    junction_reason: str
    junction_proof: dict


class Session:
    def __init__(self, domain: str, model_alias: str, mutation_tools: set,
                 gold_reads: int, temperature: float = 0.0, max_steps: int = 16):
        self.domain = domain
        self.mutation_tools = mutation_tools
        self.gold_reads = gold_reads
        self.max_steps = max_steps
        self.env = get_env(domain)
        model, api_base = MODEL_ENDPOINTS[model_alias]
        self.agent = LLMAgent(
            tools=self.env.get_tools(), domain_policy=self.env.get_policy(),
            llm=model, llm_args={"api_base": api_base, "api_key": "EMPTY",
                                 "temperature": temperature, "num_retries": 2},
        )
        self.agent_state = self.agent.get_init_state()
        self.messages: list = []           # scorable trajectory (no system message)
        self.reads_done = 0
        self.mutations_done = 0

    # ---- one agent turn: emit tool calls (executed via get_response) or a user msg ----
    def _agent_turn(self, in_msg) -> AssistantMessage:
        msg = in_msg
        for _ in range(self.max_steps):
            am, self.agent_state = self.agent.generate_next_message(msg, self.agent_state)
            self.messages.append(am)
            tcs = am.tool_calls or []
            if not tcs:
                return am  # yielded to the user
            tmsgs = []
            for tc in tcs:
                if tc.name in STOP_TOOLS:
                    tm = ToolMessage(id=tc.id, role="tool", content="stop",
                                     requestor="assistant", error=False)
                else:
                    tm = self.env.get_response(tc)  # real ToolMessage, id==tc.id
                    if not tm.error:
                        if tc.name in self.mutation_tools:
                            self.mutations_done += 1
                        else:
                            self.reads_done += 1
                self.messages.append(tm)
                tmsgs.append(tm)
            if any(tc.name in STOP_TOOLS for tc in tcs):
                return am
            msg = tmsgs[0] if len(tmsgs) == 1 else MultiToolMessage(role="tool", tool_messages=tmsgs)
        return am

    def user(self, text: str) -> UserMessage:
        um = UserMessage(role="user", content=text)
        self.messages.append(um)
        return um

    # ---- family-specific junction ----
    def run_prefix_to_junction(self, opening: str, stratum: str) -> Optional[Snapshot]:
        """Run neutral opening; step the agent until a family-valid junction, then
        snapshot. Returns None (with self.messages populated) if no valid junction
        is reachable before the endpoint (-> this cell is junction-ineligible)."""
        msg = self.user(opening)
        for _turn in range(6):
            am = self._agent_turn(msg)
            proof = self._junction_proof(stratum, am)
            if proof["junction_valid"]:
                return Snapshot(
                    tools=copy.deepcopy(self.env.tools),
                    agent_state=copy.deepcopy(self.agent_state),
                    messages=copy.deepcopy(self.messages),
                    db_hash=self.env.get_db_hash(),
                    reads_done=self.reads_done, mutations_done=self.mutations_done,
                    junction_reason=proof["reason"], junction_proof=proof,
                )
            if proof["endpoint_reached_or_dead"]:
                return None
            # otherwise: give the agent a minimal neutral nudge and continue
            msg = self.user("Please continue with the required process.")
        return None

    def _junction_proof(self, stratum: str, last_am: AssistantMessage) -> dict:
        text = (last_am.content or "").lower()
        yielded = not (last_am.tool_calls or [])
        confirm_asked = any(c in text for c in CONFIRM_CUES)
        remaining_gold_reads = max(0, self.gold_reads - self.reads_done)
        endpoint_done = self.mutations_done > 0
        proof = dict(
            stratum=stratum,
            reads_done=self.reads_done,
            mutations_done=self.mutations_done,
            remaining_legal_actions=remaining_gold_reads + (0 if stratum == "T1" else 1),
            remaining_evidence_sources=remaining_gold_reads,
            confirmation_not_yet_done=not confirm_asked if stratum == "T2" else True,
            mutation_not_yet_done=self.mutations_done == 0,
            endpoint_not_complete=not endpoint_done,
            agent_yielded_to_user=yielded,
            confirmation_asked=confirm_asked,
        )
        if stratum == "T1":
            # ≥2 legal reads still available, endpoint not done, agent will get another msg
            valid = (yielded and remaining_gold_reads >= 2 and not endpoint_done
                     and self.reads_done >= 1)
            reason = "T1: agent yielded with >=2 gold reads remaining, no mutation yet"
        else:  # T2
            # confirmation not done, mutation not done, agent yielded (about to confirm/act)
            valid = (yielded and not endpoint_done and self.reads_done >= 1)
            reason = "T2: agent yielded before confirmation/mutation with evidence gathered"
        # dead end: agent yielded but produced nothing actionable and no reads -> unusable
        dead = (yielded and self.reads_done == 0 and not confirm_asked) or endpoint_done
        proof["junction_valid"] = bool(valid)
        proof["endpoint_reached_or_dead"] = bool(dead and not valid)
        proof["reason"] = reason
        return proof

    def restore(self, snap: Snapshot) -> None:
        self.env.tools = copy.deepcopy(snap.tools)
        self.agent_state = copy.deepcopy(snap.agent_state)
        self.messages = copy.deepcopy(snap.messages)
        self.reads_done = snap.reads_done
        self.mutations_done = snap.mutations_done

    def run_suffix(self, user_turns: list[str], prefix_len: int) -> dict:
        """Run a branch: alternate user turn -> agent turn, up to len(user_turns)."""
        last = next((m.content for m in reversed(self.messages)
                     if isinstance(m, AssistantMessage) and not m.tool_calls), "")
        for ut in user_turns:
            um = self.user(ut)
            am = self._agent_turn(um)
            last = am.content or ""
            if any(isinstance(m, ToolMessage) and m.content == "stop" for m in self.messages[-4:]):
                break
        return self._suffix_metrics(prefix_len)

    def _suffix_metrics(self, prefix_len: int) -> dict:
        suffix = self.messages[prefix_len:]
        tool_msgs = [m for m in suffix if isinstance(m, ToolMessage) and m.content != "stop"]
        # map each ToolMessage back to whether it was a mutation via the preceding call
        seq, muts, reads, errs = [], 0, 0, 0
        first_mut = None
        for i, m in enumerate(suffix):
            if isinstance(m, AssistantMessage) and m.tool_calls:
                for tc in m.tool_calls:
                    seq.append(tc.name)
                    is_mut = tc.name in self.mutation_tools
                    if is_mut and first_mut is None:
                        first_mut = len(seq) - 1
        return dict(
            n_tool_events=len(seq),
            n_reads=sum(1 for s in seq if s not in self.mutation_tools),
            n_mutations=sum(1 for s in seq if s in self.mutation_tools),
            first_mutation_step=first_mut,
            tool_sequence=" ".join(seq),
            suffix_len=len(suffix),
        )
