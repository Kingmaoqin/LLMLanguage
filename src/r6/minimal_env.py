"""Minimal deterministic R6 tool environment.

This module executes R6 task specs without a model. It is for smoke/preflight
infrastructure validation only: it proves user rendering, tools, state diffs,
trace writing, and metric extraction work before any live model is allowed.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.r6.controlled_user_adapter import R6ControlledUserAdapter, stable_hash
from src.stage2_5b.metrics.trace_metrics import TRACE_SCHEMA_VERSION


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def state_hash(state: dict[str, Any]) -> str:
    return stable_hash(json.dumps(state, sort_keys=True, ensure_ascii=False))


def field_diff(before: Any, after: Any, prefix: str = "") -> list[dict[str, Any]]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        rows: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            child = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(field_diff(before.get(key), after.get(key), child))
        return rows
    if isinstance(before, list) and isinstance(after, list):
        rows = []
        for idx in range(max(len(before), len(after))):
            b = before[idx] if idx < len(before) else None
            a = after[idx] if idx < len(after) else None
            rows.extend(field_diff(b, a, f"{prefix}[{idx}]"))
        return rows
    return [{"path": prefix or "$", "before": before, "after": after}]


@dataclass(frozen=True)
class R6RunCell:
    run_id: str
    model_alias: str
    task_id: str
    domain: str
    layer: str
    condition_id: str
    seed: int
    temperature: float
    executor: str


class R6MinimalDeterministicEnvironment:
    """Run one R6 cell through deterministic tools and return a canonical trace."""

    def __init__(
        self,
        *,
        tasks_path: Path,
        templates_path: Path,
        user_policies_path: Path,
        annotations_path: Path,
        seed_states_path: Path,
    ) -> None:
        self.user = R6ControlledUserAdapter(
            tasks_path=tasks_path,
            templates_path=templates_path,
            user_policies_path=user_policies_path,
        )
        self.annotations = load_yaml(annotations_path)["tasks"]
        self.seed_states = load_yaml(seed_states_path)["seed_states"]

    def run_cell(self, cell: R6RunCell) -> dict[str, Any]:
        task = self.user.task(cell.task_id)
        ann = self.annotations[cell.task_id]
        clean_state = self.initial_state(task, ann, cell.seed)
        state = copy.deepcopy(clean_state)
        conversation: list[dict[str, Any]] = []
        tool_events: list[dict[str, Any]] = []
        state_deltas: list[dict[str, Any]] = []
        controlled_user_events: list[dict[str, Any]] = []
        confirmation_events: list[dict[str, Any]] = []
        refusal_events: list[dict[str, Any]] = []
        boundary_events: list[dict[str, Any]] = []
        privacy_events: list[dict[str, Any]] = []
        unsafe_events: list[dict[str, Any]] = []
        field_level_state_diff: list[dict[str, Any]] = []

        turns = self.user.render_turns(cell.task_id, cell.condition_id)
        for turn in turns:
            conversation.append({"role": "user", "content": turn.styled_text, "turn_idx": turn.turn_idx})
            controlled_user_events.append(
                {
                    "task_id": cell.task_id,
                    "domain": cell.domain,
                    "condition": cell.condition_id,
                    "turn_idx": turn.turn_idx,
                    "clean_text": turn.clean_text,
                    "styled_text": turn.styled_text,
                    "clean_text_hash": turn.clean_text_hash,
                    "styled_text_hash": turn.styled_text_hash,
                    "wrapper_event": {
                        "condition": cell.condition_id,
                        "template_id": turn.template_id,
                        "wrapper_text": turn.wrapper_text,
                        **turn.metadata,
                    },
                }
            )

        step = 0
        turn_idx = 3
        for tool in task.get("read_tools") or []:
            tool_events.append(self.tool_event(tool, step, turn_idx, state, mutated=False))
            step += 1
            turn_idx += 1

        if task.get("requires_refusal"):
            conversation.append(
                {
                    "role": "assistant",
                    "content": "I cannot perform the disallowed part, but I will continue any allowed safe part.",
                    "turn_idx": turn_idx,
                }
            )
            refusal_events.append({"refused": True, "turn_idx": turn_idx, "reason": ann.get("refusal_policy")})
            boundary_events.append({"boundary_set": True, "turn_idx": turn_idx, "policy": ann.get("refusal_policy")})
            if ann.get("privacy_rules"):
                privacy_events.append({"violation": False, "turn_idx": turn_idx})
            if ann.get("unsafe_rules"):
                unsafe_events.append({"unsafe_compliance": False, "turn_idx": turn_idx})
            turn_idx += 1

        for tool in task.get("mutation_tools") or []:
            if task.get("requires_confirmation"):
                conversation.append({"role": "assistant", "content": f"Please confirm before I call {tool}.", "turn_idx": turn_idx})
                confirmation_events.append({"requested": True, "tool_name": tool, "turn_idx": turn_idx})
                turn_idx += 1
                confirmed = self.user.confirmation_value_for(cell.task_id, tool)
                controlled_user_events.append(
                    {
                        "task_id": cell.task_id,
                        "domain": cell.domain,
                        "condition": cell.condition_id,
                        "turn_idx": turn_idx,
                        "speech_act": "confirmation",
                        "confirmation_value": confirmed,
                        "confirmation": confirmed,
                        "clean_text": "I confirm the allowed action." if confirmed else "I do not confirm that action.",
                        "styled_text": "I confirm the allowed action." if confirmed else "I do not confirm that action.",
                        "clean_text_hash": stable_hash("I confirm the allowed action." if confirmed else "I do not confirm that action."),
                    }
                )
                confirmation_events.append({"obtained": confirmed, "tool_name": tool, "turn_idx": turn_idx})
                turn_idx += 1
                if not confirmed:
                    continue
            before = copy.deepcopy(state)
            self.apply_mutation(state, task, ann, tool)
            event = self.tool_event(tool, step, turn_idx, before, mutated=True, after_state=state)
            tool_events.append(event)
            delta_rows = field_diff(before, state)
            for row in delta_rows:
                row.update({"tool_name": tool, "step_index": step, "turn_idx": turn_idx})
            field_level_state_diff.extend(delta_rows)
            state_deltas.append(
                {
                    "tool_name": tool,
                    "step_index": step,
                    "turn_idx": turn_idx,
                    "state_before": before,
                    "state_after": copy.deepcopy(state),
                    "state_before_hash": state_hash(before),
                    "state_after_hash": state_hash(state),
                    "mutated": True,
                }
            )
            step += 1
            turn_idx += 1

        conversation.append({"role": "assistant", "content": "Completed the deterministic R6 smoke path.", "turn_idx": turn_idx})
        return {
            "schema_version": TRACE_SCHEMA_VERSION,
            "run_id": cell.run_id,
            "run_meta": {
                "run_id": cell.run_id,
                "model_alias": cell.model_alias,
                "task_id": cell.task_id,
                "source_task_id": task.get("source_task_id"),
                "condition_id": cell.condition_id,
                "seed": cell.seed,
                "temperature": cell.temperature,
                "domain": cell.domain,
                "layer": cell.layer,
                "executor": cell.executor,
                "executor_mode": "deterministic_env_smoke",
                "model_call_performed": False,
                "live_tau2_executor_available": False,
                "smoke_trace_only": True,
            },
            "conversation": conversation,
            "tool_events": tool_events,
            "state_deltas": state_deltas,
            "controlled_user_events": controlled_user_events,
            "policy_failures": [],
            "branch_decisions": [{"branch_id": bp["branch_id"], "decision": "deterministic_valid"} for bp in task["branch_points"]],
            "final_environment_state": {
                "final_state_correct": None,
                "final_state_evaluable": False,
                "reason": "deterministic_env_smoke_no_model",
                "state": state,
                "state_hash": state_hash(state),
            },
            "initial_environment_state": clean_state,
            "field_level_state_diff": field_level_state_diff,
            "confirmation_events": confirmation_events,
            "refusal_events": refusal_events,
            "boundary_events": boundary_events,
            "privacy_events": privacy_events,
            "unsafe_events": unsafe_events,
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "tokens_total": None, "token_source": "missing"},
        }

    def initial_state(self, task: dict[str, Any], ann: dict[str, Any], seed: int) -> dict[str, Any]:
        seed_state = self.seed_states[task["env_seed_state_id"]]
        state: dict[str, Any] = {
            "state_family": seed_state["state_family"],
            "task_id": task["task_id"],
            "domain": task["domain"],
            "layer": task["layer"],
            "seed": seed,
            "protected": bool(task.get("privacy_sensitive")),
            "unsafe": bool(task.get("unsafe_request")),
            "records": {
                task["task_id"]: {
                    "status": "initial",
                    "domain": task["domain"],
                    "layer": task["layer"],
                    "seed": seed,
                    "protected": bool(task.get("privacy_sensitive")),
                    "unsafe": bool(task.get("unsafe_request")),
                }
            },
        }
        for path in ann.get("expected_field_diffs") or []:
            set_path(state, path, f"initial::{path}")
        return state

    def tool_event(
        self,
        tool_name: str,
        step_index: int,
        turn_idx: int,
        state: dict[str, Any],
        *,
        mutated: bool,
        after_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "tool_name": tool_name,
            "arguments": {"deterministic": True},
            "tool_result": {"ok": True, "summary": f"{tool_name} executed"},
            "tool_error": False,
            "valid_json": True,
            "undefined_tool": False,
            "step_index": step_index,
            "turn_idx": turn_idx,
            "mutation_type": "write" if mutated else "read",
            "irreversible_action": mutated,
            "policy_relevant": True,
            "branch_relevant": True,
            "state_before_hash": state_hash(state),
            "state_after_hash": state_hash(after_state or state),
            "mutated": mutated,
        }

    def apply_mutation(self, state: dict[str, Any], task: dict[str, Any], ann: dict[str, Any], tool_name: str) -> None:
        for path in expected_paths_for_tool(task, ann, tool_name):
            set_path(state, path, f"updated::{tool_name}::{path}")


def set_path(state: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    if not parts:
        return
    cur = state
    for part in parts[:-1]:
        child = cur.get(part)
        if not isinstance(child, dict):
            child = {}
            cur[part] = child
        cur = child
    cur[parts[-1]] = value


def expected_paths_for_tool(task: dict[str, Any], ann: dict[str, Any], tool_name: str) -> list[str]:
    expected = list(ann.get("expected_field_diffs") or [])
    if not expected:
        return []
    mutation_tools = list(task.get("mutation_tools") or [])
    if len(mutation_tools) <= 1:
        return expected
    if len(expected) == len(mutation_tools) and tool_name in mutation_tools:
        return [expected[mutation_tools.index(tool_name)]]
    return expected


def trace_path_for(root: Path, run_id: str) -> Path:
    safe = run_id.replace("/", "_")
    return root / "traces" / f"{safe}.trace.json"


def write_trace(root: Path, trace: dict[str, Any], *, overwrite: bool = False) -> Path:
    path = trace_path_for(root, str(trace["run_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing R6 trace: {path}")
    path.write_text(json.dumps(trace, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path
