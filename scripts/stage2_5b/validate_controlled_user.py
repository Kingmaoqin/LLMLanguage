from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.data_model.message import AssistantMessage
from tau2.run import get_tasks

from src.stage2_5b.controlled_user import (
    ControlledUser,
    ControlledUserState,
    MAIN_CONDITIONS,
    TASK_POLICIES,
    generic_policy_from_task,
    has_gold_tool_leakage,
    has_hidden_or_style_leakage,
    stable_text_hash,
)


STATIC_TASK_IDS = ["4", "30", "55", "7", "12", "44"]
STYLE_TEMPLATE_PATH = ROOT / "data" / "stage2_5b" / "social_style_templates_frozen.yaml"
CANDIDATE_TASKS_CSV = ROOT / "data" / "stage2_5b" / "candidate_tasks.csv"
OUT_DIR = ROOT / "results" / "stage2_5b_validation"
REPORT_DIR = ROOT / "reports" / "stage2_5b"
CSV_PATH = OUT_DIR / "controlled_user_invariance.csv"
REPORT_PATH = REPORT_DIR / "CONTROLLED_USER_VALIDATION.md"


OBJECT_ID_RE = re.compile(
    r"[\w.+-]+@[\w.-]+|"
    r"\b[A-Z0-9]{4,}\b|"
    r"\b[a-z]+_[a-z]+_[0-9]{3,}\b|"
    r"\b[0-9]{4,5}\b"
)


@dataclass(frozen=True)
class Fixture:
    name: str
    assistant_text: str
    turn_index: int
    user_turn_idx: int
    assistant_text_turns_before: int = 0


@dataclass(frozen=True)
class TaskSpec:
    task_key: str
    source_task_id: str
    domain: str
    policy_override: Any = None


def load_task_specs() -> list[TaskSpec]:
    specs = [
        TaskSpec(task_key=f"static_{task_id}", source_task_id=task_id, domain=TASK_POLICIES[task_id].domain)
        for task_id in STATIC_TASK_IDS
    ]
    if not CANDIDATE_TASKS_CSV.exists():
        return specs
    with CANDIDATE_TASKS_CSV.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("status") != "candidate_structural":
                continue
            domain = row["domain"]
            source_task_id = str(row["source_task_id"])
            tau2_task = get_tasks(domain, task_ids=[source_task_id])[0]
            policy_override = None
            if source_task_id not in TASK_POLICIES:
                policy_override = generic_policy_from_task(
                    source_task_id=source_task_id,
                    domain=domain,
                    task_label=f"{domain}_{source_task_id}",
                    user_scenario=tau2_task.user_scenario,
                )
            specs.append(
                TaskSpec(
                    task_key=f"{domain}_{source_task_id}",
                    source_task_id=source_task_id,
                    domain=domain,
                    policy_override=policy_override,
                )
            )
    return specs


def load_first_templates() -> dict[str, dict[str, str]]:
    with STYLE_TEMPLATE_PATH.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    templates: dict[str, dict[str, str]] = {}
    for condition in MAIN_CONDITIONS:
        entry = payload["conditions"][condition]
        first = entry["templates"][0]
        templates[condition] = {
            "mode": entry["mode"],
            "template_id": first["template_id"],
            "text": first["text"],
        }
    return templates


def fixtures_for_task(source_task_id: str) -> list[Fixture]:
    fixtures = [
        Fixture("opening", "Hello, how can I help?", turn_index=0, user_turn_idx=0),
        Fixture(
            "identity",
            "Can you confirm your identity with your name, email, ZIP code, user ID, or reservation ID?",
            turn_index=1,
            user_turn_idx=1,
            assistant_text_turns_before=1,
        ),
        Fixture(
            "payment_or_cost",
            "Please provide any payment card, fee limit, cost limit, or charge rule needed for this request.",
            turn_index=1,
            user_turn_idx=1,
            assistant_text_turns_before=1,
        ),
        Fixture(
            "preference",
            "Which option do you prefer: exchange, return, business upgrade, or list the items first?",
            turn_index=1,
            user_turn_idx=1,
            assistant_text_turns_before=1,
        ),
        Fixture(
            "confirmation",
            "Would you like me to proceed with this action?",
            turn_index=1,
            user_turn_idx=1,
            assistant_text_turns_before=1,
        ),
        Fixture(
            "denial",
            "I should not proceed if this is not allowed.",
            turn_index=1,
            user_turn_idx=1,
            assistant_text_turns_before=1,
        ),
        Fixture(
            "completion",
            "The task is completed. Is there anything else I can help with?",
            turn_index=2,
            user_turn_idx=2,
            assistant_text_turns_before=2,
        ),
    ]
    if source_task_id == "7":
        fixtures.append(
            Fixture(
                "task7_extra_upcoming_flights",
                "I have handled the named reservations.",
                turn_index=1,
                user_turn_idx=1,
                assistant_text_turns_before=2,
            )
        )
    return fixtures


