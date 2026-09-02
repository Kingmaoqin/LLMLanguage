#!/bin/bash
# Detached driver: measurement-complete FULL rerun (480) + full post-processing.
# Uses existing endpoints gemma@8005 (GPU2) + gpt-oss@8192 (GPU1+3). Leaves GPU0 free.
# Resumable: run_full_blocks gates and skips completed blocks; safe to re-invoke.
# Writes to a fresh root; never overwrites R4 / r4_1.
set -o pipefail
cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2
ROOT=results/stage2_5b_repair/measurement_complete_full_r5
CONDA="conda run -n agentsearch python"

echo "[driver] START $(date -u +%FT%TZ)"

$CONDA scripts/stage2_5b/run_full_blocks.py \
  --workers 2 \
  --gemma-base-urls http://127.0.0.1:8005/v1 \
  --gpt-oss-base-urls http://127.0.0.1:8192/v1 \
  --output-root "$ROOT" \
  --log-dir artifacts/stage2_5b/logs/measurement_complete_full_r5 \
  --report-dir reports/stage2_5b/run_blocks_measurement_complete_full_r5
RC=$?
echo "[driver] run_full_blocks rc=$RC $(date -u +%FT%TZ)"
if [ $RC -ne 0 ]; then echo "[driver] ABORT post-steps (runner rc=$RC)"; exit $RC; fi

echo "[driver] integrity audit"
$CONDA scripts/stage2_5b/final_integrity_audit.py --root "$ROOT" \
  --csv "$ROOT/final_integrity_report.csv" \
  --report reports/measurement_repair/MC_FULL_INTEGRITY.md

echo "[driver] reconstruct traces"
$CONDA scripts/stage2_5b/reconstruct_traces_from_existing_artifacts.py --root "$ROOT"

echo "[driver] extract interactional metrics"
$CONDA scripts/stage2_5b/extract_interactional_metrics.py --root "$ROOT"

echo "[driver] robustness profile"
$CONDA scripts/stage2_5b/analyze_interactional_robustness_profile.py --root "$ROOT" \
  --report reports/measurement_repair/INTERACTIONAL_ROBUSTNESS_PROFILE_FULL_R5.md

echo "[driver] noise floor"
$CONDA scripts/stage2_5b/estimate_noise_floor.py --root "$ROOT" \
  --report reports/measurement_repair/NOISE_FLOOR_REPORT_FULL_R5.md

echo "[driver] ALL_DONE $(date -u +%FT%TZ)"
