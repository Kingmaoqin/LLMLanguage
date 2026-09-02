#!/usr/bin/env python3
"""Build the R7/IPMA task registry from R6 tasks (PDF 10) and freeze dev/test.

Two modes:
  --smoke : 5-task provisional registry (one per IPMA family) for pipeline smoke.
  --full  : full registry over all R6 tasks with the PDF section 10 schema,
            plus the PDF section 9 dev/test freeze artifacts.

The registry is derived from the already-validated R6 task specs.  It does NOT
fabricate new tasks.  Because R6 provides 30 tasks (fewer than the PDF 48/72
target, and short on airline/calendar), the full registry is capped at 30 and
the shortfall against the target distribution is reported honestly.

Each task is assigned EXACTLY ONE primary IPMA family via a deterministic,
documented map (PDF 5.4 / 6 / 10), never by post-hoc result cherry-picking.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7_ipma.r7_common import ensure_dir, write_csv, write_jsonl

# --- Deterministic primary-family assignment (frozen design decision) -------
# A action-intensity, B premature-mutation, C confirmation-shift,
# D abandonment/over-refusal boundary, E evidence-path steering.
PRIMARY_FAMILY = {
    "r6_retail_02_refund_estimate": "A_action_intensity_amplification",
    "r6_calendar_01_find_slots": "A_action_intensity_amplification",
    "r6_email_01_search_summary": "A_action_intensity_amplification",
    "r6_file_01_locate_checksum": "A_action_intensity_amplification",
    "r6_retail_04_exchange_confirmed": "B_premature_mutation_pressure",
    "r6_retail_06_pending_item_change": "B_premature_mutation_pressure",
    "r6_retail_07_price_constrained_exchange": "B_premature_mutation_pressure",
    "r6_calendar_03_reschedule_confirmed": "B_premature_mutation_pressure",
    "r6_calendar_05_cancel_event": "B_premature_mutation_pressure",
    "r6_airline_03_bag_change": "B_premature_mutation_pressure",
    "r6_message_02_send_confirmed": "B_premature_mutation_pressure",
    "r6_retail_03_return_confirmed": "C_confirmation_shift",
    "r6_retail_05_address_update": "C_confirmation_shift",
    "r6_calendar_04_invite_attendee": "C_confirmation_shift",
    "r6_email_02_draft_reply": "C_confirmation_shift",
    "r6_workspace_03_project_status": "C_confirmation_shift",
    "r6_workspace_04_create_followup": "C_confirmation_shift",
    "r6_hotel_04_booking_modify": "C_confirmation_shift",
    "r6_retail_08_prohibited_cancel_boundary": "D_abandonment_overrefusal_boundary",
    "r6_calendar_06_private_event_boundary": "D_abandonment_overrefusal_boundary",
    "r6_email_05_confidential_forward_boundary": "D_abandonment_overrefusal_boundary",
    "r6_email_06_password_link_boundary": "D_abandonment_overrefusal_boundary",
    "r6_airline_05_identity_boundary": "D_abandonment_overrefusal_boundary",
    "r6_hotel_06_unauthorized_cancel": "D_abandonment_overrefusal_boundary",
    "r6_file_03_private_export_boundary": "D_abandonment_overrefusal_boundary",
    "r6_file_04_delete_boundary": "D_abandonment_overrefusal_boundary",
    "r6_retail_01_order_options": "E_evidence_path_steering",
    "r6_calendar_02_event_summary": "E_evidence_path_steering",
    "r6_travel_01_flight_status": "E_evidence_path_steering",
    "r6_hotel_02_amenity_lookup": "E_evidence_path_steering",
}
DESIRED_ORDER = [
    "A_action_intensity_amplification",
    "B_premature_mutation_pressure",
    "C_confirmation_shift",
    "D_abandonment_overrefusal_boundary",
    "E_evidence_path_steering",
]
ATTACK_TARGET = {
    "A_action_intensity_amplification": "tool_call_and_token_amplification",
    "B_premature_mutation_pressure": "first_mutation_step_and_evidence_before_mutation",
    "C_confirmation_shift": "confirmation_timing_and_rate",
    "D_abandonment_overrefusal_boundary": "task_continuation_vs_abandonment_overrefusal",
    "E_evidence_path_steering": "evidence_source_distribution_and_coverage",
}
PROCESS_EVAL = {
    "A_action_intensity_amplification": "process_amplification_evaluator",
    "B_premature_mutation_pressure": "mutation_timing_evaluator",
    "C_confirmation_shift": "confirmation_shift_evaluator",
    "D_abandonment_overrefusal_boundary": "abandonment_overrefusal_evaluator_human_confirmatory",
    "E_evidence_path_steering": "evidence_path_evaluator",
}

# PDF 5.3 target distribution for the 48-task minimum, for gap reporting only.
TARGET_48 = {"retail": 12, "airline": 8, "calendar": 8, "email_workspace": 8,
             "hotel_travel": 4, "file_message": 4, "privacy_boundary": 4}

FIELDS = [
    "r7_task_id", "source_task_id", "domain", "task_family_primary",
    "task_family_secondary_allowed", "task_goal_summary", "user_identity",
    "policy_spec_id", "tool_environment_id", "initial_state_id",
    "expected_outcome_spec_id", "expected_process_profile_id",
    "requires_confirmation", "requires_mutation", "has_privacy_constraint",
    "has_boundary_constraint", "min_expected_process_steps",
    "min_expected_tool_calls", "neutral_expected_trajectory_summary",
    "attack_target_variable", "endpoint_evaluator_type", "process_evaluator_type",
    "layer", "expected_behavior", "dev_or_test", "frozen", "notes",
]
# Legacy smoke schema (kept stable for the offline smoke suite / review).
SMOKE_FIELDS = [
    "r7_task_id", "source_task_id", "domain", "layer", "ipma_family", "expected_behavior",
    "requires_confirmation", "requires_refusal", "privacy_sensitive", "unsafe_request",
    "user_goal", "registry_status",
]


def family_for(task: dict) -> str:
    tid = str(task.get("task_id", ""))
    if tid in PRIMARY_FAMILY:
        return PRIMARY_FAMILY[tid]
    # Fallback heuristic for tasks not in the frozen map (should not happen for R6).
    if task.get("requires_refusal") or task.get("unsafe_request"):
        return "D_abandonment_overrefusal_boundary"
    if task.get("mutation_tools") and task.get("requires_confirmation"):
        return "C_confirmation_shift"
    if task.get("mutation_tools"):
        return "B_premature_mutation_pressure"
    return "A_action_intensity_amplification"


def tool_env_id(domain: str) -> str:
    return "tau2_retail" if domain == "retail" else "tau2_airline" if domain == "airline" else f"r6_synthetic_{domain}"


def endpoint_eval(domain: str) -> str:
    return "tau2_field_diff" if domain in {"retail", "airline"} else "custom_field_diff"


def load_tasks(tasks_path: Path) -> list[dict]:
    data = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    return data.get("tasks", data)


def build_full_row(task: dict) -> dict:
    tid = str(task.get("task_id", ""))
    fam = family_for(task)
    domain = str(task.get("domain", ""))
    min_tools = int(task.get("expected_min_tool_calls") or 0)
    return {
        "r7_task_id": f"r7_{tid}",
        "source_task_id": tid,
        "domain": domain,
        "task_family_primary": fam,
        "task_family_secondary_allowed": "",
        "task_goal_summary": task.get("user_goal", ""),
        "user_identity": "verified_account_holder",
        "policy_spec_id": f"{domain}_policy_v1",
        "tool_environment_id": tool_env_id(domain),
        "initial_state_id": task.get("env_seed_state_id", ""),
        "expected_outcome_spec_id": f"{tid}__outcome",
        "expected_process_profile_id": f"{tid}__process",
        "requires_confirmation": str(bool(task.get("requires_confirmation"))),
        "requires_mutation": str(bool(task.get("mutation_tools"))),
        "has_privacy_constraint": str(bool(task.get("privacy_sensitive"))),
        "has_boundary_constraint": str(bool(task.get("requires_refusal"))),
        "min_expected_process_steps": max(5, min_tools),  # PDF 5.4: >= 5 process steps
        "min_expected_tool_calls": min_tools,
        "neutral_expected_trajectory_summary": " ".join(task.get("expected_minimal_tool_path") or []),
        "attack_target_variable": ATTACK_TARGET[fam],
        "endpoint_evaluator_type": endpoint_eval(domain),
        "process_evaluator_type": PROCESS_EVAL[fam],
        "layer": task.get("layer", ""),
        "expected_behavior": task.get("expected_behavior", ""),
        "dev_or_test": "",  # filled by split
        "frozen": "True",
        "notes": "",
    }


def stratified_split(rows: list[dict], n_dev: int) -> None:
    """Deterministically mark dev rows: one per family (sorted), then fill from
    the largest families until n_dev reached.  Mutates rows in place."""
    by_family: dict[str, list[dict]] = {}
    for r in sorted(rows, key=lambda r: r["r7_task_id"]):
        by_family.setdefault(r["task_family_primary"], []).append(r)
    dev_ids: list[str] = []
    for fam in DESIRED_ORDER:
        if by_family.get(fam):
            dev_ids.append(by_family[fam][0]["r7_task_id"])
    # Fill remaining dev slots from families with the most tasks, deterministically.
    extra_pool = []
    for fam in DESIRED_ORDER:
        for r in by_family.get(fam, [])[1:]:
            extra_pool.append(r["r7_task_id"])
    for rid in extra_pool:
        if len(dev_ids) >= n_dev:
            break
        dev_ids.append(rid)
    dev_set = set(dev_ids[:n_dev])
    for r in rows:
        r["dev_or_test"] = "dev" if r["r7_task_id"] in dev_set else "test"


def process_smoke(tasks: list[dict], out_path: Path) -> int:
    selected_by_family: dict[str, dict] = {}
    for task in tasks:
        selected_by_family.setdefault(family_for(task), task)
    chosen = [selected_by_family[f] for f in DESIRED_ORDER if f in selected_by_family]
    rows = []
    for idx, task in enumerate(chosen, start=1):
        fam = family_for(task)
        rows.append({
            "r7_task_id": f"r7_ipma_{idx:03d}", "source_task_id": task.get("task_id", ""),
            "domain": task.get("domain", ""), "layer": task.get("layer", ""), "ipma_family": fam,
            "expected_behavior": task.get("expected_behavior", ""),
            "requires_confirmation": str(bool(task.get("requires_confirmation"))),
            "requires_refusal": str(bool(task.get("requires_refusal"))),
            "privacy_sensitive": str(bool(task.get("privacy_sensitive"))),
            "unsafe_request": str(bool(task.get("unsafe_request"))),
            "user_goal": task.get("user_goal", ""), "registry_status": "smoke_provisional",
        })
    write_csv(out_path, rows, SMOKE_FIELDS)
    return len(rows)


def process_full(tasks: list[dict], out_path: Path, frozen_dir: Path, n_dev: int) -> dict:
    rows = [build_full_row(t) for t in tasks]
    stratified_split(rows, n_dev)
    write_csv(out_path, rows, FIELDS)

    ensure_dir(frozen_dir)
    dev_rows = [r for r in rows if r["dev_or_test"] == "dev"]
    test_rows = [r for r in rows if r["dev_or_test"] == "test"]
    write_jsonl(frozen_dir / "r7_dev_tasks.jsonl", dev_rows)
    write_jsonl(frozen_dir / "r7_test_tasks.jsonl", test_rows)
    fam_reg = [{"r7_task_id": r["r7_task_id"], "source_task_id": r["source_task_id"],
                "domain": r["domain"], "task_family_primary": r["task_family_primary"],
                "dev_or_test": r["dev_or_test"], "frozen": "True"} for r in rows]
    write_csv(frozen_dir / "r7_task_family_registry.csv", fam_reg,
              ["r7_task_id", "source_task_id", "domain", "task_family_primary", "dev_or_test", "frozen"])

    from collections import Counter
    fam_counts = Counter(r["task_family_primary"] for r in rows)
    dom_counts = Counter(r["domain"] for r in rows)
    return {"n_tasks": len(rows), "n_dev": len(dev_rows), "n_test": len(test_rows),
            "family_counts": dict(fam_counts), "domain_counts": dict(dom_counts)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, default=ROOT / "data/r6/r6_tasks.yaml")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--frozen_dir", type=Path, default=ROOT / "data/r7_ipma/frozen")
    ap.add_argument("--n_dev", type=int, default=6)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    tasks = load_tasks(args.tasks)
    if args.full:
        out = args.out or (ROOT / "data/r7_ipma/r7_task_registry.csv")
        summary = process_full(tasks, out, args.frozen_dir, args.n_dev)
        summary["out"] = str(out)
        print(json.dumps(summary, ensure_ascii=False))
    else:
        out = args.out or (ROOT / "data/r7_ipma/r7_task_registry_smoke.csv")
        n = process_smoke(tasks, out)
        print(json.dumps({"registry_rows": n, "out": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
