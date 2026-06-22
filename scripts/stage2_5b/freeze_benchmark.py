#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TAU_ROOT = Path("/home/xqin5/tau2-bench")
DOMAINS = ("retail", "airline")


def run_cmd(args: list[str], cwd: Path | None = None) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "cmd": args,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_show_bytes(tau_root: Path, ref: str, rel_path: str) -> bytes | None:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{rel_path}"],
        cwd=tau_root,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def git_ref_exists(tau_root: Path, ref: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=tau_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def collect_files(tau_root: Path) -> list[str]:
    files: set[str] = set()

    for name in ("pyproject.toml", "README.md", "uv.lock"):
        p = tau_root / name
        if p.exists():
            files.add(name)

    for domain in DOMAINS:
        data_dir = tau_root / "data" / "tau2" / "domains" / domain
        for pattern in ("tasks.json", "tasks_voice.json", "policy.md", "db.json", "split_tasks.json", "audio_difficulty.json"):
            p = data_dir / pattern
            if p.exists():
                files.add(rel(p, tau_root))
        issue_dir = data_dir / "task_issues"
        if issue_dir.exists():
            for p in sorted(issue_dir.rglob("*")):
                if p.is_file():
                    files.add(rel(p, tau_root))

        src_dir = tau_root / "src" / "tau2" / "domains" / domain
        for p in sorted(src_dir.glob("*.py")):
            files.add(rel(p, tau_root))

    for p in sorted((tau_root / "src" / "tau2" / "evaluator").glob("*.py")):
        files.add(rel(p, tau_root))

    for p in sorted((tau_root / "src" / "tau2" / "data_model").glob("*.py")):
        files.add(rel(p, tau_root))

    for p in sorted((tau_root / "src" / "tau2" / "environment").glob("*.py")):
        files.add(rel(p, tau_root))

    for p in [
        tau_root / "src" / "tau2" / "__init__.py",
        tau_root / "src" / "tau2" / "run.py",
        tau_root / "src" / "tau2" / "registry.py",
        tau_root / "src" / "tau2" / "config.py",
        tau_root / "src" / "tau2" / "utils" / "utils.py",
        tau_root / "src" / "tau2" / "utils" / "llm_utils.py",
        tau_root / "src" / "tau2" / "orchestrator" / "environment_manager.py",
        tau_root / "src" / "tau2" / "orchestrator" / "orchestrator.py",
    ]:
        if p.exists():
            files.add(rel(p, tau_root))

    user_sim_dir = tau_root / "data" / "tau2" / "user_simulator"
    if user_sim_dir.exists():
        for p in sorted(user_sim_dir.glob("simulation_guidelines*.md")):
            files.add(rel(p, tau_root))

    return sorted(files)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(obj: Any) -> str:
    return sha256_bytes(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def task_by_id(tasks: Any, task_id: str) -> dict[str, Any] | None:
    if isinstance(tasks, dict):
        values = tasks.get("tasks", tasks.get("data", []))
    else:
        values = tasks
    for task in values:
        if str(task.get("id")) == str(task_id) or str(task.get("task_id")) == str(task_id):
            return task
    return None


def load_stage2_task_map() -> dict[str, dict[str, str]]:
    path = ROOT / "data" / "stage2_5b" / "task_policy_annotations.yaml"
    default = {
        "R1_retail_modify_pending": {"domain": "retail", "source_task_id": "4"},
        "R2_retail_return_cancel_mix": {"domain": "retail", "source_task_id": "30"},
        "R3_retail_bulk_cancel_return": {"domain": "retail", "source_task_id": "55"},
        "T1_airline_cancel_multi": {"domain": "airline", "source_task_id": "7"},
        "T2_airline_class_baggage": {"domain": "airline", "source_task_id": "12"},
        "T3_airline_conditional_cancel": {"domain": "airline", "source_task_id": "44"},
    }
    if yaml is None or not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, dict[str, str]] = {}
    for task_id, spec in (data.get("tasks") or {}).items():
        out[task_id] = {
            "domain": str(spec.get("domain")),
            "source_task_id": str(spec.get("source_task_id")),
        }
    return out or default


def compare_task_to_ref(tau_root: Path, ref: str, task_label: str, domain: str, source_task_id: str) -> dict[str, Any]:
    tasks_rel = f"data/tau2/domains/{domain}/tasks.json"
    policy_rel = f"data/tau2/domains/{domain}/policy.md"
    tasks_path = tau_root / tasks_rel
    policy_path = tau_root / policy_rel
    current_tasks = load_json(tasks_path)
    current_task = task_by_id(current_tasks, source_task_id)

    ref_task = None
    ref_tasks_bytes = git_show_bytes(tau_root, ref, tasks_rel)
    if ref_tasks_bytes is not None:
        ref_task = task_by_id(json.loads(ref_tasks_bytes.decode("utf-8")), source_task_id)

    current_eval = (current_task or {}).get("evaluation_criteria")
    ref_eval = (ref_task or {}).get("evaluation_criteria") if ref_task else None
    issue_dir = tau_root / "data" / "tau2" / "domains" / domain / "task_issues"
    issue_files = sorted(p.name for p in issue_dir.glob(f"task_{source_task_id}_*.json")) if issue_dir.exists() else []

    policy_ref_bytes = git_show_bytes(tau_root, ref, policy_rel)
    current_policy_hash = sha256_file(policy_path) if policy_path.exists() else None
    ref_policy_hash = sha256_bytes(policy_ref_bytes) if policy_ref_bytes is not None else None

    return {
        "task_label": task_label,
        "domain": domain,
        "source_task_id": source_task_id,
        "tasks_file": tasks_rel,
        "policy_file": policy_rel,
        "current_task_found": current_task is not None,
        "ref_task_found": ref_task is not None,
        "current_task_hash": canonical_hash(current_task) if current_task is not None else None,
        "ref_task_hash": canonical_hash(ref_task) if ref_task is not None else None,
        "task_text_changed_vs_ref": (
            (current_task or {}).get("instruction") != (ref_task or {}).get("instruction")
            if current_task is not None and ref_task is not None
            else None
        ),
        "current_reward_basis": (current_eval or {}).get("reward_basis") if current_eval else None,
        "ref_reward_basis": (ref_eval or {}).get("reward_basis") if ref_eval else None,
        "expected_state_changed_vs_ref": (
            canonical_hash(current_eval) != canonical_hash(ref_eval)
            if current_eval is not None and ref_eval is not None
            else None
        ),
        "policy_hash": current_policy_hash,
        "ref_policy_hash": ref_policy_hash,
        "policy_changed_vs_ref": (
            current_policy_hash != ref_policy_hash
            if current_policy_hash is not None and ref_policy_hash is not None
            else None
        ),
        "known_task_issue_files": issue_files,
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_reports(
    report_dir: Path,
    artifact_dir: Path,
    manifest: dict[str, Any],
    task_audit: list[dict[str, Any]],
    evaluator_changed: bool | None,
) -> None:
    git = manifest["git"]
    version_lines = [
        "# Benchmark Version Freeze",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        "## Active tau2 Source",
        "",
        f"- tau root: `{manifest['tau_root']}`",
        f"- tau package path: `{manifest['tau_import']['file']}`",
        f"- tau package version: `{manifest['tau_import']['version']}`",
        f"- distribution version: `{manifest['tau_import']['distribution_version']}`",
        "",
        "## Git",
        "",
        f"- branch: `{git['branch']['stdout'] or 'UNKNOWN'}`",
        f"- HEAD: `{git['head']['stdout']}`",
        f"- describe: `{git['describe']['stdout']}`",
        f"- origin/main: `{git['origin_main']['stdout']}`",
        f"- status short: `{git['status_short']['stdout'] or '(clean)'}`",
        "",
        "The current tau2 working tree is frozen as-is. No benchmark upgrade or cleanup was performed.",
        "",
        "## Dirty Diff",
        "",
        "```diff",
        git["diff"]["stdout"] or "(no diff)",
        "```",
        "",
        "## Data And Code Snapshot",
        "",
        f"- snapshot directory: `{artifact_dir / 'benchmark_snapshot'}`",
        f"- SHA256 file: `{artifact_dir / 'benchmark_snapshot' / 'SHA256SUMS'}`",
        f"- files copied: {len(manifest['files'])}",
        "",
        "Included categories: retail/airline task definitions, policies, DB fixtures, split files, task issue records, domain tools/environments/data models, evaluator implementation, tau2 task/message/simulation data models, environment core, registry/run/config files, and user-simulator guidelines.",
        "",
        "## tau2 check-data",
        "",
        "The required CLI check was attempted with `conda run -n agentsearch tau2 check-data` before freezing. It failed because the CLI entrypoint resolved through `/home/xqin5/.local/bin/tau2` and then lacked `tokenizers` in that import path. This is recorded as an environment issue; direct `conda run -n agentsearch python -c 'import tau2'` succeeds.",
    ]
    (report_dir / "BENCHMARK_VERSION_FREEZE.md").write_text("\n".join(version_lines) + "\n", encoding="utf-8")

    diff_lines = [
        "# Benchmark Task Diff Audit",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        f"Comparison ref: `{manifest['comparison_ref']}`",
        "",
        "No network fetch or automatic benchmark upgrade was performed. The comparison uses the local remote-tracking ref if present.",
        "",
        f"Evaluator files changed vs ref: `{evaluator_changed}`",
        "",
        "| Task | Domain | Source ID | Task Text Changed | Reward Basis | Expected State Changed | Policy Changed | Known Issue Files |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for row in task_audit:
        diff_lines.append(
            "| {task_label} | {domain} | {source_task_id} | {task_text_changed_vs_ref} | `{reward}` | {expected_state_changed_vs_ref} | {policy_changed_vs_ref} | {issues} |".format(
                task_label=row["task_label"],
                domain=row["domain"],
                source_task_id=row["source_task_id"],
                task_text_changed_vs_ref=row["task_text_changed_vs_ref"],
                reward=",".join(row.get("current_reward_basis") or []),
                expected_state_changed_vs_ref=row["expected_state_changed_vs_ref"],
                policy_changed_vs_ref=row["policy_changed_vs_ref"],
                issues=", ".join(row["known_task_issue_files"]) or "(none)",
            )
        )
    diff_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The six legacy task labels are audited here only to establish provenance. Stage-2.5b task calibration must still scan 10-15 benchmark tasks and freeze a new confirmatory set before treatment runs.",
        ]
    )
    (report_dir / "BENCHMARK_TASK_DIFF_AUDIT.md").write_text("\n".join(diff_lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tau-root", default=str(DEFAULT_TAU_ROOT))
    ap.add_argument("--comparison-ref", default="origin/main")
    ap.add_argument("--artifact-dir", default=str(ROOT / "artifacts" / "stage2_5b"))
    ap.add_argument("--report-dir", default=str(ROOT / "reports" / "stage2_5b"))
    args = ap.parse_args()

    tau_root = Path(args.tau_root).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    report_dir = Path(args.report_dir).resolve()
    snapshot_dir = artifact_dir / "benchmark_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    comparison_ref = args.comparison_ref if git_ref_exists(tau_root, args.comparison_ref) else "HEAD"
    file_rels = collect_files(tau_root)
    file_entries: list[dict[str, Any]] = []
    sha_lines: list[str] = []

    for rel_path in file_rels:
        src = tau_root / rel_path
        dst = snapshot_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        current_hash = sha256_file(src)
        head_bytes = git_show_bytes(tau_root, "HEAD", rel_path)
        ref_bytes = git_show_bytes(tau_root, comparison_ref, rel_path)
        entry = {
            "source_path": str(src),
            "relative_path": rel_path,
            "snapshot_path": str(dst),
            "size_bytes": src.stat().st_size,
            "sha256": current_hash,
            "head_sha256": sha256_bytes(head_bytes) if head_bytes is not None else None,
            "comparison_ref_sha256": sha256_bytes(ref_bytes) if ref_bytes is not None else None,
            "dirty_vs_head": current_hash != sha256_bytes(head_bytes) if head_bytes is not None else None,
            "changed_vs_comparison_ref": current_hash != sha256_bytes(ref_bytes) if ref_bytes is not None else None,
        }
        file_entries.append(entry)
        sha_lines.append(f"{current_hash}  {rel_path}")

    (snapshot_dir / "SHA256SUMS").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")

    git_info = {
        "head": run_cmd(["git", "rev-parse", "HEAD"], cwd=tau_root),
        "branch": run_cmd(["git", "branch", "--show-current"], cwd=tau_root),
        "describe": run_cmd(["git", "describe", "--tags", "--always"], cwd=tau_root),
        "status_short": run_cmd(["git", "status", "--short"], cwd=tau_root),
        "remote_v": run_cmd(["git", "remote", "-v"], cwd=tau_root),
        "origin_main": run_cmd(["git", "rev-parse", "--verify", "origin/main"], cwd=tau_root),
        "diff": run_cmd(["git", "diff"], cwd=tau_root),
    }
    tau_import = {
        "file": None,
        "version": None,
        "distribution_version": None,
        "import_check": run_cmd(
            [
                "conda",
                "run",
                "-n",
                "agentsearch",
                "python",
                "-c",
                "import importlib.metadata as m, tau2; print(tau2.__file__); print(getattr(tau2,'__version__','NO_VERSION')); print(m.version('tau2'))",
            ],
            cwd=ROOT,
        ),
    }
    lines = tau_import["import_check"]["stdout"].splitlines()
    if len(lines) >= 3:
        tau_import["file"], tau_import["version"], tau_import["distribution_version"] = lines[-3:]

    task_map = load_stage2_task_map()
    task_audit = [
        compare_task_to_ref(tau_root, comparison_ref, label, spec["domain"], spec["source_task_id"])
        for label, spec in sorted(task_map.items())
    ]
    evaluator_entries = [e for e in file_entries if e["relative_path"].startswith("src/tau2/evaluator/")]
    evaluator_changed = any(e["changed_vs_comparison_ref"] for e in evaluator_entries) if evaluator_entries else None

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "tau_root": str(tau_root),
        "comparison_ref": comparison_ref,
        "git": git_info,
        "tau_import": tau_import,
        "domains": list(DOMAINS),
        "files": file_entries,
        "task_audit": task_audit,
        "evaluator_changed_vs_comparison_ref": evaluator_changed,
        "python": sys.version,
    }
    write_json(artifact_dir / "tau_snapshot_manifest.json", manifest)
    write_json(artifact_dir / "benchmark_task_diff_audit.json", task_audit)
    write_reports(report_dir, artifact_dir, manifest, task_audit, evaluator_changed)
    print(f"snapshot files: {len(file_entries)}")
    print(f"manifest: {artifact_dir / 'tau_snapshot_manifest.json'}")
    print(f"sha256: {snapshot_dir / 'SHA256SUMS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
