"""Frozen task-user policies for the Stage-2.5b scripted user."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = (
    ROOT / "data" / "stage2_5b" / "task_user_policies.yaml"
)


@dataclass(frozen=True)
class TaskUserPolicy:
    source_task_id: str
    domain: str
    task_label: str
    initial_state: str
    user_facts: dict[str, str]
    decisions: dict[str, Any]
    confirmation_revision_once: bool = False


def load_task_policies(
    path: Path = DEFAULT_POLICY_PATH,
) -> tuple[dict[str, TaskUserPolicy], list[str], dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid task policy file: {path}")
    tasks = payload.get("tasks")
    if not isinstance(tasks, dict) or not tasks:
        raise ValueError("task_user_policies.yaml must contain non-empty tasks")
    state_machine = payload.get("state_machine")
    if not isinstance(state_machine, dict) or "request_open" not in state_machine:
        raise ValueError("task policy file is missing request_open state")

    policies: dict[str, TaskUserPolicy] = {}
    source_ids: set[str] = set()
    for task_label, item in tasks.items():
        if not isinstance(item, dict):
            raise ValueError(f"invalid task policy: {task_label}")
        source_task_id = str(item["source_task_id"])
        domain = str(item["domain"])
        key = f"{domain}_{source_task_id}"
        if key != task_label:
            raise ValueError(
                f"task key mismatch: {task_label!r}, expected {key!r}"
            )
        user_facts = {
            str(name): str(value)
            for name, value in (item.get("user_facts") or {}).items()
        }
        required_facts = {
            "opening",
            "identity",
            "preference",
            "payment",
            "fallback",
            "confirmation_detail",
        }
        missing = sorted(required_facts - set(user_facts))
        if missing:
            raise ValueError(
                f"task {task_label} missing user_facts: {missing}"
            )
        policies[task_label] = TaskUserPolicy(
            source_task_id=source_task_id,
            domain=domain,
            task_label=task_label,
            initial_state=str(item.get("initial_state", "request_open")),
            user_facts=user_facts,
            decisions=dict(item.get("decisions") or {}),
            confirmation_revision_once=bool(
                item.get("confirmation_revision_once", False)
            ),
        )
        source_ids.add(source_task_id)

    calibration_panel = [
        str(task_id) for task_id in payload.get("calibration_panel") or []
    ]
    unknown_panel = sorted(set(calibration_panel) - set(policies))
    if unknown_panel:
        raise ValueError(
            f"unknown calibration-panel tasks: {unknown_panel}"
        )
    return policies, calibration_panel, state_machine


TASK_POLICIES, CALIBRATION_PANEL, STATE_MACHINE = load_task_policies()


def resolve_policy(
    source_task_id: str,
    *,
    domain: str | None = None,
) -> TaskUserPolicy:
    source_task_id = str(source_task_id)
    if domain is not None:
        key = f"{domain}_{source_task_id}"
        if key in TASK_POLICIES:
            return TASK_POLICIES[key]
        raise KeyError(f"no frozen task-user policy for {key}")
    matches = [
        policy
        for policy in TASK_POLICIES.values()
        if policy.source_task_id == source_task_id
    ]
    if len(matches) != 1:
        raise KeyError(
            f"source_task_id={source_task_id!r} is missing or ambiguous; "
            "provide domain"
        )
    return matches[0]
