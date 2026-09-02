"""Deterministic R6 user/style adapter.

This adapter is intentionally independent from the Stage-2.5b tau2 user class:
R6 uses eight 3-turn-matched conditions, while the R5 user wrapper was built
around single/repeated templates. The adapter renders the same clean task turns
under every R6 condition and records hashes/metadata for invariance checks.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def stable_hash(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class R6StyledTurn:
    turn_idx: int
    clean_text: str
    styled_text: str
    wrapper_text: str
    condition_id: str
    template_id: str
    clean_text_hash: str
    styled_text_hash: str
    metadata: dict[str, Any]


class R6ControlledUserAdapter:
    """Render deterministic R6 user turns for any task/condition pair."""

    def __init__(
        self,
        *,
        tasks_path: Path,
        templates_path: Path,
        user_policies_path: Path,
    ) -> None:
        self.tasks_payload = _load_yaml(tasks_path)
        self.templates_payload = _load_yaml(templates_path)
        policies_payload = _load_yaml(user_policies_path)
        self.tasks = {task["task_id"]: task for task in self.tasks_payload["tasks"]}
        self.conditions = {cond["condition_id"]: cond for cond in self.templates_payload["conditions"]}
        self.policies = {policy["task_id"]: policy for policy in policies_payload["tasks"]}
        self.defaults = policies_payload.get("defaults") or {}
        if self.defaults.get("runtime_llm_user_allowed") is not False:
            raise ValueError("R6 controlled user requires runtime_llm_user_allowed=false")

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return self.tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"unknown R6 task_id: {task_id}") from exc

    def policy(self, task_id: str) -> dict[str, Any]:
        try:
            return self.policies[task_id]
        except KeyError as exc:
            raise KeyError(f"missing R6 user policy for task_id: {task_id}") from exc

    def condition(self, condition_id: str) -> dict[str, Any]:
        try:
            return self.conditions[condition_id]
        except KeyError as exc:
            raise KeyError(f"unknown R6 condition_id: {condition_id}") from exc

    def render_turns(self, task_id: str, condition_id: str) -> list[R6StyledTurn]:
        task = self.task(task_id)
        condition = self.condition(condition_id)
        clean_turns = list(task["clean_user_turns"])
        wrappers = list(condition["wrappers"])
        if len(clean_turns) != 3 or len(wrappers) != 3:
            raise ValueError(f"R6 requires 3-turn matched task/template: {task_id} x {condition_id}")
        turns: list[R6StyledTurn] = []
        for idx, (clean, wrapper) in enumerate(zip(clean_turns, wrappers)):
            styled = f"{wrapper} {clean}".strip()
            turns.append(
                R6StyledTurn(
                    turn_idx=idx,
                    clean_text=clean,
                    styled_text=styled,
                    wrapper_text=wrapper,
                    condition_id=condition_id,
                    template_id=f"{condition_id}_turn{idx + 1}",
                    clean_text_hash=stable_hash(clean),
                    styled_text_hash=stable_hash(styled),
                    metadata={
                        "family": condition["family"],
                        "valence": condition["valence"],
                        "pressure": condition["pressure"],
                        "pressure_type": condition["pressure_type"],
                        "turn_structure": condition["turn_structure"],
                        "authorization_contamination": condition["authorization_contamination"],
                        "urgency_contamination": condition["urgency_contamination"],
                        "threat_contamination": condition["threat_contamination"],
                        "continuation_instruction": condition["continuation_instruction"],
                        "policy_reminder": condition["policy_reminder"],
                        "protected_class_slur": condition["protected_class_slur"],
                    },
                )
            )
        return turns

    def confirmation_value_for(self, task_id: str, tool_name: str) -> bool:
        policy = self.policy(task_id)
        scope = policy.get("confirmation_scope") or ""
        if isinstance(scope, str):
            allowed = {item.strip() for item in scope.split(",") if item.strip()}
        else:
            allowed = set(scope)
        return bool(policy.get("provides_confirmation_if_requested")) and tool_name in allowed

    def never_authorize_tools(self, task_id: str) -> set[str]:
        return set(self.policy(task_id).get("never_authorize_tools") or [])