def extract_object_ids(text: str) -> str:
    ids = sorted(set(m.group(0) for m in OBJECT_ID_RE.finditer(text or "")))
    return "|".join(ids)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def run_case(spec: TaskSpec, fixture: Fixture, condition: str, template: dict[str, str]) -> dict[str, Any]:
    user = ControlledUser(
        spec.source_task_id,
        condition=condition,
        template_id=template["template_id"],
        template_text=template["text"],
        policy_override=spec.policy_override,
    )
    state = ControlledUserState(
        messages=[],
        system_messages=[],
        turn_index=fixture.turn_index,
        assistant_text_turns=fixture.assistant_text_turns_before,
    )
    user.style.user_turn_idx = fixture.user_turn_idx
    message, _state = user.generate_next_message(
        AssistantMessage(role="assistant", content=fixture.assistant_text),
        state,
    )
    event = user.events[-1]
    clean_text = event["clean_text"]
    styled_text = event["styled_text"]
    return {
        "task_id": spec.task_key,
        "source_task_id": spec.source_task_id,
        "domain": spec.domain,
        "policy_kind": "static" if spec.policy_override is None else "generic",
        "fixture": fixture.name,
        "condition": condition,
        "template_id": template["template_id"],
        "template_mode": template["mode"],
        "turn_index": fixture.turn_index,
        "user_turn_idx": fixture.user_turn_idx,
        "speech_act": event["speech_act"],
        "decision": event["decision"],
        "confirmation": str(bool(event["confirmation"])).lower(),
        "factual_slots_json": canonical_json(event["factual_slots"]),
        "object_ids": extract_object_ids(clean_text),
        "clean_text_hash": stable_text_hash(clean_text),
        "styled_text_hash": stable_text_hash(styled_text),
        "clean_text": clean_text,
        "styled_text": styled_text,
        "styled_contains_clean": str(clean_text in styled_text).lower(),
        "wrapper_applied": str(bool(event["wrapper_event"]["wrapped"])).lower(),
        "gold_tool_leakage": str(has_gold_tool_leakage(clean_text)).lower(),
        "hidden_or_style_leakage": str(has_hidden_or_style_leakage(clean_text)).lower(),
        "message_content_matches_event": str(message.content == styled_text).lower(),
    }


