#!/usr/bin/env bash
# R7/IPMA full experiment — self-serving, resume-safe, unattended queue.
#
# Lesson from the first attempt: depending on external standing endpoints meant
# the run never fired.  This version SELF-SERVES the models it can, on whichever
# GPU is free, so "launch and walk away" actually works:
#
#   * gpt_oss_120b : used ONLY if its endpoint (:8192) is already up. Never
#     self-served here (TP=2 + auth proxy are managed externally). Skipped (with
#     resume) if down, so the run still completes for the other models.
#   * gemma4_31b   : self-served on the freest GPU (needs ~65GB free).
#   * mistral_small_3p2 : self-served on the freest GPU (needs ~50GB free).
#
# Each model: ensure endpoint -> run its R7 cells (R6 runner + R7 conditions +
# snapshot capture, --skip-existing) -> stop any model we served.
# Then integrity + metrics + neutral reference.
#
# Safety: R7_ALLOW_FULL=1 required; single-instance lock; resume-safe; conservative
# gpu-memory-utilization with headroom so we do not OOM the co-tenant; if a model
# cannot be served within its wait window it is skipped (never blocks the whole run).
#
# Launch (detached):
#   R7_ALLOW_FULL=1 setsid nohup bash scripts/r7_ipma/queue_r7_full.sh \
#     > logs/r7_full_queue_$(date -u +%Y%m%d_%H%M%S).log 2>&1 < /dev/null &

set -uo pipefail
cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2

STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_ROOT="${R7_FULL_ROOT:-results/r7_ipma/main/full_20260702_043032}"   # stable default = resume prior root
LOG_DIR="logs"
LOCK_FILE="${LOG_DIR}/r7_full_queue.lock"
TEMPLATES="data/r6/r7_ipma_conditions_r6fmt.yaml"
FULL_CFG="configs/r6/r7_ipma_full.yaml"
POLL="${R7_POLL:-120}"
PER_MODEL_MAX_WAIT="${R7_MODEL_MAX_WAIT:-$((6*3600))}"   # per-model GPU wait
CONDA_VLLM=(conda run -n p08_skilloverload)
CONDA_R6=(conda run -n agentsearch python)

mkdir -p "$LOG_DIR" "$OUT_ROOT"
log() { printf '[r7-queue] %s %s\n' "$(date -u +%FT%TZ)" "$*"; }

[ "${R7_ALLOW_FULL:-0}" = "1" ] || { log "REFUSING: set R7_ALLOW_FULL=1 to run."; exit 2; }

# --- single-instance lock ---------------------------------------------------
if [ -e "$LOCK_FILE" ]; then
  old_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    log "queue already running (PID $old_pid); exiting."; exit 0
  fi
  rm -f "$LOCK_FILE"
fi
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# endpoint_up PORT SERVED_ID : true only if the port serves the EXPECTED model id
# (a bare 200 is not enough — another user's model may hold the port).
endpoint_up() {
  curl -sf -m 8 "http://127.0.0.1:$1/v1/models" 2>/dev/null \
    | python3 -c "import sys,json;
try:
    ids=[x.get('id') for x in json.load(sys.stdin).get('data',[])]
except Exception:
    ids=[]
sys.exit(0 if '$2' in ids else 1)" 2>/dev/null
}

# freest GPU index and its free MiB -> "idx free"
freest_gpu() {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits 2>/dev/null \
    | tr -d ' ' | awk -F, '{print $2, $1}' | sort -rn | head -1 | awk '{print $2, $1}'
}

# serve $alias on freest GPU that has >= $need_mib free. Blocks up to PER_MODEL_MAX_WAIT.
# args: alias port served_id parser weights need_mib [extra vllm args...]
serve_model() {
  local alias="$1" port="$2" served="$3" parser="$4" weights="$5" need="$6"; shift 6
  local extra=("$@")
  [ -f "${weights}/config.json" ] || { log "ERROR $alias: missing ${weights}/config.json"; return 2; }
  local waited=0 gpu free
  while true; do
    read -r gpu free < <(freest_gpu)
    if [ -n "${free:-}" ] && [ "$free" -ge "$need" ]; then break; fi
    if [ "$waited" -ge "$PER_MODEL_MAX_WAIT" ]; then
      log "SKIP $alias: no GPU with >=${need}MiB free after ${PER_MODEL_MAX_WAIT}s (freest=${free:-?}MiB on gpu${gpu:-?})."
      return 3
    fi
    log "$alias: waiting for GPU (need ${need}MiB, freest ${free:-?}MiB on gpu${gpu:-?})"
    sleep "$POLL"; waited=$((waited + POLL))
  done
  # conservative utilization: use free minus 3GB headroom, capped 0.92
  local total util
  total="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits --id="$gpu" | tr -d ' ')"
  util="$(python3 -c "print(min(0.92, max(0.5, ($free-3000)/$total)))")"
  local serve_log="${LOG_DIR}/serve_${alias}_r7_${STAMP}.log"
  log "serving $alias on gpu${gpu} (free ${free}MiB, util ${util}, port ${port})"
  CUDA_VISIBLE_DEVICES="$gpu" nohup "${CONDA_VLLM[@]}" vllm serve "$weights" \
    --port "$port" --served-model-name "$served" --tensor-parallel-size 1 \
    --max-model-len 16384 --gpu-memory-utilization "$util" \
    --enable-auto-tool-choice --tool-call-parser "$parser" "${extra[@]}" \
    > "$serve_log" 2>&1 &
  echo $! > "${LOG_DIR}/serve_${alias}.pid"
  local w=0
  while ! curl -sf -m 5 "http://127.0.0.1:${port}/health" >/dev/null 2>&1; do
    sleep 10; w=$((w+10))
    if [ "$w" -ge 2400 ]; then log "ERROR $alias startup timeout"; tail -60 "$serve_log" || true; return 1; fi
  done
  log "$alias endpoint up on :${port}"
}

