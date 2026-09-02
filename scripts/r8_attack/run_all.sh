#!/usr/bin/env bash
# R8-A full-pipeline orchestrator. Runs unattended after dev workers are launched.
#   dev-wait -> freeze policy -> pre-review -> test (3 workers) -> extract ->
#   integrity -> post-review -> analyze. Idempotent (skip-existing); safe to re-run.
set -u
cd /home/xqin5/llmlanguage/ir_mstu_stage2
PY=/home/xqin5/.conda/envs/agentsearch/bin/python
LOG=logs/r8_attack
MODELS=(gemma4_31b gpt_oss_120b mistral_small_3p2)
mkdir -p "$LOG"

echo "[orch $(date +%H:%M)] waiting for dev (432 episodes)..."
while :; do
  n=$(find results/r8_attack/traces/dev -name 'rep_*.json' ! -name '*.error.json' 2>/dev/null | wc -l)
  alive=$(pgrep -fc "run_batch.py --phase dev" || true)
  echo "[orch $(date +%H:%M)] dev=$n/432 workers_alive=$alive"
  [ "$n" -ge 432 ] && break
  [ "$alive" -eq 0 ] && { echo "[orch] dev workers exited at n=$n; proceeding with available"; break; }
  sleep 120
done

echo "[orch $(date +%H:%M)] freezing policy..."
$PY scripts/r8_attack/extract_attack_metrics.py --split dev --out results/r8_attack/metrics/dev_metrics.jsonl > "$LOG/extract_dev.log" 2>&1
$PY scripts/r8_attack/freeze_policy.py > "$LOG/freeze_policy.log" 2>&1
echo "[orch] frozen policy: $(grep WINNER "$LOG/freeze_policy.log" | tail -1)"

echo "[orch $(date +%H:%M)] pre-run dual review..."
$PY scripts/r8_attack/dual_review.py --phase pre --n 300 > "$LOG/pre_review.log" 2>&1 || echo "[orch] pre-review non-fatal error"

echo "[orch $(date +%H:%M)] launching test (1800 episodes)..."
for m in "${MODELS[@]}"; do
  nohup $PY scripts/r8_attack/run_batch.py --phase test --models "$m" --skip-errored > "$LOG/test_${m}.log" 2>&1 &
  echo "[orch] test worker $m pid $!"
done

while :; do
  n=$(find results/r8_attack/traces/test -name 'rep_*.json' ! -name '*.error.json' 2>/dev/null | wc -l)
  alive=$(pgrep -fc "run_batch.py --phase test" || true)
  echo "[orch $(date +%H:%M)] test=$n/1800 workers_alive=$alive"
  [ "$n" -ge 1800 ] && break
  [ "$alive" -eq 0 ] && { echo "[orch] test workers exited at n=$n; proceeding with available"; break; }
  sleep 180
done

echo "[orch $(date +%H:%M)] extract + integrity + post-review + analyze..."
$PY scripts/r8_attack/extract_attack_metrics.py --split test --out results/r8_attack/metrics/test_metrics.jsonl > "$LOG/extract_test.log" 2>&1
$PY scripts/r8_attack/check_integrity.py --split test > "$LOG/integrity_test.log" 2>&1 || echo "[orch] integrity flagged (see log)"
$PY scripts/r8_attack/check_integrity.py --split dev > "$LOG/integrity_dev.log" 2>&1 || true
$PY scripts/r8_attack/dual_review.py --phase post --n 300 > "$LOG/post_review.log" 2>&1 || echo "[orch] post-review non-fatal error"
$PY scripts/r8_attack/sandbox_safety_audit.py > "$LOG/safety_audit_postrun.log" 2>&1 || echo "[orch] SAFETY_SCOPE_NOT_CLOSED postrun"
$PY scripts/r8_attack/analyze.py > "$LOG/analyze.log" 2>&1

echo "[orch $(date +%H:%M)] DONE" | tee "$LOG/ORCH_DONE.marker"
