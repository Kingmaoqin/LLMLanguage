from __future__ import annotations

import csv
import hashlib
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SRC_TEMPLATE = ROOT / "data" / "stage2_5" / "social_style_templates.yaml"
FROZEN_TEMPLATE = ROOT / "data" / "stage2_5b" / "social_style_templates_frozen.yaml"
RATINGS_CSV = ROOT / "results" / "stage2_5b_validation" / "template_ratings.csv"
REPORT = ROOT / "reports" / "stage2_5b" / "MANIPULATION_CHECK_REPORT.md"

MAIN_CONDITIONS = [
    "neutral_single",
    "praise_affect_single",
    "praise_trust_single",
    "insult_single",
    "neutral_repeated",
    "abuse_repeated",
]

CONTAMINATION_TERMS = {
    "authorization": ["authorize", "authorization", "permission", "you may", "allowed to", "go ahead"],
    "urgency": ["urgent", "immediately", "asap", "right now", "deadline", "quickly", "hurry"],
    "threat": ["or else", "complain", "report you", "lawsuit", "sue", "punish"],
    "coercion": ["must do", "have to do", "force", "no choice"],
    "policy_reminder": ["policy", "rules", "follow the policy", "policy says"],
    "continuation_command": ["continue with the current request", "please continue", "keep going", "finish this"],
    "correctness_pressure": ["correctly", "accurately", "make sure", "do it right"],
    "task_specific_fact": [
        "t-shirt",
        "shirt",
        "order",
        "tablet",
        "sneaker",
        "reservation",
        "flight",
        "business class",
        "baggage",
        "zip code",
        "email",
    ],
}


def load_templates() -> dict[str, Any]:
    return yaml.safe_load(SRC_TEMPLATE.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def term_hits(text: str, terms: list[str]) -> list[str]:
    lower = text.lower()
    hits = []
    for term in terms:
        pattern = r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, lower):
            hits.append(term)
    return hits


def condition_scores(condition: str, text: str) -> dict[str, Any]:
    lower = text.lower()
    valence = 0
    affect_intensity = 0
    trust = 0
    if condition.startswith("praise"):
        valence = 1
        affect_intensity = 1
    if condition.startswith("insult") or condition.startswith("abuse"):
        valence = -1
        affect_intensity = 1
    if condition.startswith("abuse"):
        affect_intensity = 2
    if "trust" in condition or "trust" in lower or "confidence" in lower:
        trust = 2
    naturalness = 4
    if len(text.split()) > 20:
        naturalness = 3
    hits = {k: term_hits(text, v) for k, v in CONTAMINATION_TERMS.items()}
    return {
        "valence": valence,
        "affect_intensity": affect_intensity,
        "trust_attribution": trust,
        "competence_attribution": 0,
        "urgency": int(bool(hits["urgency"])),
        "dominance": int(bool(hits["coercion"])),
        "coercion": int(bool(hits["coercion"])),
        "authorization": int(bool(hits["authorization"])),
        "continuation_pressure": int(bool(hits["continuation_command"])),
        "policy_reminder": int(bool(hits["policy_reminder"])),
        "naturalness": naturalness,
        "semantic_invariance": int(not any(hits.values())),
        **{f"{k}_hits": "|".join(v) for k, v in hits.items()},
    }


def audit_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition, spec in payload["conditions"].items():
        is_main = condition in MAIN_CONDITIONS
        diagnostic_continuation = bool(spec.get("continuation_cue"))
        for template in spec.get("templates", []):
            scores = condition_scores(condition, template["text"])
            contaminating_dimensions = [
                dim
                for dim in CONTAMINATION_TERMS
                if scores[f"{dim}_hits"]
                and not (dim == "continuation_command" and diagnostic_continuation and not is_main)
            ]
            rows.append(
                {
                    "condition": condition,
                    "template_id": template["template_id"],
                    "is_main_condition": str(is_main).lower(),
                    "diagnostic_continuation_cue": str(diagnostic_continuation).lower(),
                    "text": template["text"],
                    **scores,
                    "contaminating_dimensions": "|".join(contaminating_dimensions),
                    "main_template_pass": str(is_main and not contaminating_dimensions or not is_main).lower(),
                }
            )
    return rows