def group_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["task_id"], row["fixture"]), []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for (task_id, fixture), group in sorted(grouped.items()):
        summary_rows.append(
            {
                "task_id": task_id,
                "fixture": fixture,
                "condition_count": len({r["condition"] for r in group}),
                "clean_response_agreement": len({r["clean_text_hash"] for r in group}) == 1,
                "factual_slot_agreement": len({r["factual_slots_json"] for r in group}) == 1,
                "confirmation_decision_agreement": len({r["confirmation"] for r in group}) == 1,
                "decision_agreement": len({r["decision"] for r in group}) == 1,
                "object_id_agreement": len({r["object_ids"] for r in group}) == 1,
                "styled_contains_clean": all(r["styled_contains_clean"] == "true" for r in group),
                "message_content_matches_event": all(r["message_content_matches_event"] == "true" for r in group),
                "gold_tool_leakage_count": sum(r["gold_tool_leakage"] == "true" for r in group),
                "hidden_or_style_leakage_count": sum(r["hidden_or_style_leakage"] == "true" for r in group),
            }
        )
    return summary_rows


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "task_id",
        "source_task_id",
        "domain",
        "policy_kind",
        "fixture",
        "condition",
        "template_id",
        "template_mode",
        "turn_index",
        "user_turn_idx",
        "speech_act",
        "decision",
        "confirmation",
        "factual_slots_json",
        "object_ids",
        "clean_text_hash",
        "styled_text_hash",
        "clean_text",
        "styled_text",
        "styled_contains_clean",
        "wrapper_applied",
        "gold_tool_leakage",
        "hidden_or_style_leakage",
        "message_content_matches_event",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> None:
    total_groups = len(summary_rows)
    total_condition_rows = len(rows)
    metrics = {
        "fixture_groups": total_groups,
        "condition_rows": total_condition_rows,
        "task_count": len({r["task_id"] for r in rows}),
        "condition_count": len({r["condition"] for r in rows}),
        "clean_response_agreement": sum(r["clean_response_agreement"] for r in summary_rows),
        "factual_slot_agreement": sum(r["factual_slot_agreement"] for r in summary_rows),
        "confirmation_decision_agreement": sum(r["confirmation_decision_agreement"] for r in summary_rows),
        "decision_agreement": sum(r["decision_agreement"] for r in summary_rows),
        "object_id_agreement": sum(r["object_id_agreement"] for r in summary_rows),
        "styled_contains_clean": sum(r["styled_contains_clean"] for r in summary_rows),
        "message_content_matches_event": sum(r["message_content_matches_event"] for r in summary_rows),
        "gold_tool_leakage_count": sum(r["gold_tool_leakage_count"] for r in summary_rows),
        "hidden_or_style_leakage_count": sum(r["hidden_or_style_leakage_count"] for r in summary_rows),
    }
    all_pass = (
        metrics["clean_response_agreement"] == total_groups
        and metrics["factual_slot_agreement"] == total_groups
        and metrics["confirmation_decision_agreement"] == total_groups
        and metrics["decision_agreement"] == total_groups
        and metrics["object_id_agreement"] == total_groups
        and metrics["styled_contains_clean"] == total_groups
        and metrics["message_content_matches_event"] == total_groups
        and metrics["gold_tool_leakage_count"] == 0
        and metrics["hidden_or_style_leakage_count"] == 0
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Controlled User Validation",
        "",
        f"Status: {'PASS' if all_pass else 'FAIL'}",
        "",
        "Scope:",
        f"- Static source tasks: {', '.join(STATIC_TASK_IDS)}",
        f"- Candidate task specs included: {len({r['task_id'] for r in rows if not str(r['task_id']).startswith('static_')})}",
        f"- Policy kinds: {', '.join(sorted({r['policy_kind'] for r in rows}))}",
        f"- Main style conditions: {', '.join(MAIN_CONDITIONS)}",
        f"- Fixture groups: {total_groups}",
        f"- Condition-level rows: {total_condition_rows}",
        f"- CSV artifact: `{CSV_PATH.relative_to(ROOT)}`",
        "",
        "Invariance checks:",
        f"- Clean response agreement: {metrics['clean_response_agreement']}/{total_groups}",
        f"- Factual slot agreement: {metrics['factual_slot_agreement']}/{total_groups}",
        f"- Confirmation decision agreement: {metrics['confirmation_decision_agreement']}/{total_groups}",
        f"- Response decision agreement: {metrics['decision_agreement']}/{total_groups}",
        f"- Object ID agreement: {metrics['object_id_agreement']}/{total_groups}",
        f"- Styled text contains clean text: {metrics['styled_contains_clean']}/{total_groups}",
        f"- UserMessage content matches logged styled text: {metrics['message_content_matches_event']}/{total_groups}",
        f"- Gold tool-name leakage count: {metrics['gold_tool_leakage_count']}",
        f"- Hidden/style/process leakage count: {metrics['hidden_or_style_leakage_count']}",
        "",
        "Interpretation:",
        "- The clean user policy is deterministic across all six main social-style conditions for the tested task prompts.",
        "- Social style is applied only as a wrapper around the already selected clean response.",
        "- This validates the user-simulator layer; it does not by itself validate agent behavior or tau2 final-state outcomes.",
        "",
    ]
    if not all_pass:
        lines.extend(["Failing groups:", ""])
        for row in summary_rows:
            if not (
                row["clean_response_agreement"]
                and row["factual_slot_agreement"]
                and row["confirmation_decision_agreement"]
                and row["decision_agreement"]
                and row["object_id_agreement"]
                and row["styled_contains_clean"]
                and row["message_content_matches_event"]
                and row["gold_tool_leakage_count"] == 0
                and row["hidden_or_style_leakage_count"] == 0
            ):
                lines.append(f"- task={row['task_id']} fixture={row['fixture']} row={canonical_json(row)}")
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    templates = load_first_templates()
    task_specs = load_task_specs()
    rows: list[dict[str, Any]] = []
    for spec in task_specs:
        for fixture in fixtures_for_task(spec.source_task_id):
            for condition in MAIN_CONDITIONS:
                rows.append(run_case(spec, fixture, condition, templates[condition]))

    write_csv(rows)
    summary_rows = group_rows(rows)
    write_report(rows, summary_rows)

    failed = [
        row
        for row in summary_rows
        if not (
            row["condition_count"] == len(MAIN_CONDITIONS)
            and row["clean_response_agreement"]
            and row["factual_slot_agreement"]
            and row["confirmation_decision_agreement"]
            and row["decision_agreement"]
            and row["object_id_agreement"]
            and row["styled_contains_clean"]
            and row["message_content_matches_event"]
            and row["gold_tool_leakage_count"] == 0
            and row["hidden_or_style_leakage_count"] == 0
        )
    ]
    if failed:
        print(f"Controlled user validation failed for {len(failed)} fixture groups. See {REPORT_PATH}")
        return 1
    print(f"Controlled user validation PASS: {len(summary_rows)} fixture groups, {len(rows)} condition rows.")
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
