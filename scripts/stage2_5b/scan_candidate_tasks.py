from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tau2.run import get_tasks

from src.adapters.normalize import IRREVERSIBLE_TOOLS
from src.stage2_5.official_tau_evaluator import official_basis


OUT_CSV = ROOT / "data" / "stage2_5b" / "candidate_tasks.csv"
OUT_REPORT = ROOT / "reports" / "stage2_5b" / "CANDIDATE_TASK_AUDIT.md"
OUT_JSON = ROOT / "artifacts" / "stage2_5b" / "candidate_task_scan.json"
DOMAINS = ["retail", "airline"]
TARGET_PER_DOMAIN = {"retail": 24, "airline": 7}  # expanded retail pool (Stage-2.5b CP-013): airline is all-floor, retail is the confirmatory domain


def action_name(action: Any) -> str:
    return str(getattr(action, "name", ""))


def action_args(action: Any) -> str:
    try:
        return json.dumps(getattr(action, "arguments", None), sort_keys=True, ensure_ascii=True)
    except TypeError:
        return str(getattr(action, "arguments", None))


def text_judge_components(basis: list[str]) -> list[str]:
    return [b for b in basis if b in {"NL_ASSERTION", "COMMUNICATE"}]


def row_for_task(domain: str, task: Any) -> dict[str, Any]:
    criteria = task.evaluation_criteria
    actions = getattr(criteria, "actions", None) or []
    names = [action_name(a) for a in actions if action_name(a)]
    write_names = [name for name in names if name in IRREVERSIBLE_TOOLS]
    read_names = [name for name in names if name and name not in IRREVERSIBLE_TOOLS]
    basis = official_basis(task)
    txt = text_judge_components(basis)
    branch_proxy = len(set(read_names)) + max(0, len(set(write_names)) - 1)
    multistage = len(actions) >= 4 and len(set(read_names)) >= 1 and len(write_names) >= 1
    policy_sensitive = len(write_names) > 0
    offline = not txt
    status = "candidate_structural"
    exclusion_reason = ""
    if not policy_sensitive:
        status = "excluded_no_mutation"
        exclusion_reason = "no irreversible/write action in reference actions"
    elif not multistage:
        status = "excluded_not_multistage"
        exclusion_reason = "reference workflow lacks enough read/write stages"
    elif branch_proxy < 2:
        status = "excluded_low_branch_proxy"
        exclusion_reason = "fewer than two evidence/branch proxy points"
    score = (
        (20 if status == "candidate_structural" else 0)
        + (5 if offline else 0)
        + min(len(actions), 12)
        + 2 * len(set(write_names))
        + len(set(read_names))
        + min(branch_proxy, 6)
    )
    return {
        "source_task_id": str(task.id),
        "domain": domain,
        "reward_basis": "|".join(basis),
        "official_reward_basis_fully_local": str(offline).lower(),
        "text_judge_components": "|".join(txt),
        "action_count": len(actions),
        "read_action_count": len(read_names),
        "write_action_count": len(write_names),
        "unique_read_tools": "|".join(sorted(set(read_names))),
        "unique_write_tools": "|".join(sorted(set(write_names))),
        "branch_proxy_count": branch_proxy,
        "has_policy_sensitive_decision": str(policy_sensitive).lower(),
        "is_multistage_reference": str(multistage).lower(),
        "status": status,
        "exclusion_reason": exclusion_reason,
        "score": score,
        "goal": str(getattr(task, "user_scenario", ""))[:500].replace("\n", " "),
        "reference_action_sequence": " > ".join(names),
        "reference_action_args": " || ".join(f"{action_name(a)}:{action_args(a)}" for a in actions),
    }


def scan() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    all_rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for domain in DOMAINS:
        tasks = get_tasks(domain)
        counts[domain] = len(tasks)
        for task in tasks:
            all_rows.append(row_for_task(domain, task))
    selected: list[dict[str, Any]] = []
    for domain in DOMAINS:
        domain_candidates = [
            r for r in all_rows
            if r["domain"] == domain and r["status"] == "candidate_structural"
        ]
        domain_candidates.sort(key=lambda r: (-int(r["score"]), int(r["source_task_id"])))
        for row in domain_candidates[: TARGET_PER_DOMAIN[domain]]:
            chosen = dict(row)
            chosen["selection_set"] = "screened_10_15"
            selected.append(chosen)
    selected_ids = {(r["domain"], r["source_task_id"]) for r in selected}
    for row in all_rows:
        row["selection_set"] = "screened_10_15" if (row["domain"], row["source_task_id"]) in selected_ids else ""
    return all_rows, selected, counts


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    selected = [r for r in rows if r["selection_set"]]
    fields = list(selected[0])
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(selected)


def write_json(all_rows: list[dict[str, Any]], selected: list[dict[str, Any]], counts: dict[str, int]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "domains_scanned": counts,
                "n_all_rows": len(all_rows),
                "n_selected": len(selected),
                "selected": selected,
                "all_rows": all_rows,
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )


def write_report(selected: list[dict[str, Any]], counts: dict[str, int]) -> None:
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Candidate Task Audit",
        "",
        "Scope:",
        f"- Domains scanned: {', '.join(f'{k}={v}' for k, v in counts.items())}",
        f"- Selected structural candidates: {len(selected)}",
        f"- Candidate CSV: `{OUT_CSV.relative_to(ROOT)}`",
        f"- Full scan JSON: `{OUT_JSON.relative_to(ROOT)}`",
        "",
        "Selection rule:",
        "- Use only real tau2 tasks from the frozen local benchmark.",
        "- Require at least one irreversible/write action, a multistage read/write reference workflow, and at least two evidence/branch proxy points.",
        "- Do not use treatment outcomes or model success rates.",
        "",
        "| domain | source_task_id | reward_basis | actions | writes | branch_proxy | fully_local | write_tools |",
        "|---|---:|---|---:|---:|---:|---|---|",
    ]
    for row in selected:
        lines.append(
            f"| {row['domain']} | {row['source_task_id']} | {row['reward_basis']} | "
            f"{row['action_count']} | {row['write_action_count']} | {row['branch_proxy_count']} | "
            f"{row['official_reward_basis_fully_local']} | {row['unique_write_tools']} |"
        )
    lines.extend(
        [
            "",
            "Calibration status:",
            "- These are structural candidates only.",
            "- Confirmatory inclusion still requires neutral-condition calibration with calibration seeds separated from confirmatory seeds.",
            "- Tasks with text-judged reward components must keep `official_reward_basis_success` missing unless a frozen text evaluator is added.",
        ]
    )
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    all_rows, selected, counts = scan()
    write_csv(all_rows)
    write_json(all_rows, selected, counts)
    write_report(selected, counts)
    print(f"scanned={sum(counts.values())} selected={len(selected)}")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_REPORT}")
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