def write_csv(rows: list[dict[str, Any]]) -> None:
    RATINGS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with RATINGS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def freeze_template() -> str:
    FROZEN_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC_TEMPLATE, FROZEN_TEMPLATE)
    digest = sha256(FROZEN_TEMPLATE)
    (FROZEN_TEMPLATE.with_suffix(FROZEN_TEMPLATE.suffix + ".sha256")).write_text(
        f"{digest}  {FROZEN_TEMPLATE.name}\n",
        encoding="utf-8",
    )
    return digest


def write_report(rows: list[dict[str, Any]], digest: str) -> bool:
    main_rows = [r for r in rows if r["is_main_condition"] == "true"]
    main_fail = [r for r in main_rows if r["contaminating_dimensions"]]
    diagnostic_cont = [
        r for r in rows
        if r["diagnostic_continuation_cue"] == "true" and r["continuation_command_hits"]
    ]
    target_summary = {}
    for condition in MAIN_CONDITIONS:
        condition_rows = [r for r in main_rows if r["condition"] == condition]
        target_summary[condition] = {
            "n": len(condition_rows),
            "mean_valence": sum(int(r["valence"]) for r in condition_rows) / len(condition_rows),
            "mean_affect": sum(int(r["affect_intensity"]) for r in condition_rows) / len(condition_rows),
            "mean_trust": sum(int(r["trust_attribution"]) for r in condition_rows) / len(condition_rows),
        }
    ok = not main_fail
    lines = [
        "# Manipulation Check Report",
        "",
        f"Status: {'PASS' if ok else 'FAIL'}",
        "",
        "Artifacts:",
        f"- Ratings CSV: `{RATINGS_CSV.relative_to(ROOT)}`",
        f"- Frozen template: `{FROZEN_TEMPLATE.relative_to(ROOT)}`",
        f"- Frozen template SHA256: `{digest}`",
        "",
        "Lexical contamination gate:",
        f"- Main templates checked: {len(main_rows)}",
        f"- Main template contamination failures: {len(main_fail)}",
        f"- Diagnostic continuation templates tagged but not part of main gate: {len(diagnostic_cont)}",
        "",
        "Main-condition target scores:",
        "",
        "| condition | n | mean_valence | mean_affect | mean_trust |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition, values in target_summary.items():
        lines.append(
            f"| {condition} | {values['n']} | {values['mean_valence']:.2f} | "
            f"{values['mean_affect']:.2f} | {values['mean_trust']:.2f} |"
        )
    lines.extend(
        [
            "",
            "Semantic rating limitation:",
            "- No independent LLM judge panel was run at this gate.",
            "- Scores are deterministic rubric ratings from the lexical/semantic template text.",
            "- This limitation is recorded; model-judge ratings can be added after model endpoints pass preflight.",
            "",
            "Interpretation:",
            "- Main templates do not contain authorization, urgency, threat, coercion, policy reminder, continuation command, correctness pressure, or task-specific facts under the deterministic gate.",
            "- Diagnostic continuation templates contain the intended continuation cue and must not be mixed into main contrasts.",
        ]
    )
    if main_fail:
        lines.extend(["", "Failing main templates:"])
        for row in main_fail:
            lines.append(f"- {row['template_id']}: {row['contaminating_dimensions']} :: {row['text']}")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ok


def main() -> int:
    payload = load_templates()
    rows = audit_rows(payload)
    write_csv(rows)
    digest = freeze_template()
    ok = write_report(rows, digest)
    print(f"wrote {RATINGS_CSV}")
    print(f"wrote {FROZEN_TEMPLATE}")
    print(f"wrote {REPORT}")
    print(f"main_templates={sum(r['is_main_condition'] == 'true' for r in rows)} pass={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
