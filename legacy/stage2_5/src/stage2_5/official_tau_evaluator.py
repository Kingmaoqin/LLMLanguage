"""Local official tau2 reward-basis helpers."""

from __future__ import annotations

from typing import Any


def official_basis(task: Any) -> list[str]:
    crit = getattr(task, "evaluation_criteria", None)
    return [str(x).split(".")[-1] for x in (getattr(crit, "reward_basis", None) or [])]


def official_local_metrics(task: Any, reward_info: Any) -> dict:
    """Compute official and local-proxy success with explicit missingness.

    `official_reward_basis_success` is only assigned when all components in the
    task's own reward basis are locally available. `local_proxy_success` covers
    the locally computable subset only and must not be described as full
    official task success.
    """
    basis = official_basis(task)
    db_ok = bool(reward_info.db_check.db_match) if getattr(reward_info, "db_check", None) else None
    comm = getattr(reward_info, "communicate_checks", None) or []
    comm_ok = all(bool(c.met) for c in comm) if comm else None
    local_parts: list[bool] = []
    local_components: list[str] = []
    missing_components: list[str] = []
    if "DB" in basis or "ENV_ASSERTION" in basis:
        if db_ok is None:
            missing_components.append("DB")
        else:
            local_parts.append(db_ok)
            local_components.append("DB")
    if "COMMUNICATE" in basis:
        if comm_ok is None:
            missing_components.append("COMMUNICATE")
        else:
            local_parts.append(comm_ok)
            local_components.append("COMMUNICATE")
    if "NL_ASSERTION" in basis:
        missing_components.append("NL_ASSERTION")
    unsupported = sorted(set(basis) - {"DB", "ENV_ASSERTION", "COMMUNICATE", "NL_ASSERTION"})
    missing_components.extend(unsupported)

    local_proxy_success = all(local_parts) if local_parts else None
    fully_evaluable = not missing_components and bool(local_parts)
    official_reward_basis_success = all(local_parts) if fully_evaluable else None
    return {
        "official_reward_basis": "|".join(basis),
        "official_missing_offline_components": "|".join(missing_components),
        "official_fully_evaluable_offline": fully_evaluable,
        "official_reward_basis_success": official_reward_basis_success,
        "local_proxy_success": local_proxy_success,
        "local_proxy_components": "|".join(local_components),
        "official_needs_nl_assertion": "NL_ASSERTION" in basis,
        "official_local_success": local_proxy_success,
        "official_task_success": official_reward_basis_success,
        "official_db_success": db_ok,
        "official_communicate_success": comm_ok,
    }
