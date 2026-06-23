"""Deterministic offline re-scoring of frozen R4 run bundles under the v3 explicit
policy annotations.

This applies the explicit annotations (data/stage2_5b/task_policy_annotations.yaml) to the
*stored* R4 trajectories WITHOUT re-running any LLM. It recomputes only the
annotation-dependent layers — evidence, branch, policy-failure, and the policy-derived part
of safe_task_success — and reuses the annotation-independent endpoints
(official_*, local_proxy_success, invalid_run) verbatim from the stored bundle.

Outputs go to a fresh r4_1 analysis root; the stored R4 results are never modified.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.run_stage2_5b_experiment import _explicit_annotation
from src.stage2_5b.branch_evaluator import evaluate_branches
from src.stage2_5b.evaluator import evaluate_policy_failures, safe_success_metrics
from src.stage2_5b.evidence_graph import evaluate_evidence

# Annotation-dependent metric columns recomputed here.
DIAGNOSTIC_COLUMNS = [
    "required_fact_coverage",
    "missing_required_facts",
    "mutation_before_evidence",
    "first_mutation_tool",
    "first_mutation_step",
    "n_policy_failures",
    "policy_failure_types",
    "safe_task_success",
    "safe_task_success_basis",
]


def load_annotations(config_path: Path) -> dict[str, Any]:
    import yaml

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    ann_path = ROOT / cfg["paths"]["task_policy_annotations"]
    return yaml.safe_load(ann_path.read_text(encoding="utf-8"))["tasks"]


def rescore_bundle(bundle: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any]:
    events = bundle.get("normalized_tool_events") or []
    controlled = bundle.get("controlled_user_events") or []
    stored = bundle["metrics"]

    evidence = evaluate_evidence(events, annotation)
    policy_failures = evaluate_policy_failures(
        events, [], annotation, evidence, confirmation_events=controlled
    )
    invalid_run = bool(stored.get("invalid_run"))
    safe = safe_success_metrics(
        official={
            "local_proxy_success": stored.get("local_proxy_success"),
            "official_reward_basis_success": stored.get("official_reward_basis_success"),
        },
        evidence=evidence,
        policy_failures=policy_failures,
        invalid_run=invalid_run,
    )
    branches = evaluate_branches(events, annotation)

    rescored = {
        "required_fact_coverage": evidence["required_fact_coverage"],
        "missing_required_facts": evidence["missing_required_facts"],
        "mutation_before_evidence": evidence["mutation_before_evidence"],
        "first_mutation_tool": evidence["first_mutation_tool"],
        "first_mutation_step": evidence["first_mutation_step"],
        "n_policy_failures": safe["n_policy_failures"],
        "policy_failure_types": safe["policy_failure_types"],
        "safe_task_success": safe["safe_task_success"],
        "safe_task_success_basis": safe["safe_task_success_basis"],
    }
    return {"rescored": rescored, "branches": branches, "policy_failures": policy_failures}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    return str(value)


def iter_bundles(results_root: Path):
    for block in sorted(p for p in results_root.iterdir() if p.is_dir()):
        bundle_dir = block / "run_bundles"
        if not bundle_dir.is_dir():
            continue
        for path in sorted(bundle_dir.glob("*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage2_5b/experiment.yaml")
    parser.add_argument("--root", default="results/stage2_5b_repair/r4_confirmatory_canonical")
    parser.add_argument("--output", default="results/stage2_5b_rescore_of_r4")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    annotations = load_annotations(ROOT / args.config)
    results_root = ROOT / args.root
    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    rescored_rows: list[dict[str, Any]] = []
    diff_rows: list[dict[str, Any]] = []
    n = 0
    safe_changes = 0
    for bundle in iter_bundles(results_root):
        meta = bundle["run_meta"]
        spec = {"task_id": meta["task_id"], "source_task_id": str(meta["source_task_id"])}
        annotation = _explicit_annotation(spec, annotations)
        if annotation is None:
            raise SystemExit(f"no explicit annotation for {meta['task_id']} (run {meta['run_id']})")
        result = rescore_bundle(bundle, annotation)
        stored = bundle["metrics"]
        rescored = result["rescored"]

        row = {
            "run_id": meta["run_id"],
            "model_alias": meta["model_alias"],
            "task_id": meta["task_id"],
            "condition_id": meta["condition_id"],
            "seed": meta["seed"],
            # endpoints reused verbatim
            "local_proxy_success": _norm(stored.get("local_proxy_success")),
            "official_reward_basis_success": _norm(stored.get("official_reward_basis_success")),
            "invalid_run": _norm(stored.get("invalid_run")),
            **{f"v3_{k}": _norm(v) for k, v in rescored.items()},
        }
        rescored_rows.append(row)

        changed = {
            col: (_norm(stored.get(col)), _norm(rescored.get(col)))
            for col in DIAGNOSTIC_COLUMNS
            if _norm(stored.get(col)) != _norm(rescored.get(col))
        }
        if changed:
            diff_rows.append({
                "run_id": meta["run_id"],
                "changed_columns": "|".join(sorted(changed)),
                **{f"{col}__stored": old for col, (old, _new) in changed.items()},
                **{f"{col}__v3": new for col, (_old, new) in changed.items()},
            })
            if "safe_task_success" in changed:
                safe_changes += 1
        n += 1

    rescored_csv = output_dir / "rescored_run_metrics.csv"
    with rescored_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rescored_rows[0].keys()))
        writer.writeheader()
        writer.writerows(rescored_rows)

    diff_csv = output_dir / "rescore_diff_summary.csv"
    diff_fields = sorted({k for row in diff_rows for k in row}) if diff_rows else ["run_id", "changed_columns"]
    with diff_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=diff_fields)
        writer.writeheader()
        writer.writerows(diff_rows)

    status = {
        "rescored_runs": n,
        "runs_with_any_diagnostic_change": len(diff_rows),
        "runs_with_safe_task_success_change": safe_changes,
        "annotation_version": "stage2_5b_policy_annotations_v3",
        "source_root": str(args.root),
        "note": (
            "Endpoints (official_*, local_proxy_success, invalid_run) reused verbatim from "
            "stored R4 bundles; only annotation-dependent diagnostic + safe layers recomputed."
        ),
    }
    (output_dir / "rescore_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
