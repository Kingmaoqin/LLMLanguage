#!/usr/bin/env bash
# Queue R6 full resume after multiaiagent Phase-2 finishes.
#
# This intentionally does not compete with the active multiaiagent Gemma4 run
# on port 8005/GPU0. It waits until the Phase-2 resume driver and run_phase2.py
# workers are gone, then resumes R6 in the same output root with --skip-existing.

set -euo pipefail

cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

R6_ROOT="${R6_FULL_ROOT:-results/r6_sensitivity/full_main_seq_eligible_20260626}"
LOCK_FILE="${LOG_DIR}/r6_after_phase2_queue.lock"
R6_LOG="${LOG_DIR}/r6_full_resume_after_phase2_$(date -u +%Y%m%d_%H%M%S).log"

log() {
  printf '[r6-queue] %s %s\n' "$(date -u +%FT%TZ)" "$*"
}

if [ -e "$LOCK_FILE" ]; then
  old_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    log "Existing queue is already running with PID $old_pid; exiting."
    exit 0
  fi
  rm -f "$LOCK_FILE"
fi
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

phase2_running() {
  pgrep -af '/home/xqin5/multiaiagent/scripts/run_phase2.py|run_phase2_resume_missing_20260625.sh' >/dev/null 2>&1
}

r6_running() {
  pgrep -af 'run_r6_full_sequential.sh|run_r6_live.py --phase full' >/dev/null 2>&1
}

trace_count() {
  find "$R6_ROOT/traces" -name '*.trace.json' 2>/dev/null | wc -l
}

log "Queued R6 resume after Phase-2. R6 root: $R6_ROOT"
log "Current R6 trace count: $(trace_count)/2160"

while phase2_running; do
  log "Phase-2 still running; waiting 300s. R6 traces: $(trace_count)/2160"
  sleep 300
done

log "Phase-2 no longer running. Preparing to resume R6."

if r6_running; then
  log "R6 appears already running; not launching another copy."
  exit 0
fi

for url in http://127.0.0.1:8005/v1/models http://127.0.0.1:8192/v1/models; do
  if ! curl -sf "$url" >/dev/null 2>&1; then
    log "ERROR: required baseline endpoint is not healthy: $url"
    exit 1
  fi
done

log "Starting R6 resume. Output log: $R6_LOG"
R6_ALLOW_FULL=1 R6_RESUME=1 R6_FULL_ROOT="$R6_ROOT" \
  bash scripts/r6/run_r6_full_sequential.sh >> "$R6_LOG" 2>&1

log "R6 resume command exited with status $?. Final trace count: $(trace_count)/2160"