stop_served() { # alias
  local pf="${LOG_DIR}/$1.pid"
  [ -f "$pf" ] && kill "$(cat "$pf")" 2>/dev/null; rm -f "$pf"; sleep 3
}

run_one_model() { # alias
  local cfg="/tmp/r7_$1_${STAMP}.yaml"
  python3 - "$1" "$FULL_CFG" "$cfg" <<'PY'
import sys, yaml; from pathlib import Path
cfg = yaml.safe_load(Path(sys.argv[2]).read_text()); cfg["models"]=[sys.argv[1]]
Path(sys.argv[3]).write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
PY
  log "RUN model=$1"
  "${CONDA_R6[@]}" scripts/r6/run_r6_live.py \
    --phase full --config "$cfg" --output-root "$OUT_ROOT" \
    --templates "$TEMPLATES" --capture-snapshots \
    --live --skip-existing --allow-live-pilot-full
  local rc=$?; rm -f "$cfg"; return $rc
}

EXPECTED=$((30 * 6 * 3))   # tasks x conditions x seeds per model = 540
PASSES="${R7_MODEL_PASSES:-4}"

# serve_and_run ALIAS PORT SERVED PARSER WEIGHTS NEED_MIB [extra vllm args...]
# Runs a model to completion across up to $PASSES resume passes: (re)serves if the
# endpoint is down, runs, and repeats until all EXPECTED cells exist. Per-cell
# failures are recorded by the runner and retried on the next pass; a mid-run
# server death is healed by re-serving on the next pass.
serve_and_run() {
  local alias="$1" port="$2" served="$3" parser="$4" weights="$5" need="$6"; shift 6
  local extra=("$@") pass have
  for pass in $(seq 1 "$PASSES"); do
    have=$(ls "$OUT_ROOT"/traces/ 2>/dev/null | grep -c "^${alias}__")
    if [ "$have" -ge "$EXPECTED" ]; then log "$alias complete ($have/$EXPECTED)"; break; fi
    if ! endpoint_up "$port" "$served"; then
      serve_model "$alias" "$port" "$served" "$parser" "$weights" "$need" "${extra[@]}" \
        || { log "$alias: serve failed on pass $pass; giving up this model"; break; }
    fi
    run_one_model "$alias" || log "WARN $alias run pass $pass rc=$?"
    have=$(ls "$OUT_ROOT"/traces/ 2>/dev/null | grep -c "^${alias}__")
    log "$alias pass $pass: $have/$EXPECTED traces"
    stop_served "$alias"   # drop server between passes so a crashed one is re-served fresh
  done
}

log "START self-serving queue; out_root=$OUT_ROOT"

# Each model runs to completion (multi-pass, self-serving, self-healing).
serve_and_run gpt_oss_120b 8192 gpt-oss openai \
  /home/xqin5/hf_p08_models/gpt-oss-120b 68000
serve_and_run gemma4_31b 8005 g4 gemma4 \
  /home/xqin5/hf_p08_models/gemma-4-31B-it 66000
serve_and_run mistral_small_3p2 8007 mistral-small-3p2 mistral \
  /home/xqin5/hf_p08_models/Mistral-Small-3.2-24B-Instruct-2506 50000 \
  --limit-mm-per-prompt '{"image": 0}'

# --- post: integrity + metrics + R7 neutral reference ----------------------
log "post-run: integrity + metrics + neutral reference"
"${CONDA_R6[@]}" scripts/r6/final_integrity_audit_r6.py --root "$OUT_ROOT" \
  --report "reports/r7_ipma/R7_FULL_INTEGRITY_${STAMP}.md" || log "WARN integrity rc=$?"
"${CONDA_R6[@]}" scripts/r6/extract_r6_metrics.py --root "$OUT_ROOT" || log "WARN metrics rc=$?"
"${CONDA_R6[@]}" scripts/r7_ipma/reconstruct_tau2_field_diffs.py \
  --results_root "$OUT_ROOT" --out_dir "$OUT_ROOT/measurement_repair" \
  --report "reports/r7_ipma/R7_FULL_TAU2_FIELD_DIFF_${STAMP}.md" || log "WARN field-diff rc=$?"
"${CONDA_R6[@]}" scripts/r7_ipma/extract_usage_and_timing.py \
  --results_root "$OUT_ROOT" --out_dir "$OUT_ROOT/measurement_repair" \
  --report "reports/r7_ipma/R7_FULL_USAGE_TIMING_${STAMP}.md" || log "WARN usage rc=$?"
"${CONDA_R6[@]}" scripts/r7_ipma/build_neutral_reference_table.py \
  --metrics "$OUT_ROOT/interactional_metrics/per_run_metrics.csv" \
  --out "$OUT_ROOT/analysis/neutral_reference_table.csv" \
  --neutral_condition neutral_control || log "WARN neutral-ref rc=$?"

# count what we produced
N=$(ls "$OUT_ROOT"/traces/ 2>/dev/null | wc -l)
log "DONE $(date -u +%FT%TZ); traces=$N; out_root=$OUT_ROOT"
