#!/usr/bin/env bash
# R7-B/IPMA full queue — resume-safe, self-serving, strict R7-B templates.
#
# Launch:
#   R7B_ALLOW_FULL=1 setsid nohup bash scripts/r7b_ipma/queue_r7b_full.sh \
#     > logs/r7b_full_queue_$(date -u +%Y%m%d_%H%M%S).log 2>&1 < /dev/null &

set -uo pipefail
cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2

STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_ROOT="${R7B_FULL_ROOT:-results/r7b_ipma/main/full_${STAMP}}"
LOG_DIR="logs"
LOCK_FILE="${LOG_DIR}/r7b_full_queue_${STAMP}.lock"
FULL_CFG="${R7B_FULL_CFG:-configs/r7b_ipma/r7b_full.yaml}"
POLL="${R7B_POLL:-120}"
PER_MODEL_MAX_WAIT="${R7B_MODEL_MAX_WAIT:-$((6*3600))}"
PASSES="${R7B_MODEL_PASSES:-4}"
CONDA_VLLM=(conda run -n p08_skilloverload)
CONDA_R7B=(conda run -n agentsearch python)

mkdir -p "$LOG_DIR" "$OUT_ROOT"
log() { printf '[r7b-queue] %s %s\n' "$(date -u +%FT%TZ)" "$*"; }

[ "${R7B_ALLOW_FULL:-0}" = "1" ] || { log "REFUSING: set R7B_ALLOW_FULL=1 to run full."; exit 2; }

if [ -e "$LOCK_FILE" ]; then
  old_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    log "queue already running (PID $old_pid); exiting."
    exit 0
  fi
  rm -f "$LOCK_FILE"
fi
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

endpoint_up() {
  curl -sf -m 8 "http://127.0.0.1:$1/v1/models" 2>/dev/null \
    | python3 -c "import sys,json
try:
    ids=[x.get('id') for x in json.load(sys.stdin).get('data',[])]
except Exception:
    ids=[]
sys.exit(0 if '$2' in ids else 1)" 2>/dev/null
}

freest_gpu() {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits 2>/dev/null \
    | tr -d ' ' | awk -F, '{print $2, $1}' | sort -rn | head -1 | awk '{print $2, $1}'
}

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
    sleep "$POLL"
    waited=$((waited + POLL))
  done
  local total util serve_log
  total="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits --id="$gpu" | tr -d ' ')"
  util="$(python3 -c "print(min(0.92, max(0.5, ($free-3000)/$total)))")"
  serve_log="${LOG_DIR}/serve_${alias}_r7b_${STAMP}.log"
  log "serving $alias on gpu${gpu} (free ${free}MiB, util ${util}, port ${port})"
  CUDA_VISIBLE_DEVICES="$gpu" nohup "${CONDA_VLLM[@]}" vllm serve "$weights" \
    --port "$port" --served-model-name "$served" --tensor-parallel-size 1 \
    --max-model-len 16384 --gpu-memory-utilization "$util" \
    --enable-auto-tool-choice --tool-call-parser "$parser" "${extra[@]}" \
    > "$serve_log" 2>&1 &
  echo $! > "${LOG_DIR}/serve_${alias}.pid"
  local w=0
  while ! endpoint_up "$port" "$served"; do
    sleep 10
    w=$((w + 10))
    if [ "$w" -ge 2400 ]; then
      log "ERROR $alias startup timeout"
      tail -80 "$serve_log" || true
      return 1
    fi
  done
  log "$alias endpoint up on :${port}"
}

stop_served() {
  local pf="${LOG_DIR}/serve_$1.pid"
  if [ -f "$pf" ]; then
    kill "$(cat "$pf")" 2>/dev/null || true
    rm -f "$pf"
    sleep 3
  fi
}

expected_per_model() {
  python3 - <<'PY'
import csv, yaml
from pathlib import Path
cfg = yaml.safe_load(Path("configs/r7b_ipma/r7b_full.yaml").read_text())
rows = list(csv.DictReader(Path("data/r7b_ipma/r7b_task_registry.csv").open()))
split = cfg.get("task_split", "test")
rows = [r for r in rows if r.get("dev_or_test") == split and r.get("endpoint_oracle_supported") == "True"]
print(len(rows) * len(cfg["conditions"]) * len(cfg["seeds"]))
PY
}

EXPECTED="$(expected_per_model)"

