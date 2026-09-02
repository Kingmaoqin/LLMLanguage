#!/usr/bin/env python3
"""R9 canonical paths (spec 4, 21). Single source of truth for every artifact root.

Every R9 script imports from here so that the frozen/results/report layout required by
spec 4 and spec 21 cannot drift between the production and the reference implementation.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]

DATA = ROOT / "data" / "r9_attack"
FROZEN = DATA / "frozen"
SCRIPTS = ROOT / "scripts" / "r9_attack"
CONFIGS = ROOT / "configs" / "r9_attack"
# Episode sinks live under a per-config subdir so a NEW experiment configuration never appends
# into a prior run's ResultsSink (the R9v1 cross-run contamination root cause). Set
# R9_RESULTS_SUBDIR=r9v2 for the R9v2 BFCL-deep run; default keeps the R9v1 layout.
import os as _os
RESULTS = ROOT / "results" / _os.environ.get("R9_RESULTS_SUBDIR", "r9_attack")
REPORTS = ROOT / "reports" / "r9_attack"
ARTIFACTS = ROOT / "artifacts" / "r9_attack"

CALIBRATION = RESULTS / "calibration"
DEV = RESULTS / "dev"
CONFIRMATORY = RESULTS / "confirmatory"
CONFOUNDERS = RESULTS / "confounders"
REVIEWS = RESULTS / "reviews"
INTEGRITY = RESULTS / "integrity"

# --- frozen artifacts (spec 5, 6.5, 7.2, 8.6, 13) -------------------------------
CALIBRATION_REGISTRY = FROZEN / "calibration_registry.jsonl"
DEV_REGISTRY = FROZEN / "dev_registry.jsonl"
TEST_REGISTRY = FROZEN / "test_registry.jsonl"
CONFOUNDER_REGISTRY = FROZEN / "confounder_registry.jsonl"
ENVIRONMENT_MANIFEST = FROZEN / "environment_manifest.json"
MODEL_MANIFEST = FROZEN / "model_manifest.json"
SPLIT_HASHES = FROZEN / "split_hashes.sha256"
SELECTED_MODELS = FROZEN / "selected_models.json"
FACT_LEDGERS = FROZEN / "toolsandbox_fact_ledgers.jsonl"
CANONICAL_MESSAGES = FROZEN / "canonical_messages.jsonl"
COMPRESSION_ATTACKER = FROZEN / "compression_attacker.json"
INFLATION_ATTACKER = FROZEN / "inflation_attacker.json"
ATTACKER_HASHES = FROZEN / "attacker_hashes.sha256"
PRACTICAL_THRESHOLDS = FROZEN / "practical_thresholds.json"

SAFETY_AUDIT = INTEGRITY / "local_sandbox_safety_audit.json"

ALL_DIRS = (
    DATA, FROZEN, RESULTS, REPORTS, ARTIFACTS, CONFIGS,
    CALIBRATION, DEV, CONFIRMATORY, CONFOUNDERS, REVIEWS, INTEGRITY,
)


def ensure_dirs() -> None:
    """Create every R9 output directory. Idempotent."""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)
