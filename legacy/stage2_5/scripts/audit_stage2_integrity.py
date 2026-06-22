"""Stage-2.5 asset, tau2, evaluator, and legacy-result audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.stage2_5.integrity_checks import summarize_stage2_results


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _cmd(args: list[str]) -> str:
    try:
        return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip()
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_initial_status(report_dir: Path) -> None:
    lines = [
        "# Initial Status",
        "",
        f"- Project root: `{ROOT}`",
        f"- Is git repository: {(ROOT / '.git').exists()}",
        "",
        "## Git Status",
        "```text",
        _cmd(["git", "status", "--short"]) or "(not a git repository or clean)",
        "```",
        "",
        "## Python",
        "```text",
        _cmd([sys.executable, "-V"]),
        "```",
    ]
    (report_dir / "INITIAL_GIT_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_asset_audit(report_dir: Path, audit_dir: Path) -> None:
    paths = [
        "第二轮测试的修改方案",
        "skill.md",
        "ir_mstu_stage2/run_stage2_experiment.py",
        "ir_mstu_stage2/src/valence.py",
        "ir_mstu_stage2/data/irmstu_tasks/tau_adapted_tasks.yaml",
        "ir_mstu_stage2/data/stage2_5/social_style_templates.yaml",
        "ir_mstu_stage2/data/stage2_5/task_policy_annotations.yaml",
        "ir_mstu_stage2/configs/stage2_5/experiment.yaml",
        "ir_mstu_stage2/configs/stage2_5/models.yaml",
        "ir_mstu_stage2/configs/stage2_5/tasks.yaml",
    ]
    rows = []
    for rel in paths:
        path = ROOT.parent / rel if rel in {"第二轮测试的修改方案", "skill.md"} else ROOT / rel.replace("ir_mstu_stage2/", "")
        rows.append({
            "path": str(path),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else "",
            "sha256": _sha256(path) if path.exists() and path.is_file() else "",
        })
    with (audit_dir / "asset_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    lines = ["# Asset Audit", "", "| Path | Exists | Bytes | SHA256 |", "|---|---:|---:|---|"]
    for row in rows:
        lines.append(f"| `{row['path']}` | {row['exists']} | {row['bytes']} | `{row['sha256']}` |")
    (report_dir / "ASSET_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_code_path_map(report_dir: Path) -> None:
    lines = [
        "# Code Path Map",
        "",
        "## Legacy Stage-2",
        "- Runner: `run_stage2_experiment.py`",
        "- Social manipulation: `src/valence.py`",
        "- Output directories: `results/stage2_smoke/`, `results/stage2_mini/`",
        "- Main bias found: dynamic social injection can be scheduled after tool-call counts, so dose can depend on agent trajectory.",
        "",
        "## Stage-2.5 Repair",
        "- Runner: `scripts/run_stage2_5_experiment.py`",
        "- Templates: `data/stage2_5/social_style_templates.yaml`",
        "- Social wrapper: `src/stage2_5/social_style_wrapper.py`",
        "- Official reward helpers: `src/stage2_5/official_tau_evaluator.py`",
        "- Safe diagnostics: `src/stage2_5/safe_task_evaluator.py`",
        "- Evidence/branch diagnostics: `src/stage2_5/evidence_graph_evaluator.py`, `src/stage2_5/branch_evaluator.py`",
        "- Outputs: `results/stage2_5_repair/<phase>/`, reports under `reports/stage2_5/`.",
    ]
    (report_dir / "CODE_PATH_MAP.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tau2_audit(report_dir: Path, audit_dir: Path) -> None:
    lines = ["# tau2 Version And Evaluator Audit", ""]
    try:
        import tau2
        from tau2.run import EvaluationType, get_tasks

        lines += [
            f"- tau2 module: `{Path(tau2.__file__).resolve()}`",
            f"- tau2 version attr: `{getattr(tau2, '__version__', 'not_exposed')}`",
            f"- EvaluationType values: `{', '.join(e.name for e in EvaluationType)}`",
            "",
            "The Stage-2.5 runner uses `EvaluationType.ALL_IGNORE_BASIS` so remote NL assertion judging is not silently mixed into local runs. NL assertion tasks are flagged as only locally partially evaluable.",
            "",
        ]

        tasks_cfg = _load_yaml(ROOT / "configs/stage2_5/tasks.yaml")
        source_spec = _load_yaml(ROOT / tasks_cfg["task_source"])
        task_map = {t["task_id"]: t for t in source_spec["mini_stage2_v1"]}
        candidates = tasks_cfg["candidate_tasks"]
        rows = []
        for task_id in candidates:
            spec = task_map[task_id]
            task = get_tasks(spec["source_domain"], task_ids=[str(spec["source_task_id"])])[0]
            criteria = getattr(task, "evaluation_criteria", None)
            reward_basis = [str(x).split(".")[-1] for x in (getattr(criteria, "reward_basis", None) or [])]
            rows.append({
                "task_id": task_id,
                "domain": spec["source_domain"],
                "source_task_id": spec["source_task_id"],
                "official_reward_basis": "|".join(reward_basis),
                "has_nl_assertion": "NL_ASSERTION" in reward_basis,
                "goal": getattr(task, "goal", ""),
            })
        with (audit_dir / "official_reward_basis.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        lines += ["## Official Reward Basis", "", "| Task | Domain | tau2 ID | Reward basis | NL assertion? |", "|---|---|---:|---|---:|"]
        for row in rows:
            reward_basis_cell = row["official_reward_basis"].replace("|", ", ")
            lines.append(
                f"| {row['task_id']} | {row['domain']} | {row['source_task_id']} | "
                f"{reward_basis_cell} | {row['has_nl_assertion']} |"
            )
        (report_dir / "OFFICIAL_REWARD_BASIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as exc:
        lines += [f"- tau2 audit failed: `{type(exc).__name__}: {exc}`"]

    (report_dir / "TAU2_VERSION_AND_EVALUATOR_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_legacy_reinterpretation(report_dir: Path, audit_dir: Path) -> None:
    legacy = ROOT / "results/stage2_mini"
    summary = summarize_stage2_results(legacy)
    (audit_dir / "legacy_stage2_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    lines = [
        "# Legacy Stage-2 Reinterpretation",
        "",
        f"- Legacy results directory: `{legacy}`",
        f"- Metric rows found: {summary['n_metric_rows']}",
        f"- Duplicate run IDs: {summary['n_duplicate_run_ids']}",
        "",
        "## Status",
        "旧 Stage-2 结果只能作为 exploratory / legacy diagnostic，不应作为 confirmatory 结论。",
        "",
        "Reasons:",
        "- treatment schedule used dynamic injection tied to tool-call progress in the legacy valence layer;",
        "- neutral/treatment repetition structure was not the repaired fully paired seed design;",
        "- user simulator was not controlled beyond the injected wrapper, so later user turns may diverge after agent trajectory divergence;",
        "- safe-task success was not separated from official DB/reward success.",
    ]
    (report_dir / "LEGACY_STAGE2_REINTERPRETATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-dir", default="results/stage2_5_audit")
    ap.add_argument("--report-dir", default="reports/stage2_5")
    args = ap.parse_args()
    audit_dir = ROOT / args.audit_dir
    report_dir = ROOT / args.report_dir
    audit_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    write_initial_status(report_dir)
    write_asset_audit(report_dir, audit_dir)
    write_code_path_map(report_dir)
    write_tau2_audit(report_dir, audit_dir)
    write_legacy_reinterpretation(report_dir, audit_dir)
    print(f"audit written -> {report_dir}")


if __name__ == "__main__":
    main()