run_one_model() {
  local alias="$1"
  local cfg="/tmp/r7b_${alias}_${STAMP}.yaml"
  python3 - "$alias" "$FULL_CFG" "$cfg" <<'PY'
import sys, yaml
from pathlib import Path
cfg = yaml.safe_load(Path(sys.argv[2]).read_text())
cfg["models"] = [sys.argv[1]]
Path(sys.argv[3]).write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
PY
  log "RUN model=$alias"
  "${CONDA_R7B[@]}" scripts/r7b_ipma/run_r7b_live.py \
    --phase full --config "$cfg" --output-root "$OUT_ROOT" \
    --live --skip-existing --allow-full
  local rc=$?
  rm -f "$cfg"
  return $rc
}

count_model_traces() {
  find "$OUT_ROOT/traces" -maxdepth 1 -type f -name "$1__*.trace.json" 2>/dev/null | wc -l
}

serve_and_run() {
  local alias="$1" port="$2" served="$3" parser="$4" weights="$5" need="$6"; shift 6
  local extra=("$@") pass have
  for pass in $(seq 1 "$PASSES"); do
    have="$(count_model_traces "$alias")"
    if [ "$have" -ge "$EXPECTED" ]; then
      log "$alias complete ($have/$EXPECTED)"
      break
    fi
    if ! endpoint_up "$port" "$served"; then
      serve_model "$alias" "$port" "$served" "$parser" "$weights" "$need" "${extra[@]}" \
        || { log "$alias: serve failed on pass $pass; giving up this model"; break; }
    fi
    run_one_model "$alias" || log "WARN $alias run pass $pass rc=$?"
    have="$(count_model_traces "$alias")"
    log "$alias pass $pass: $have/$EXPECTED traces"
    stop_served "$alias"
  done
}

freest_two_gpus() {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits 2>/dev/null \
    | tr -d ' ' | awk -F, '{print $2, $1}' | sort -rn | head -2 | awk '{printf "%s %s\n", $2, $1}'
}

serve_model_tp2() {
  local alias="$1" port="$2" served="$3" parser="$4" weights="$5" need_each="$6"; shift 6
  local waited=0 line1 line2 gpu1 free1 gpu2 free2
  [ -f "${weights}/config.json" ] || { log "ERROR $alias: missing ${weights}/config.json"; return 2; }
  while true; do
    line1="$(freest_two_gpus | sed -n '1p')"
    line2="$(freest_two_gpus | sed -n '2p')"
    read -r gpu1 free1 <<< "$line1"
    read -r gpu2 free2 <<< "$line2"
    if [ -n "${free1:-}" ] && [ -n "${free2:-}" ] && [ "$free1" -ge "$need_each" ] && [ "$free2" -ge "$need_each" ]; then
      break
    fi
    if [ "$waited" -ge "$PER_MODEL_MAX_WAIT" ]; then
      log "SKIP $alias TP2: no two GPUs with >=${need_each}MiB free after ${PER_MODEL_MAX_WAIT}s (top=${free1:-?}/${free2:-?} MiB)."
      return 3
    fi
    log "$alias TP2: waiting for two GPUs (need ${need_each}MiB each, top free ${free1:-?}/${free2:-?} MiB)"
    sleep "$POLL"
    waited=$((waited + POLL))
  done
  local gpu_csv="${gpu1},${gpu2}"
  local total1 total2 util serve_log
  total1="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits --id="$gpu1" | tr -d ' ')"
  total2="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits --id="$gpu2" | tr -d ' ')"
  util="$(python3 -c "print(min(0.90, max(0.5, (min($free1,$free2)-4000)/min($total1,$total2))))")"
  serve_log="${LOG_DIR}/serve_${alias}_r7b_${STAMP}.log"
  log "serving $alias TP2 on gpu${gpu_csv} (free ${free1}/${free2}MiB, util ${util}, port ${port})"
  CUDA_VISIBLE_DEVICES="$gpu_csv" nohup "${CONDA_VLLM[@]}" vllm serve "$weights" \
    --port "$port" --served-model-name "$served" --tensor-parallel-size 2 \
    --max-model-len 16384 --gpu-memory-utilization "$util" \
    --enable-auto-tool-choice --tool-call-parser "$parser" \
    > "$serve_log" 2>&1 &
  echo $! > "${LOG_DIR}/serve_${alias}.pid"
  local w=0
  while ! endpoint_up "$port" "$served"; do
    sleep 10
    w=$((w + 10))
    if [ "$w" -ge 2400 ]; then
      log "ERROR $alias TP2 startup timeout"
      tail -80 "$serve_log" || true
      return 1
    fi
  done
  log "$alias endpoint up on :${port}"
}

