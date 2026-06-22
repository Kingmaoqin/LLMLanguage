from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.run import get_tasks

from src.stage2_5b.evaluator import official_basis


TASK_SPEC_PATH = ROOT / "data" / "irmstu_tasks" / "tau_adapted_tasks.yaml"
OUT_CSV = ROOT / "data" / "stage2_5b" / "task_reward_basis.csv"
OUT_REPORT = ROOT / "reports" / "stage2_5b" / "OFFICIAL_REWARD_BASIS_AUDIT.md"


def load_stage2_tasks() -> list[dict[str, Any]]:
    payload = yaml.safe_load(TASK_SPEC_PATH.read_text(encoding="utf-8"))
    return list(payload["mini_stage2_v1"])


def bool_str(value: bool) -> str:
    return "true" if value else "false"


def audit_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in load_stage2_tasks():
        tau_task = get_tasks(spec["source_domain"], task_ids=[str(spec["source_task_id"])])[0]
        criteria = tau_task.evaluation_criteria
        basis = official_basis(tau_task)
        has_db = "DB" in basis or "ENV_ASSERTION" in basis
        has_comm = "COMMUNICATE" in basis
        has_nl = "NL_ASSERTION" in basis
        text_judge_components = []
        if has_nl:
            text_judge_components.append("NL_ASSERTION")
        if has_comm:
            text_judge_components.append("COMMUNICATE")
        local_components = []
        if has_db:
            local_components.append("DB")
        rows.append(
            {
                "task_id": spec["task_id"],
                "source_domain": spec["source_domain"],
                "source_task_id": str(spec["source_task_id"]),
                "reward_basis": "|".join(basis),
                "has_db_component": bool_str(has_db),
                "has_communicate_component": bool_str(has_comm),
                "has_nl_assertion_component": bool_str(has_nl),
                "actions_count": len(getattr(criteria, "actions", None) or []),
                "env_assertions_count": len(getattr(criteria, "env_assertions", None) or []),
                "communicate_info_count": len(getattr(criteria, "communicate_info", None) or []),
                "nl_assertions_count": len(getattr(criteria, "nl_assertions", None) or []),
                "locally_evaluable_components": "|".join(local_components),
                "requires_text_judge_components": "|".join(text_judge_components),
                "official_reward_basis_fully_local": bool_str(not text_judge_components),
                "offline_evaluability_note": (
                    "DB component can be locally proxied; full official success requires text judge"
                    if text_judge_components
                    else "official reward basis appears locally evaluable"
                ),
            }
        )
    return rows


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict[str, Any]]) -> None:
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    fully_local = [r for r in rows if r["official_reward_basis_fully_local"] == "true"]
    text_judge = [r for r in rows if r["requires_text_judge_components"]]
    lines = [
        "# Official Reward Basis Audit",
        "",
        "Scope:",
        f"- Task spec: `{TASK_SPEC_PATH.relative_to(ROOT)}`",
        f"- Output table: `{OUT_CSV.relative_to(ROOT)}`",
        f"- Tasks audited: {len(rows)}",
        "",
        "Summary:",
        f"- Fully locally evaluable official reward basis: {len(fully_local)}/{len(rows)}",
        f"- Require text-judged official components: {len(text_judge)}/{len(rows)}",
        "",
        "| task_id | source | reward_basis | local_proxy_components | text_judge_components | actions | nl_assertions |",
        "|---|---:|---|---|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {task_id} | {source_domain}:{source_task_id} | {reward_basis} | "
            "{locally_evaluable_components} | {requires_text_judge_components} | "
            "{actions_count} | {nl_assertions_count} |".format(**row)
        )
    lines.extend(
        [
            "",
            "Metric semantics for Stage-2.5b:",
            "- `official_reward_basis_success`: complete official reward-basis success; missing when any required official text-judged component is unavailable offline.",
            "- `local_proxy_success`: success on the locally computable official components only, usually DB state.",
            "- `safe_task_success`: `local_proxy_success` plus policy, evidence-before-mutation, confirmation, and invalid-run checks.",
            "",
            "Consequence:",
            "- These six legacy candidate tasks cannot use a DB-only value as full official success.",
            "- Later task calibration must either select tasks with fully computable official reward basis or report missing official success explicitly.",
        ]
    )
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = audit_rows()
    write_csv(rows)
    write_report(rows)
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_REPORT}")
    print(f"tasks={len(rows)} fully_local={sum(r['official_reward_basis_fully_local'] == 'true' for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
