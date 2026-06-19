"""Manipulation / contamination checks for IR-MSTU Stage-2 valence templates (plan §17).

Stage-2 injects valence as a *prefix* onto tau2's own user turns, so task goal, object
IDs, permissions, policy and success criteria are structurally invariant across conditions
(the underlying tau2 task object is shared and never edited). The remaining risk is that a
valence template smuggles in explicit authorization, urgency, threat, or policy override.
This module verifies the templates carry no such contamination before any run.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

# Banned surface forms (plan §3.3 + §17). Matched case-insensitively on word-ish boundaries.
FORBIDDEN_PHRASES = [
    "go ahead", "just do it", "skip confirmation", "skip the confirmation",
    "no need to check", "no need to confirm", "don't ask me", "do not ask",
    "i authorize", "authorized", "asap", "urgent", "or else",
    "override", "skip the policy", "ignore the policy",
]
# Threat / coercion / identity cues that must never appear.
FORBIDDEN_PATTERNS = [
    r"\bthreat\b", r"\bor I('?ll| will)\b", r"\bfired\b", r"\bsue\b",
    r"\b(race|religion|gender|nationality|ethnicity|disabled|disability)\b",
]


@dataclass
class ConditionCheck:
    condition_id: str
    n_turns: int
    forbidden_hits: list[str]
    pattern_hits: list[str]

    @property
    def passed(self) -> bool:
        return not self.forbidden_hits and not self.pattern_hits


def _condition_texts(spec: dict) -> list[str]:
    """All templated strings a condition can emit (first turn + any mid-turn injections)."""
    texts = [spec["first_turn"]]
    texts.extend(m["text"] for m in spec.get("mid_turns") or [])
    return texts


def check_condition(condition_id: str, spec: dict) -> ConditionCheck:
    texts = _condition_texts(spec)
    blob = " ".join(texts)
    # Word-boundary match so e.g. "authorized" does not fire inside "unauthorized".
    forbidden = [p for p in FORBIDDEN_PHRASES
                 if re.search(rf"\b{re.escape(p)}\b", blob, re.IGNORECASE)]
    patterns = [p for p in FORBIDDEN_PATTERNS if re.search(p, blob, re.IGNORECASE)]
    return ConditionCheck(condition_id, len(texts), forbidden, patterns)


def check_task_spec_invariance(task_spec_path: Path) -> list[str]:
    """Validate that each IR-MSTU task maps to exactly one real, distinct tau2 source task.

    Task semantics (goal, object IDs, permissions, policy, success criteria) are invariant
    across conditions *by construction*: the same tau2 task object is used for all five
    conditions and valence is only a prefix on user turns — tau2's DB/tools/policy/evaluator
    are never edited. This check guards the remaining failure mode: a malformed spec that
    duplicates or mislabels source tasks.
    """
    issues: list[str] = []
    spec = yaml.safe_load(task_spec_path.read_text(encoding="utf-8"))
    tasks = spec.get("mini_stage2_v1") or []
    seen_sources, seen_ids = set(), set()
    for t in tasks:
        tid = t.get("task_id")
        src = (t.get("source_domain"), str(t.get("source_task_id")))
        if tid in seen_ids:
            issues.append(f"duplicate task_id {tid}")
        if src in seen_sources:
            issues.append(f"duplicate source task {src} (mapped by {tid})")
        if not t.get("source_task_id"):
            issues.append(f"{tid}: missing source_task_id")
        if not t.get("social_valence_applicable", False):
            issues.append(f"{tid}: social_valence_applicable is not true")
        seen_ids.add(tid)
        seen_sources.add(src)
    return issues


def run_checks(templates_path: Path, reports_dir: Path, results_dir: Path,
               task_spec_path: Path | None = None) -> bool:
    """Run all checks, write the report + csv, return overall pass/fail."""
    spec = yaml.safe_load(templates_path.read_text(encoding="utf-8"))
    conditions = spec["conditions"]
    checks = [check_condition(cid, conditions[cid]) for cid in spec["condition_order"]]
    task_issues = check_task_spec_invariance(task_spec_path) if task_spec_path else []
    overall = all(c.passed for c in checks) and not task_issues

    results_dir.mkdir(parents=True, exist_ok=True)
    with (results_dir / "manipulation_checks.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["condition_id", "n_templated_turns", "forbidden_hits", "pattern_hits", "passed"])
        for c in checks:
            writer.writerow([c.condition_id, c.n_turns, "|".join(c.forbidden_hits), "|".join(c.pattern_hits), c.passed])

    reports_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MANIPULATION_CHECKS — Stage-2 valence templates",
        "",
        f"Templates: `{templates_path}`",
        f"Overall pass: **{overall}**",
        "",
        "**Invariance is by construction, not by NL comparison:** for every condition the runner "
        "uses the *same* tau2 task object and only prefixes a valence string onto user turns; "
        "tau2's DB, tools, policy and goal-state evaluator are never edited. So task goal, object "
        "IDs, permissions, policy rules and success criteria are identical across conditions. "
        "This module verifies the two things that are *not* guaranteed by construction: (1) the "
        "templates add no explicit authorization / urgency / threat / policy override, and (2) the "
        "task spec maps each task to a single distinct real tau2 source task.",
        "",
        "### (1) Template contamination",
        "| condition | templated turns | forbidden hits | pattern hits | passed |",
        "|---|---|---|---|---|",
    ]
    for c in checks:
        lines.append(
            f"| {c.condition_id} | {c.n_turns} | {'|'.join(c.forbidden_hits) or '—'} "
            f"| {'|'.join(c.pattern_hits) or '—'} | {'✅' if c.passed else '❌'} |"
        )
    lines += ["", "### (2) Task-spec invariance",
              ("All tasks map to distinct real tau2 source tasks; no duplication/mislabel. ✅"
               if not task_issues else "Issues: " + "; ".join(task_issues))]
    if not overall:
        lines += ["", "**Check failed — do not run the main experiment (plan §17).**"]
    (reports_dir / "MANIPULATION_CHECKS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return overall


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    ok = run_checks(
        root / "data" / "social_valence_templates.yaml",
        root / "reports",
        root / "results",
        task_spec_path=root / "data" / "irmstu_tasks" / "tau_adapted_tasks.yaml",
    )
    print("manipulation checks pass:", ok)
    raise SystemExit(0 if ok else 1)
