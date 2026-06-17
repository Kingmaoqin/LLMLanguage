"""Integrity checks shared by Stage-2.5 audit and runner scripts."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


FORBIDDEN_MAIN_PATTERNS = {
    "continuation_or_finish": r"\b(continue|finish|complete|carry on|keep going|proceed)\b",
    "policy_instruction": r"\b(policy|rule|correctly|safely|use tools?|follow)\b",
    "authorization": r"\b(authorize|permission|approve|confirm|go ahead|do it)\b",
    "task_fact": r"\b(order|reservation|flight|cancel|return|exchange|address|zip|email)\b",
}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def check_template_spec(path: Path) -> list[dict[str, Any]]:
    import re

    spec = load_yaml(path)
    rows: list[dict[str, Any]] = []
    for condition, condition_spec in spec.get("conditions", {}).items():
        is_diagnostic_continuation = condition.endswith("_with_continuation")
        for tmpl in condition_spec.get("templates", []):
            text = str(tmpl.get("text") or "")
            hits = []
            for name, pat in FORBIDDEN_MAIN_PATTERNS.items():
                if is_diagnostic_continuation and name == "continuation_or_finish":
                    continue
                if re.search(pat, text, flags=re.IGNORECASE):
                    hits.append(name)
            rows.append({
                "condition_id": condition,
                "template_id": tmpl.get("template_id"),
                "mode": condition_spec.get("mode"),
                "text": text,
                "is_diagnostic_continuation": is_diagnostic_continuation,
                "n_forbidden_hits": len(hits),
                "forbidden_hits": "|".join(hits),
                "pass": len(hits) == 0,
            })
    return rows


def summarize_stage2_results(results_dir: Path) -> dict[str, Any]:
    import csv
    import json

    metrics_path = results_dir / "run_metrics.csv"
    rows = list(csv.DictReader(metrics_path.open(encoding="utf-8"))) if metrics_path.exists() else []
    run_ids = [r.get("run_id") for r in rows]
    dupes = [k for k, v in Counter(run_ids).items() if k and v > 1]
    by_model_condition = Counter((r.get("model_alias"), r.get("condition_id")) for r in rows)
    json_counts = {}
    for path in sorted(results_dir.glob("*.jsonl")):
        json_counts[path.name] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    repeated = defaultdict(set)
    for r in rows:
        repeated[(r.get("model_alias"), r.get("task_id"), r.get("condition_id"))].add(r.get("repeat_id"))
    repeat_counts = Counter(len(v) for v in repeated.values())

    return {
        "results_dir": str(results_dir),
        "n_metric_rows": len(rows),
        "n_duplicate_run_ids": len(dupes),
        "duplicate_run_ids": dupes,
        "by_model_condition": {f"{k[0]}::{k[1]}": v for k, v in by_model_condition.items()},
        "jsonl_counts": json_counts,
        "repeat_count_distribution": {str(k): v for k, v in repeat_counts.items()},
    }
