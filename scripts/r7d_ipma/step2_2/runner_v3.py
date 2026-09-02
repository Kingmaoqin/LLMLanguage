#!/usr/bin/env python3
"""R7-D Step 2.2 runner v3: NATURAL information-gated junctions + fail-closed parser.

Fixes over v2 (which passed junction legality G2a but failed suffix exposure G2b):
  * NATURAL junctions. The neutral opening deliberately WITHHOLDS the identity/decision
    fact, so the agent's own first move is to ASK for it. That request IS the junction.
    The branch replies then supply the identical fact/decision, forcing the real
    reads (T1) or the confirmation->mutation (T2) to happen in the SUFFIX, not the prefix.
      - T1 junction: agent yielded, requesting a required fact, with NO substantive tool
        work yet (reads_done == 0). >=2 real reads become possible only after the reply.
      - T2 junction: agent yielded at a natural confirmation node, evidence already
        gathered, confirmation + first mutation not yet done -> mutation lands in suffix.
  * Fail-closed parser: an empty/whitespace tool-call name is NOT silently counted as a
    tool event; it is sanitized to "__invalid__" (so litellm won't 400 on the next turn)
    and returned as an error ToolMessage. Fixes the Mistral empty-function-name crash.

Only N0/N1/P are ever run here. No adaptive treatment A. All local vLLM.
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
CONFIRM_CUES = ("confirm", "shall i", "should i", "would you like me", "do you want me",
                "can i proceed", "may i proceed", "to proceed", "go ahead",
                "please confirm", "would you like to proceed")
FACT_REQUEST_CUES = ("your name", "first name", "last name", "zip", "order number",
                     "order id", "order #", "reservation", "user id", "email",
                     "could you provide", "can you provide", "please provide",
                     "what is your", "may i have", "to look up", "to pull up",
                     "to locate", "to find your", "to access your", "identify your")


def get_env(domain: str):
    mod = __import__(f"tau2.domains.{domain}.environment", fromlist=["get_environment"])
    return mod.get_environment()


@dataclasses.dataclass
class Snapshot:
    tools: Any
    agent_state: Any
    messages: list
    db_hash: str
    reads_done: int
    mutations_done: int
    junction_reason: str
    junction_proof: dict


class Session:
    def __init__(self, domain: str, model_alias: str, mutation_tools: set,
                 temperature: float = 0.0, max_steps: int = 16):
        self.domain = domain
        self.mutation_tools = mutation_tools
        self.max_steps = max_steps
        self.env = get_env(domain)
        model, api_base = MODEL_ENDPOINTS[model_alias]
        self.agent = LLMAgent(
            tools=self.env.get_tools(), domain_policy=self.env.get_policy(),
            llm=model, llm_args={"api_base": api_base, "api_key": "EMPTY",
                                 "temperature": temperature, "num_retries": 2},
        )
        self.agent_state = self.agent.get_init_state()
        self.messages: list = []
        self.reads_done = 0
        self.mutations_done = 0
        self.parser_errors = 0

    def _agent_turn(self, in_msg) -> AssistantMessage:
        msg = in_msg
        for _ in range(self.max_steps):
            am, self.agent_state = self.agent.generate_next_message(msg, self.agent_state)
            self.messages.append(am)
            tcs = am.tool_calls or []
            if not tcs:
                return am
            tmsgs = []
            for tc in tcs:
                name = (tc.name or "").strip()
                if not name:
                    # fail-closed: sanitize so litellm accepts the history, count as error
                    tc.name = "__invalid__"
                    self.parser_errors += 1
                    tm = ToolMessage(id=tc.id, role="tool",
                                     content="Error: empty tool name (rejected, fail-closed)",
                                     requestor="assistant", error=True)
                elif tc.name in STOP_TOOLS:
                    tm = ToolMessage(id=tc.id, role="tool", content="stop",
                                     requestor="assistant", error=False)
                else:
                    tm = self.env.get_response(tc)
                    if not tm.error:
                        if tc.name in self.mutation_tools:
                            self.mutations_done += 1
                        else:
                            self.reads_done += 1
                self.messages.append(tm)
                tmsgs.append(tm)
            if any((tc.name or "") in STOP_TOOLS for tc in tcs):
                return am
            msg = tmsgs[0] if len(tmsgs) == 1 else MultiToolMessage(role="tool", tool_messages=tmsgs)
        return am

    def user(self, text: str) -> UserMessage:
        um = UserMessage(role="user", content=text)
        self.messages.append(um)
        return um

    def run_prefix_to_junction(self, opening: str, stratum: str,
                               max_user_turns: int = 4) -> Optional[Snapshot]:
        msg = self.user(opening)
        for _ in range(max_user_turns):
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
            if proof["dead"]:
                return None
            # minimal neutral nudge to keep the agent going toward a junction
            msg = self.user("Sure — what do you need from me to proceed?")
        return None

    def _junction_proof(self, stratum: str, last_am: AssistantMessage) -> dict:
        text = (last_am.content or "").lower()
        yielded = not (last_am.tool_calls or [])
        confirm_asked = any(c in text for c in CONFIRM_CUES)
        fact_requested = any(c in text for c in FACT_REQUEST_CUES)
        endpoint_done = self.mutations_done > 0
        proof = dict(
            stratum=stratum, reads_done=self.reads_done, mutations_done=self.mutations_done,
            agent_yielded_to_user=yielded, fact_requested=fact_requested,
            confirmation_asked=confirm_asked,
            mutation_not_yet_done=self.mutations_done == 0,
            endpoint_not_complete=not endpoint_done,
        )
        if stratum == "T1":
            # NATURAL: agent asks for a required fact BEFORE substantive tool work.
            valid = yielded and fact_requested and self.reads_done == 0 and not endpoint_done
            reason = "T1: agent requesting a required fact before any substantive read"
            proof["exposure_expectation"] = ">=2 reads become possible only after the reply"
        else:  # T2
            # NATURAL: confirmation node with evidence gathered, no mutation yet.
            valid = yielded and confirm_asked and self.reads_done >= 1 and not endpoint_done
            reason = "T2: natural confirmation node, evidence gathered, mutation not yet done"
            proof["exposure_expectation"] = "confirmation+mutation land in the suffix"
        # dead: agent completed/failed the endpoint, or yielded with nothing actionable
        dead = endpoint_done or (yielded and not fact_requested and not confirm_asked
                                 and self.reads_done == 0)
        proof["junction_valid"] = bool(valid)
        proof["dead"] = bool(dead and not valid)
        proof["reason"] = reason
        return proof

    def restore(self, snap: Snapshot) -> None:
        self.env.tools = copy.deepcopy(snap.tools)
        self.agent_state = copy.deepcopy(snap.agent_state)
        self.messages = copy.deepcopy(snap.messages)
        self.reads_done = snap.reads_done
        self.mutations_done = snap.mutations_done

    def run_suffix(self, user_turns: list[str], prefix_len: int) -> dict:
        for ut in user_turns:
            um = self.user(ut)
            self._agent_turn(um)
            if any(isinstance(m, ToolMessage) and m.content == "stop" for m in self.messages[-4:]):
                break
        return self._suffix_metrics(prefix_len)

    def _suffix_metrics(self, prefix_len: int) -> dict:
        suffix = self.messages[prefix_len:]
        seq, first_mut = [], None
        for m in suffix:
            if isinstance(m, AssistantMessage) and m.tool_calls:
                for tc in m.tool_calls:
                    nm = tc.name or ""
                    if nm in ("__invalid__",) or not nm:
                        continue  # fail-closed: not a real tool event
                    seq.append(nm)
                    if nm in self.mutation_tools and first_mut is None:
                        first_mut = len(seq) - 1
        reads = [s for s in seq if s not in self.mutation_tools]
        return dict(
            n_tool_events=len(seq),
            n_reads=len(reads),
            n_unique_reads=len(set(reads)),
            n_mutations=sum(1 for s in seq if s in self.mutation_tools),
            first_mutation_step=first_mut,
            evidence_before_first_mutation=(len(set(seq[:first_mut])) if first_mut is not None else None),
            tool_sequence=" ".join(seq),
            suffix_len=len(suffix),
        )