serve_and_run_tp2() {
  local alias="$1" port="$2" served="$3" parser="$4" weights="$5" need_each="$6"
  local pass have
  for pass in $(seq 1 "$PASSES"); do
    have="$(count_model_traces "$alias")"
    if [ "$have" -ge "$EXPECTED" ]; then
      log "$alias complete ($have/$EXPECTED)"
      break
    fi
    if ! endpoint_up "$port" "$served"; then
      serve_model_tp2 "$alias" "$port" "$served" "$parser" "$weights" "$need_each" \
        || { log "$alias: TP2 serve failed on pass $pass; giving up this model"; break; }
    fi
    run_one_model "$alias" || log "WARN $alias run pass $pass rc=$?"
    have="$(count_model_traces "$alias")"
    log "$alias pass $pass: $have/$EXPECTED traces"
    stop_served "$alias"
  done
}

postprocess() {
  log "postprocess: template audit + pairing + endpoint + PASR + stats"
  "${CONDA_R7B[@]}" scripts/r7b_ipma/filter_template_contamination.py || log "WARN template rule rc=$?"
  "${CONDA_R7B[@]}" scripts/r7b_ipma/judge_template_semantic_invariance.py || log "WARN semantic judge rc=$?"
  "${CONDA_R7B[@]}" scripts/r7b_ipma/export_human_template_audit.py || log "WARN human export rc=$?"
  "${CONDA_R7B[@]}" scripts/r7b_ipma/check_pairing_invariants.py \
    --trace_root "$OUT_ROOT" \
    --out_csv "$OUT_ROOT/integrity/pairing_invariant_report.csv" \
    --report "reports/r7b_ipma/R7B_PAIRING_INVARIANT_AUDIT_${STAMP}.md" || log "WARN pairing rc=$?"
  "${CONDA_R7B[@]}" scripts/r7b_ipma/evaluate_endpoint_from_snapshot.py \
    --trace_root "$OUT_ROOT" \
    --registry data/r7b_ipma/r7b_task_registry.csv \
    --out_csv "$OUT_ROOT/endpoint/endpoint_oracle_per_run.csv" \
    --report "reports/r7b_ipma/R7B_ENDPOINT_ORACLE_AUDIT_${STAMP}.md" || log "WARN endpoint rc=$?"
  "${CONDA_R7B[@]}" scripts/r7b_ipma/compute_pasr_metrics.py \
    --trace_root "$OUT_ROOT" \
    --registry data/r7b_ipma/r7b_task_registry.csv \
    --endpoint "$OUT_ROOT/endpoint/endpoint_oracle_per_run.csv" \
    --pairing "$OUT_ROOT/integrity/pairing_invariant_report.csv" \
    --semantic results/r7b_ipma/template_audit/llm_semantic_judgments.csv \
    --out_dir "$OUT_ROOT/metrics" \
    --report "reports/r7b_ipma/R7B_PASR_RECOMPUTE_AUDIT_${STAMP}.md" || log "WARN pasr rc=$?"
  "${CONDA_R7B[@]}" scripts/r7b_ipma/run_statistical_analysis.py \
    --pairs "$OUT_ROOT/metrics/r7b_pairs.csv" \
    --out_dir "$OUT_ROOT/analysis" \
    --report "reports/r7b_ipma/R7B_STATISTICAL_ANALYSIS_${STAMP}.md" || log "WARN stats rc=$?"
}

log "START R7-B full queue; out_root=$OUT_ROOT expected_per_model=$EXPECTED"

serve_and_run gemma4_31b 8005 g4 gemma4 \
  /home/xqin5/hf_p08_models/gemma-4-31B-it 66000
serve_and_run mistral_small_3p2 8007 mistral-small-3p2 mistral \
  /home/xqin5/hf_p08_models/Mistral-Small-3.2-24B-Instruct-2506 50000 \
  --limit-mm-per-prompt '{"image": 0}'
serve_and_run_tp2 gpt_oss_120b 8192 gpt-oss openai \
  /home/xqin5/hf_p08_models/gpt-oss-120b 62000

postprocess
N="$(find "$OUT_ROOT/traces" -maxdepth 1 -type f -name '*.trace.json' 2>/dev/null | wc -l)"
log "DONE; traces=$N; out_root=$OUT_ROOT"
