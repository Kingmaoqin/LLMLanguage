"""Run and gate Stage-2.5b full experiment blocks one model/task at a time."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/stage2_5b/run_stage2_5b_experiment.py"
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.run_stage2_5b_experiment import HASH_FIELDS, runtime_hashes_for_config
from src.stage2_5b.canonical_paths import R4_RESULTS_ROOT

EXPECTED_CONDITIONS = {
    "neutral_single",
    "praise_affect_single",
    "praise_trust_single",
    "insult_single",
    "neutral_repeated",
    "abuse_repeated",
}
EXPECTED_SEEDS = {"300", "301", "302", "303", "304"}
CONFIG_PATH = ROOT / "configs/stage2_5b/experiment.yaml"
EXPECTED_HASHES = runtime_hashes_for_config(CONFIG_PATH)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return rows


def bool_value(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def is_opening_event(row: dict[str, Any]) -> bool:
    """Identify the first controlled-user event across old and current schemas."""
    event_idx = row.get("user_event_idx")
    if event_idx not in (None, ""):
        try:
            return int(event_idx) == 0
        except (TypeError, ValueError):
            return False
    return row.get("user_state") == "turn_0"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def ensure_json_contract(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise SystemExit(f"contract mismatch; use a new output root: {path}")
        return
    atomic_write_json(path, payload)


@dataclass
class BlockAudit:
    passed: bool
    errors: list[str]
    stats: dict[str, Any]


def audit_block(
    output_dir: Path,
    model_alias: str,
    task_id: str,
    deployment_id: str | None = None,
) -> BlockAudit:
    errors: list[str] = []
    manifest = read_csv(output_dir / "run_manifest.csv")
    metrics = read_csv(output_dir / "run_metrics.csv")
    manifest_ids = {row.get("run_id", "") for row in manifest}
    manifest_id_list = [row.get("run_id", "") for row in manifest]
    metric_ids = [row.get("run_id", "") for row in metrics]
    metric_id_set = set(metric_ids)

    if len(manifest) != 30:
        errors.append(f"manifest rows {len(manifest)} != 30")
    if len(manifest_id_list) != len(manifest_ids):
        errors.append(f"duplicate manifest IDs: {len(manifest_id_list) - len(manifest_ids)}")
    if len(metrics) != 30:
        errors.append(f"metric rows {len(metrics)} != 30")
    if len(metric_ids) != len(metric_id_set):
        errors.append(f"duplicate metric IDs: {len(metric_ids) - len(metric_id_set)}")
    if manifest_ids != metric_id_set:
        errors.append(
            f"manifest/metric ID mismatch: missing={len(manifest_ids - metric_id_set)} "
            f"orphan={len(metric_id_set - manifest_ids)}"
        )

    if {row.get("model_alias", "") for row in metrics} not in ({model_alias}, set()):
        errors.append("mixed or wrong model aliases")
    if {row.get("task_id", "") for row in metrics} not in ({task_id}, set()):
        errors.append("mixed or wrong task IDs")
    if deployment_id is not None:
        deployment_ids = {row.get("deployment_id", "") for row in metrics}
        if deployment_ids not in ({deployment_id}, set()):
            errors.append(f"deployment ID mismatch: {sorted(deployment_ids)}")

    condition_counts = Counter(row.get("condition_id", "") for row in metrics)
    seed_counts = Counter(row.get("seed", "") for row in metrics)
    cell_counts = Counter((row.get("condition_id", ""), row.get("seed", "")) for row in metrics)
    if set(condition_counts) != EXPECTED_CONDITIONS or any(count != 5 for count in condition_counts.values()):
        errors.append(f"condition imbalance: {dict(condition_counts)}")
    if set(seed_counts) != EXPECTED_SEEDS or any(count != 6 for count in seed_counts.values()):
        errors.append(f"seed imbalance: {dict(seed_counts)}")
    if any(count != 1 for count in cell_counts.values()) or len(cell_counts) != 30:
        errors.append("condition/seed cells are not one-to-one")

    for key, expected in EXPECTED_HASHES.items():
        values = {row.get(key, "") for row in metrics}
        if values not in ({expected}, set()):
            errors.append(f"{key} mismatch: {sorted(values)}")

    metadata_fields = [
        "model_alias", "task_id", "condition_id", "seed", "template_block",
        "template_id", "temperature", "controlled_user_policy", "deployment_id",
        "deployment_base_url", *HASH_FIELDS,
    ]
    manifest_by_id = {row.get("run_id", ""): row for row in manifest}
    metadata_mismatches = 0
    for row in metrics:
        manifest_row = manifest_by_id.get(row.get("run_id", ""))
        if manifest_row is None:
            continue
        if any(str(row.get(key, "")) != str(manifest_row.get(key, "")) for key in metadata_fields):
            metadata_mismatches += 1
    if metadata_mismatches:
        errors.append(f"manifest/metric metadata mismatches: {metadata_mismatches}")

    contract_path = output_dir / "run_contract.json"
    if not contract_path.exists():
        errors.append("missing run_contract.json")
    else:
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            if contract.get("runtime_hashes") != EXPECTED_HASHES:
                errors.append("run contract runtime hashes do not match current runtime")
            if contract.get("manifest_run_ids") != manifest_id_list:
                errors.append("run contract manifest IDs do not match run_manifest.csv")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid run contract: {exc}")

    bundle_dir = output_dir / "run_bundles"
    bundle_paths = sorted(bundle_dir.glob("*.json")) if bundle_dir.exists() else []
    bundle_ids: list[str] = []
    for path in bundle_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            bundle_ids.append(str((payload.get("run_meta") or {}).get("run_id", "")))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid run bundle {path.name}: {exc}")
    if len(bundle_paths) != 30:
        errors.append(f"run bundle files {len(bundle_paths)} != 30")
    if len(bundle_ids) != len(set(bundle_ids)):
        errors.append(f"duplicate run bundle IDs: {len(bundle_ids) - len(set(bundle_ids))}")
    if set(bundle_ids) != metric_id_set:
        errors.append(
            f"bundle/metric ID mismatch: missing={len(metric_id_set - set(bundle_ids))} "
            f"orphan={len(set(bundle_ids) - metric_id_set)}"
        )

    invalid_ids = {row["run_id"] for row in metrics if bool_value(row.get("invalid_run"))}
    valid_ids = metric_id_set - invalid_ids
    valid_rate = len(valid_ids) / len(metrics) if metrics else 0.0
    if metrics and valid_rate < 0.95:
        errors.append(f"valid run rate {valid_rate:.3f} < 0.95")

    terminal_sets = {
        "final_environment_states": {row.get("run_id", "") for row in read_jsonl(output_dir / "final_environment_states.jsonl")},
        "parser_health": {row.get("run_id", "") for row in read_jsonl(output_dir / "parser_health.jsonl")},
        "termination_reasons": {row.get("run_id", "") for row in read_jsonl(output_dir / "termination_reasons.jsonl")},
    }
    for name in ("final_environment_states", "parser_health"):
        if terminal_sets[name] != valid_ids:
            errors.append(
                f"{name} IDs mismatch valid runs: missing={len(valid_ids - terminal_sets[name])} "
                f"orphan={len(terminal_sets[name] - valid_ids)}"
            )
    if terminal_sets["termination_reasons"] != metric_id_set:
        errors.append("termination reason IDs do not match metric IDs")

    parser_rows = read_jsonl(output_dir / "parser_health.jsonl")
    undefined_tools = sum(int(row.get("n_undefined_tools") or 0) for row in parser_rows)
    if undefined_tools:
        errors.append(f"undefined tools: {undefined_tools}")

    event_files = [
        "conversation_logs",
        "normalized_tool_events",
        "controlled_user_events",
        "style_wrapper_events",
        "state_deltas",
        "invalid_tool_calls",
        "evidence_events",
        "branch_decisions",
        "policy_failures",
        "termination_reasons",
        "parser_health",
        "final_environment_states",
        "adapter_errors",
    ]
    orphan_events = 0
    for name in event_files:
        for row in read_jsonl(output_dir / f"{name}.jsonl"):
            if row.get("run_id", "") not in manifest_ids:
                orphan_events += 1
    if orphan_events:
        errors.append(f"orphan events: {orphan_events}")

    controlled_rows = read_jsonl(output_dir / "controlled_user_events.jsonl")
    content_mismatches = sum(not bool_value(row.get("conversation_content_match", True)) for row in controlled_rows)
    if content_mismatches:
        errors.append(f"controlled-user conversation mismatches: {content_mismatches}")

    opening_hashes: dict[str, set[str]] = defaultdict(set)
    opening_conditions: dict[str, set[str]] = defaultdict(set)
    for row in controlled_rows:
        if row.get("run_id", "") not in valid_ids:
            continue
        if is_opening_event(row):
            seed = str(row.get("seed", ""))
            opening_hashes[seed].add(str(row.get("clean_text_hash", "")))
            opening_conditions[seed].add(str(row.get("condition_id", "")))
    valid_conditions_by_seed: dict[str, set[str]] = defaultdict(set)
    for row in metrics:
        if row.get("run_id", "") in valid_ids:
            valid_conditions_by_seed[str(row.get("seed", ""))].add(str(row.get("condition_id", "")))
    for seed in EXPECTED_SEEDS:
        expected_conditions = valid_conditions_by_seed.get(seed, set())
        if expected_conditions and len(opening_hashes.get(seed, set())) != 1:
            errors.append(f"opening clean-text drift at seed {seed}: {sorted(opening_hashes.get(seed, set()))}")
        if opening_conditions.get(seed, set()) != expected_conditions:
            errors.append(f"opening condition coverage mismatch at seed {seed}")

    initial_hashes: dict[str, set[str]] = defaultdict(set)
    for row in metrics:
        if row.get("run_id", "") in valid_ids:
            initial_hashes[row.get("seed", "")].add(row.get("state_before_hash", ""))
    for seed in EXPECTED_SEEDS:
        if valid_conditions_by_seed.get(seed) and len(initial_hashes.get(seed, set())) != 1:
            errors.append(f"initial-state mismatch at seed {seed}: {sorted(initial_hashes.get(seed, set()))}")

    stats = {
        "manifest_rows": len(manifest),
        "metric_rows": len(metrics),
        "valid_runs": len(valid_ids),
        "invalid_runs": len(invalid_ids),
        "valid_rate": round(valid_rate, 4),
        "adapter_errors": len(read_jsonl(output_dir / "adapter_errors.jsonl")),
        "undefined_tools": undefined_tools,
        "orphan_events": orphan_events,
        "max_steps": sum("MAX_STEPS" in str(row.get("termination_reason")) for row in metrics),
        "safe_successes": sum(bool_value(row.get("safe_task_success")) for row in metrics),
        "run_bundles": len(bundle_paths),
    }
    return BlockAudit(passed=not errors, errors=errors, stats=stats)


def write_report(path: Path, model_alias: str, task_id: str, audit: BlockAudit, command: list[str]) -> None:
    lines = [
        f"# Block {model_alias} / {task_id}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Status: {'PASS' if audit.passed else 'FAIL'}",
        "",
        "Command:",
        "```text",
        " ".join(command),
        "```",
        "",
        "Stats:",
        *[f"- {key}: {value}" for key, value in audit.stats.items()],
        "",
        "Errors:",
        *([f"- {error}" for error in audit.errors] if audit.errors else ["- none"]),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def frozen_tasks() -> list[str]:
    path = ROOT / "data/stage2_5b/calibrated_tasks_frozen.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        entry["task_id"] if isinstance(entry, dict) else entry
        for entry in payload["confirmatory_tasks"]
    ]


def endpoint_ok(base_url: str, expected_served_id: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/models", timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        model_ids = [row.get("id") for row in payload.get("data", [])]
        if expected_served_id not in model_ids:
            return False, f"expected served ID {expected_served_id!r}, ids={model_ids}"
        return True, f"ids={model_ids}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


@dataclass(frozen=True)
class BlockJob:
    model_alias: str
    task_id: str
    base_url: str
    deployment_id: str
    served_id: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["gemma4_31b", "gpt_oss_120b"])
    parser.add_argument("--tasks", nargs="+", default=None)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--gemma-base-urls",
        nargs="+",
        default=["http://127.0.0.1:8005/v1"],
    )
    parser.add_argument(
        "--gpt-oss-base-urls",
        nargs="+",
        default=["http://127.0.0.1:8192/v1"],
    )
    parser.add_argument("--output-root", default=R4_RESULTS_ROOT)
    parser.add_argument("--log-dir", default="artifacts/stage2_5b/logs/r4_confirmatory_canonical")
    parser.add_argument("--report-dir", default="reports/stage2_5b/run_blocks_r4")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    tasks = args.tasks or frozen_tasks()
    output_root = ROOT / args.output_root
    log_dir = ROOT / args.log_dir
    report_dir = ROOT / args.report_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    endpoint_pools = {
        "gemma4_31b": args.gemma_base_urls,
        "gpt_oss_120b": args.gpt_oss_base_urls,
    }
    served_ids = {
        "gemma4_31b": "g4",
        "gpt_oss_120b": "gpt-oss",
    }
    for model_alias in args.models:
        if model_alias not in endpoint_pools:
            raise SystemExit(f"missing endpoint pool for model {model_alias}")
    if not args.dry_run:
        failures = []
        endpoint_checks = sorted({
            (url, served_ids[model_alias])
            for model_alias in args.models
            for url in endpoint_pools[model_alias]
        })
        for url, served_id in endpoint_checks:
            ok, detail = endpoint_ok(url, served_id)
            print(f"PREFLIGHT {url} {'PASS' if ok else 'FAIL'} {detail}", flush=True)
            if not ok:
                failures.append(url)
        if failures:
            raise SystemExit(f"endpoint preflight failed: {failures}")

    jobs: list[BlockJob] = []
    counters: dict[str, int] = defaultdict(int)
    for task_id in tasks:
        for model_alias in args.models:
            urls = endpoint_pools[model_alias]
            base_url = urls[counters[model_alias] % len(urls)]
            counters[model_alias] += 1
            port = base_url.rstrip("/").split(":")[-1].split("/")[0]
            jobs.append(
                BlockJob(
                    model_alias=model_alias,
                    task_id=task_id,
                    base_url=base_url,
                    deployment_id=f"{model_alias}_port{port}",
                    served_id=served_ids[model_alias],
                )
            )

    full_contract = {
        "schema_version": 1,
        "runtime_hashes": EXPECTED_HASHES,
        "models": list(args.models),
        "tasks": list(tasks),
        "conditions": sorted(EXPECTED_CONDITIONS),
        "seeds": sorted(EXPECTED_SEEDS),
        "expected_runs": len(jobs) * 30,
        "jobs": [
            {
                "model_alias": job.model_alias,
                "task_id": job.task_id,
                "base_url": job.base_url,
                "deployment_id": job.deployment_id,
                "served_id": job.served_id,
            }
            for job in jobs
        ],
    }
    ensure_json_contract(output_root / "FULL_RUN_CONTRACT.json", full_contract)

    def run_job(job: BlockJob) -> tuple[BlockJob, BlockAudit]:
        model_alias = job.model_alias
        task_id = job.task_id
        output_dir = output_root / f"{model_alias}__{task_id}"
        log_path = log_dir / f"{model_alias}__{task_id}.log"
        report_path = report_dir / f"BLOCK_{model_alias}_{task_id}.md"
        command = [
            sys.executable,
            str(RUNNER),
            "--phase",
            "full",
            "--models",
            model_alias,
            "--tasks",
            task_id,
            "--base-url-override",
            job.base_url,
            "--deployment-id",
            job.deployment_id,
            "--skip-endpoint-check",
            "--output-dir",
            str(output_dir),
        ]
        prior = audit_block(output_dir, model_alias, task_id, job.deployment_id)
        if prior.passed:
            write_report(report_path, model_alias, task_id, prior, command)
            print(f"SKIP PASS {model_alias} {task_id} {job.deployment_id}", flush=True)
            return job, prior

        print(f"START {model_alias} {task_id} {job.deployment_id}", flush=True)
        with log_path.open("a", encoding="utf-8") as log:
            completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        audit = audit_block(output_dir, model_alias, task_id, job.deployment_id)
        if completed.returncode:
            audit.errors.append(f"runner exit code: {completed.returncode}")
            audit.passed = False
        write_report(report_path, model_alias, task_id, audit, command)
        print(
            f"END {model_alias} {task_id} {job.deployment_id} "
            f"status={'PASS' if audit.passed else 'FAIL'}",
            flush=True,
        )
        return job, audit

    if args.dry_run:
        for job in jobs:
            command = [
                sys.executable,
                str(RUNNER),
                "--phase",
                "full",
                "--models",
                job.model_alias,
                "--tasks",
                job.task_id,
                "--base-url-override",
                job.base_url,
                "--deployment-id",
                job.deployment_id,
                "--skip-endpoint-check",
                "--output-dir",
                str(output_root / f"{job.model_alias}__{job.task_id}"),
            ]
            print(" ".join(command))
        return 0

    block_results: list[tuple[str, str, BlockAudit]] = []
    failed = False
    job_iter = iter(jobs)
    futures: dict[Future[tuple[BlockJob, BlockAudit]], BlockJob] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for _ in range(min(args.workers, len(jobs))):
            job = next(job_iter, None)
            if job is not None:
                futures[executor.submit(run_job, job)] = job

        while futures:
            done, _pending = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                job = futures.pop(future)
                try:
                    completed_job, audit = future.result()
                except Exception as exc:
                    audit = BlockAudit(False, [f"block worker exception: {type(exc).__name__}: {exc}"], {})
                    completed_job = job
                block_results.append((completed_job.model_alias, completed_job.task_id, audit))
                if not audit.passed:
                    failed = True
                if not failed:
                    next_job = next(job_iter, None)
                    if next_job is not None:
                        futures[executor.submit(run_job, next_job)] = next_job

    lines = ["# Full Block Index", ""]
    for model_alias, task_id, audit in block_results:
        lines.append(f"- {model_alias} / {task_id}: {'PASS' if audit.passed else 'FAIL'}")
    if failed:
        lines.append("- Scheduling stopped after the first failed completion; already-running sibling blocks were allowed to finish and were audited.")
    (report_dir / "BLOCK_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
