#!/usr/bin/env python3
"""Build a read-only, file-level inventory of /home/xqin5/llmlanguage.

This script never edits source assets. It excludes the package directory itself,
hashes each source file, and writes the inventory and source manifest only under
the package directory.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

SOURCE = Path("/home/xqin5/llmlanguage")
PACKAGE = SOURCE / "EACL_PROCESS_ROBUSTNESS_PAPER_PACKAGE_20260718"
INVENTORY = PACKAGE / "01_INVENTORY"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def round_name(rel: str) -> str:
    low = rel.lower()
    if "interactional_robustness_pilot" in low:
        return "pilot"
    if "r8_full_episode" in low:
        return "r8"
    if "r7d_ipma" in low or "r7d-" in low:
        return "r7d"
    if "r7c_ipma" in low:
        return "r7c"
    if "r7b_ipma" in low:
        return "r7b"
    if "r7_ipma" in low:
        return "r7_v1"
    if "r6_sensitivity" in low or "/r6/" in low:
        return "r6"
    if "measurement_repair" in low or "full_r5" in low:
        return "r5"
    if "stage2_5b" in low or "r4_1" in low or "/r4" in low:
        return "r4_stage2_5b"
    if "stage2_5" in low:
        return "stage2_5"
    if "stage2" in low:
        return "stage2"
    if "research-wiki" in low:
        return "research_wiki"
    return "project_context"


def category(path: Path, rel: str) -> str:
    low = rel.lower()
    if "/traces/" in low or path.name.endswith(".trace.json"):
        return "raw_trace"
    if path.suffix.lower() in {".py", ".r", ".sh"}:
        if any(x in low for x in ("eval", "scor", "metric", "analy", "audit")):
            return "evaluator_or_analysis_code"
        return "code"
    if path.suffix.lower() in {".yaml", ".yml", ".toml"}:
        return "configuration"
    if path.suffix.lower() == ".csv":
        return "result_or_registry_table"
    if path.suffix.lower() in {".json", ".jsonl"}:
        if any(x in low for x in ("result", "metric", "analysis", "integrity", "review")):
            return "result_json"
        return "json_asset"
    if path.suffix.lower() in {".md", ".txt"}:
        if any(x in low for x in ("report", "audit", "errata", "claim", "paper", "summary")):
            return "report_or_audit"
        return "documentation"
    if path.suffix.lower() in {".png", ".pdf", ".svg", ".jpg", ".jpeg"}:
        return "figure_or_pdf"
    if path.suffix.lower() in {".log", ".pid"}:
        return "engineering_log"
    return "other"


def evidence_status(rel: str, rnd: str, cat: str) -> tuple[str, str]:
    low = rel.lower()
    if "ir_mstu_stage2_mvep_v1/" in low:
        return "DUPLICATE_WORKTREE_OR_MVEP", "Separate worktree; mechanism/liveness assets are not population evidence."
    if "synthetic" in low or "fixture" in low or "/tests/" in low or "/.pytest_cache/" in low:
        return "MECHANISM_ONLY", "Synthetic/test asset; never population-level evidence."
    if rnd == "r7_v1":
        return "EXCLUDED_FROM_PAPER", "Old PASR/pairing/endpoint gates were later invalidated."
    if rnd == "r7b":
        return "MECHANISM_ONLY", "Primarily code/synthetic smoke; no valid full model experiment."
    if rnd == "r7d":
        return "CONTEXTUAL_AUDIT", "Construct-validity/mechanism audit; not pooled with R6/R8."
    if rnd == "r7c":
        return "CONTEXTUAL_COUNTEREVIDENCE", "Strict placebo audit; no confirmatory IPMA effect."
    if rnd == "r8":
        return "CORE_CANDIDATE", "Separate official-tau2 full-episode protocol; calibrated-null evidence."
    if rnd == "r6":
        return "CORE_CANDIDATE", "Primary social-valence candidate; evaluator/executor caveats apply."
    if rnd in {"stage2", "stage2_5"}:
        return "EXCLUDED_FROM_PAPER", "Historical contaminated/repair-stage evidence."
    if rnd in {"r4_stage2_5b", "r5"}:
        return "CONTEXTUAL_REPLICATION", "Historical replication/null context; do not pool with R6/R8."
    if cat == "engineering_log":
        return "ENGINEERING_CONTEXT", "Useful for provenance, not scientific effect evidence."
    return "CONTEXTUAL", "Project context or documentation."


def git_snapshot(repo: Path) -> dict[str, object]:
    def run(*args: str) -> str:
        cp = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            text=True,
            capture_output=True,
        )
        return cp.stdout.strip() if cp.returncode == 0 else f"ERROR: {cp.stderr.strip()}"

    status = run("status", "--short", "--untracked-files=all").splitlines()
    return {
        "path": str(repo),
        "head": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty_or_untracked": bool(status),
        "status_line_count": len(status),
        "status_lines": status,
    }


def main() -> int:
    start = datetime.now().astimezone()
    rows: list[dict[str, object]] = []
    by_round: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    total_bytes = 0

    for path in sorted(SOURCE.rglob("*")):
        if not path.is_file() or PACKAGE == path or PACKAGE in path.parents:
            continue
        try:
            st = path.stat()
            digest = sha256(path)
        except (OSError, PermissionError) as exc:
            st = path.stat()
            digest = f"ERROR:{type(exc).__name__}"
        rel = str(path.relative_to(SOURCE))
        rnd = round_name(rel)
        cat = category(path, rel)
        status, note = evidence_status(rel, rnd, cat)
        rows.append(
            {
                "source_path": str(path),
                "relative_path": rel,
                "sha256": digest,
                "size_bytes": st.st_size,
                "modified_time": datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(),
                "extension": path.suffix.lower(),
                "asset_category": cat,
                "experiment_round": rnd,
                "evidence_status": status,
                "audit_note": note,
            }
        )
        total_bytes += st.st_size
        by_round[rnd] += 1
        by_category[cat] += 1
        by_status[status] += 1

    INVENTORY.mkdir(parents=True, exist_ok=True)
    csv_path = INVENTORY / "ASSET_INVENTORY.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    package_created = datetime.fromtimestamp(PACKAGE.stat().st_mtime).astimezone().isoformat()
    repos = [
        git_snapshot(SOURCE / "ir_mstu_stage2"),
        git_snapshot(SOURCE / "ir_mstu_stage2_mvep_v1"),
    ]
    manifest = {
        "schema_version": "eacl_process_robustness_source_manifest_v1",
        "audit_started_at": start.isoformat(),
        "manifest_written_at": datetime.now().astimezone().isoformat(),
        "package_directory_created_at": package_created,
        "source_root": str(SOURCE),
        "package_root": str(PACKAGE),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "file_count": len(rows),
        "total_size_bytes": total_bytes,
        "counts_by_round": dict(sorted(by_round.items())),
        "counts_by_category": dict(sorted(by_category.items())),
        "counts_by_evidence_status": dict(sorted(by_status.items())),
        "git_repositories": repos,
        "read_only_policy": {
            "source_mutated": False,
            "new_model_or_endpoint_calls": False,
            "new_rollouts": False,
            "allowed_operations": [
                "file search",
                "sha256",
                "offline JSON/JSONL/CSV parsing",
                "deterministic recomputation",
            ],
        },
    }
    (INVENTORY / "SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    md = [
        "# llmlanguage 资产盘点",
        "",
        f"- 扫描时间：{manifest['manifest_written_at']}",
        f"- 源目录：`{SOURCE}`",
        f"- 文件数：{len(rows):,}",
        f"- 表观总大小：{total_bytes / 1024**3:.3f} GiB",
        "- 所有源文件均只读；本脚本仅在论文包内写入清单。",
        "",
        "## 按实验轮次",
        "",
        "| 轮次 | 文件数 |",
        "|---|---:|",
    ]
    md += [f"| {k} | {v:,} |" for k, v in sorted(by_round.items())]
    md += [
        "",
        "## 按证据处置",
        "",
        "| 状态 | 文件数 |",
        "|---|---:|",
    ]
    md += [f"| {k} | {v:,} |" for k, v in sorted(by_status.items())]
    md += [
        "",
        "## 解释",
        "",
        "- `CORE_CANDIDATE` 只表示值得进一步核验，不表示主张已受支持。",
        "- R6 与 R8 属不同 protocol/evaluator，不得池化。",
        "- R7-v1、R7-B synthetic smoke、MVEP mechanism/liveness 均不得作为 population evidence。",
        "- 逐文件 hash、大小、mtime、轮次和处置见 `ASSET_INVENTORY.csv`。",
        "",
    ]
    (INVENTORY / "ASSET_INVENTORY.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"files": len(rows), "bytes": total_bytes, "inventory": str(csv_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
