"""Assemble flat atomic Stage-2.5b roots into the canonical block layout.

The experiment runner can execute a full model panel into one flat atomic root,
while the G11 audit and analysis consume one directory per model/task block.
This script partitions existing immutable bundles without rerunning models.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.run_stage2_5b_experiment import (
    _materialize_bundles,
    _write_manifest,
    runtime_hashes_for_config,
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def link_or_copy(source: Path, target: Path) -> None:
    if target.exists():
        if target.stat().st_ino == source.stat().st_ino:
            return
        if target.read_bytes() == source.read_bytes():
            return
        raise SystemExit(f"refusing to replace different bundle: {target}")
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def validate_sources(
    source_roots: list[Path],
    current_hashes: dict[str, str],
) -> tuple[list[dict[str, str]], dict[str, Path]]:
    rows: list[dict[str, str]] = []
    bundle_by_run: dict[str, Path] = {}
    for source_root in source_roots:
        contract = json.loads(
            (source_root / "run_contract.json").read_text(encoding="utf-8")
        )
        if contract.get("runtime_hashes") != current_hashes:
            raise SystemExit(f"runtime hash mismatch: {source_root}")
        manifest = read_csv(source_root / "run_manifest.csv")
        metrics = read_csv(source_root / "run_metrics.csv")
        manifest_ids = [row["run_id"] for row in manifest]
        metric_ids = [row["run_id"] for row in metrics]
        if len(manifest_ids) != len(set(manifest_ids)):
            raise SystemExit(f"duplicate manifest IDs: {source_root}")
        if set(manifest_ids) != set(metric_ids):
            raise SystemExit(f"manifest/metric mismatch: {source_root}")
        if contract.get("manifest_run_ids") != manifest_ids:
            raise SystemExit(f"contract/manifest order mismatch: {source_root}")
        for row in manifest:
            for field, expected in current_hashes.items():
                if row.get(field, "") != expected:
                    raise SystemExit(f"{source_root}: {row['run_id']} {field} mismatch")
            if row["run_id"] in bundle_by_run:
                raise SystemExit(f"duplicate run across roots: {row['run_id']}")
            bundle = (
                source_root
                / "run_bundles"
                / (
                    "".join(
                        c if c.isalnum() or c == "_" else "_" for c in row["run_id"]
                    )
                    + ".json"
                )
            )
            if not bundle.exists():
                raise SystemExit(f"missing bundle: {bundle}")
            bundle_by_run[row["run_id"]] = bundle
        rows.extend(manifest)
    return rows, bundle_by_run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help="Flat atomic result roots containing run_contract.json and run_bundles/.",
    )
    parser.add_argument(
        "--output-root",
        default="results/stage2_5b_repair/r4_confirmatory_canonical",
    )
    parser.add_argument(
        "--config",
        default="configs/stage2_5b/experiment.yaml",
    )
    args = parser.parse_args()

    source_roots = [ROOT / source for source in args.sources]
    output_root = ROOT / args.output_root
    config_path = ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    experiment = config["experiment"]
    current_hashes = runtime_hashes_for_config(config_path)
    manifest_rows, bundle_by_run = validate_sources(source_roots, current_hashes)
    manifest_order = {row["run_id"]: index for index, row in enumerate(manifest_rows)}

    expected_conditions = {
        "neutral_single",
        "praise_affect_single",
        "praise_trust_single",
        "insult_single",
        "neutral_repeated",
        "abuse_repeated",
    }
    expected_seeds = {"300", "301", "302", "303", "304"}
    if len(manifest_rows) != 480:
        raise SystemExit(f"expected 480 manifest rows, found {len(manifest_rows)}")
    model_counts = Counter(row["model_alias"] for row in manifest_rows)
    if set(model_counts.values()) != {240} or len(model_counts) != 2:
        raise SystemExit("model balance is not 240/240")
    if set(row["condition_id"] for row in manifest_rows) != expected_conditions:
        raise SystemExit("condition set mismatch")
    if set(row["seed"] for row in manifest_rows) != expected_seeds:
        raise SystemExit("seed set mismatch")

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in manifest_rows:
        grouped[(row["model_alias"], row["task_id"])].append(row)
    if len(grouped) != 16 or any(len(rows) != 30 for rows in grouped.values()):
        raise SystemExit("expected 16 balanced model/task blocks of 30 runs")

    jobs = []
    for (model_alias, task_id), block_rows in sorted(grouped.items()):
        block_rows.sort(key=lambda row: manifest_order[row["run_id"]])
        block = output_root / f"{model_alias}__{task_id}"
        bundle_dir = block / "run_bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        _write_manifest(block / "run_manifest.csv", block_rows)
        for row in block_rows:
            source = bundle_by_run[row["run_id"]]
            link_or_copy(source, bundle_dir / source.name)
        _materialize_bundles(block, block_rows, bundle_dir)

        deployment_ids = sorted({row["deployment_id"] for row in block_rows})
        deployment_urls = sorted({row["deployment_base_url"] for row in block_rows})
        block_contract = {
            "schema_version": 1,
            "phase": "full",
            "model_aliases": [model_alias],
            "task_ids": [task_id],
            "condition_ids": sorted(expected_conditions),
            "seeds": sorted(int(seed) for seed in expected_seeds),
            "temperature": float(block_rows[0]["temperature"]),
            "max_steps": int(experiment["max_steps"]),
            "max_errors": int(experiment["max_errors"]),
            "runtime_hashes": current_hashes,
            "manifest_run_ids": [row["run_id"] for row in block_rows],
            "deployment_ids": deployment_ids,
            "deployment_base_urls": deployment_urls,
        }
        atomic_write_json(block / "run_contract.json", block_contract)
        jobs.append(
            {
                "model_alias": model_alias,
                "task_id": task_id,
                "base_url": deployment_urls[0],
                "deployment_id": deployment_ids[0],
                "served_id": "g4" if model_alias == "gemma4_31b" else "gpt-oss",
            }
        )

    full_contract = {
        "schema_version": 1,
        "runtime_hashes": current_hashes,
        "models": sorted({row["model_alias"] for row in manifest_rows}),
        "tasks": sorted({row["task_id"] for row in manifest_rows}),
        "conditions": sorted(expected_conditions),
        "seeds": sorted(expected_seeds),
        "expected_runs": len(manifest_rows),
        "jobs": jobs,
        "assembled_from": [
            str(source_root.relative_to(ROOT)) for source_root in source_roots
        ],
    }
    atomic_write_json(output_root / "FULL_RUN_CONTRACT.json", full_contract)
    print(
        f"assembled runs={len(manifest_rows)} blocks={len(grouped)} "
        f"output={output_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
