#!/bin/bash
# Gated R6 live preflight launcher (round-6).
# Waits for the OTHER project's phase2 run to finish (to avoid GPU/endpoint
# contention on g4@8005 + gpt-oss@8192), then runs the 16-cell R6 LIVE preflight
# (2 models x 2 tau2 tasks x 4 conditions x 1 seed) and the offline post-checks.
#
# Honesty gates (any failure aborts before the next stage; never publishes bad data):
#   1. wait for PHASE2_FULL_DUAL_END in the phase2 master.log
#   2. endpoint preflight (inside run_r6_live)
#   3. all 16 traces must be schema-valid (run_r6_live exits non-zero otherwise)
#   4. final integrity audit must PASS
#   5. extract_r6_metrics must succeed
# Calendar/email/etc. R6 tasks are NOT run here (no live env; skipped as needs_environment).
#
# Launch:  nohup bash scripts/r6/launch_r6_preflight_after_phase2.sh > <log> 2>&1 &

set -o pipefail
cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2

CONDA="conda run -n agentsearch python"
PHASE2_LOG="/home/xqin5/multiaiagent/results/phase2_full_dual_20260624_1336/logs/master.log"
ROOT="results/r6_sensitivity/preflight_live_$(date -u +%Y%m%d_%H%M)"
REPORT_DIR="reports/r6_sensitivity"
POLL=120              # seconds between phase2 checks
MAX_WAIT=$((36*3600)) # give up waiting after 36h

echo "[r6-launch] START $(date -u +%FT%TZ)  root=$ROOT"

# --- gate 1: wait for phase2 to finish -------------------------------------
waited=0
while true; do
  if [ -f "$PHASE2_LOG" ] && grep -q "PHASE2_FULL_DUAL_END" "$PHASE2_LOG"; then
    echo "[r6-launch] phase2 END detected at $(date -u +%FT%TZ)"
    break
  fi
  if ! pgrep -af "run_phase2.py" | grep -q "venv"; then
    # phase2 processes gone but no END marker: treat as finished/stopped, proceed cautiously
    if [ -f "$PHASE2_LOG" ]; then
      echo "[r6-launch] phase2 processes gone (no END marker) at $(date -u +%FT%TZ); proceeding"
      break
    fi
  fi
  waited=$((waited+POLL))
  if [ "$waited" -ge "$MAX_WAIT" ]; then
    echo "[r6-launch] ABORT: waited ${waited}s for phase2, giving up"; exit 3
  fi
  sleep "$POLL"
done

# brief settle so vLLM servers are idle
sleep 30

# --- gate 2+3: live preflight (endpoint check + 16 schema-valid traces) -----
echo "[r6-launch] running R6 LIVE preflight -> $ROOT"
$CONDA scripts/r6/run_r6_live.py \
  --phase preflight --config configs/r6/r6_preflight.yaml --live \
  --output-root "$ROOT"
RC=$?
echo "[r6-launch] run_r6_live rc=$RC $(date -u +%FT%TZ)"
if [ $RC -ne 0 ]; then
  echo "[r6-launch] ABORT post-checks: live preflight failed or produced invalid traces (rc=$RC)"
  exit $RC
fi

# --- gate 4: integrity audit -----------------------------------------------
echo "[r6-launch] integrity audit"
$CONDA scripts/r6/final_integrity_audit_r6.py \
  --root "$ROOT" \
  --report "$REPORT_DIR/R6_PREFLIGHT_LIVE_INTEGRITY.md"
RC=$?
if [ $RC -ne 0 ]; then echo "[r6-launch] ABORT: integrity audit failed (rc=$RC)"; exit $RC; fi

# --- gate 5: metric extraction ---------------------------------------------
echo "[r6-launch] extract R6 metrics"
$CONDA scripts/r6/extract_r6_metrics.py --root "$ROOT"
RC=$?
if [ $RC -ne 0 ]; then echo "[r6-launch] ABORT: metric extraction failed (rc=$RC)"; exit $RC; fi

echo "[r6-launch] R6_PREFLIGHT_LIVE_DONE root=$ROOT $(date -u +%FT%TZ)"
echo "[r6-launch] NEXT: review preflight integrity + metrics, then decide pilot/full."
