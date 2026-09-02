#!/usr/bin/env bash
# R8-B orchestrator: Part A (288) -> Part B (360) -> Part C (72) -> analysis.
# Each part runs 3 model-workers in parallel (reuse existing vLLM endpoints; no new GPU mem).
set -u
cd /home/xqin5/llmlanguage/ir_mstu_stage2
PY=/home/xqin5/.conda/envs/agentsearch/bin/python
LOG=logs/r8b_attack; mkdir -p "$LOG"
MODELS=(gemma4_31b gpt_oss_120b mistral_small_3p2)

run_part () {  # $1=part letter  $2=expected_total  $3=results_subdir_glob
  local part="$1" total="$2" sub="$3"
  echo "[orch $(date +%H:%M)] launching Part $part ($total episodes)"
  for m in "${MODELS[@]}"; do
    nohup $PY scripts/r8b_attack/run_r8b_batch.py --part "$part" --models "$m" --skip-errored \
      > "$LOG/part${part}_${m}.log" 2>&1 &
  done
  while :; do
    n=$(find results/r8b_attack/$sub -name 'rep_*.json' ! -name '*.error.json' 2>/dev/null | wc -l)
    alive=$(pgrep -fc "run_r8b_batch.py --part $part" || true)
    echo "[orch $(date +%H:%M)] Part $part = $n/$total workers=$alive"
    [ "$n" -ge "$total" ] && break
    [ "$alive" -eq 0 ] && { echo "[orch] Part $part workers exited at $n"; break; }
    sleep 120
  done
}

$PY scripts/r8_attack/sandbox_safety_audit.py > "$LOG/safety_prerun.log" 2>&1 || { echo SAFETY_SCOPE_NOT_CLOSED; exit 3; }

run_part A 288 "high_intensity"
run_part B 360 "confounder_factorials"
run_part C 72  "boundary_controls"

echo "[orch $(date +%H:%M)] analysis + integrity"
$PY scripts/r8b_attack/analyze_r8b.py > "$LOG/analyze.log" 2>&1
$PY scripts/r8_attack/sandbox_safety_audit.py > "$LOG/safety_postrun.log" 2>&1 || true
echo "[orch $(date +%H:%M)] R8B_DONE" | tee "$LOG/R8B_DONE.marker"
