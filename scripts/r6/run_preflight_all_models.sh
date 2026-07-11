#!/usr/bin/env bash
# Sequential GPU-3 preflight for R6 candidate models.
#
# Safety contract:
# - Never writes into R4/R5 roots.
# - Never reuses a prior preflight root by default.
# - Writes one independent result root per model, so each root has a clean
#   live_run_plan/live_run_summary/traces/metrics/integrity set.
#
# Usage:
#   bash scripts/r6/run_preflight_all_models.sh [MODEL_ALIAS ...]
#
# Optional:
#   R6_PREFLIGHT_ROOT=results/r6_sensitivity/model_preflight_new_YYYYMMDD_HHMMSS \
#     bash scripts/r6/run_preflight_all_models.sh mistral_small_3p2

set -euo pipefail

cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2

CONDA_VLLM=(conda run -n p08_skilloverload)
CONDA_R6=(conda run -n agentsearch python)
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_BASE="${R6_PREFLIGHT_ROOT:-results/r6_sensitivity/model_preflight_new_${STAMP}}"
LOG_DIR="logs"
GPU3_PORT=8007

declare -A MODEL_PATH=(
  [mistral_small_3p2]="/home/xqin5/hf_p08_models/Mistral-Small-3.2-24B-Instruct-2506"
  [gemma3_27b]="/home/xqin5/hf_p08_models/gemma-3-27b-it"
  [olmo2_32b]="/home/xqin5/hf_p08_models/OLMo-2-0325-32B-Instruct"
  [phi4_reasoning]="/home/xqin5/hf_p08_models/Phi-4-reasoning-plus"
)

declare -A MODEL_SERVED_ID=(
  [mistral_small_3p2]="mistral-small-3p2"
  [gemma3_27b]="gemma3-27b"
  [olmo2_32b]="olmo2-32b"
  [phi4_reasoning]="phi4-reasoning"
)

ALL_NEW_MODELS=(mistral_small_3p2 gemma3_27b olmo2_32b phi4_reasoning)

if [ "$#" -gt 0 ]; then
  MODELS_TO_RUN=("$@")
else
  MODELS_TO_RUN=("${ALL_NEW_MODELS[@]}")
fi

log() { echo "[r6-preflight] $*"; }

model_args() {
  case "$1" in
    mistral_small_3p2)
      # HF-format Mistral 3 checkpoint. Do not use --load_format mistral here.
      printf '%s\n' \
        "--max-model-len" "16384" \
        "--gpu-memory-utilization" "0.90" \
        "--enable-auto-tool-choice" \
        "--tool-call-parser" "mistral" \
        "--limit-mm-per-prompt" '{"image":0}'
      ;;
    gemma3_27b)
      printf '%s\n' \
        "--max-model-len" "32768" \
        "--gpu-memory-utilization" "0.90" \
        "--enable-auto-tool-choice" \
        "--tool-call-parser" "pythonic"
      ;;
    olmo2_32b)
      printf '%s\n' \
        "--max-model-len" "4096" \
        "--gpu-memory-utilization" "0.92" \
        "--enable-auto-tool-choice" \
        "--tool-call-parser" "pythonic"
      ;;
    phi4_reasoning)
      printf '%s\n' \
        "--max-model-len" "32768" \
        "--gpu-memory-utilization" "0.85" \
        "--enable-auto-tool-choice" \
        "--tool-call-parser" "pythonic"
      ;;
    *)
      log "ERROR: unknown model alias $1"
      return 2
      ;;
  esac
}

kill_gpu3_server() {
  log "Stopping any existing server on port ${GPU3_PORT}"
  pkill -f -- "--port ${GPU3_PORT}" 2>/dev/null || true
  pkill -f -- "port ${GPU3_PORT}" 2>/dev/null || true
  sleep 5
}

serve_model_gpu3() {
  local alias="$1"
  local model_path="${MODEL_PATH[$alias]:-}"
  local served_id="${MODEL_SERVED_ID[$alias]:-}"
  local serve_log="${LOG_DIR}/serve_gpu3_${alias}_${STAMP}.log"
  local args=()
  mapfile -t args < <(model_args "$alias")

  if [ -z "$model_path" ] || [ -z "$served_id" ]; then
    log "ERROR: missing model config for $alias"
    return 2
  fi

  log "Serving $alias as $served_id on GPU3:$GPU3_PORT"
  CUDA_VISIBLE_DEVICES=3 nohup "${CONDA_VLLM[@]}" vllm serve \
    "$model_path" \
    --port "$GPU3_PORT" \
    --served-model-name "$served_id" \
    --tensor-parallel-size 1 \
    "${args[@]}" \
    > "$serve_log" 2>&1 &

  local waited=0
  local max_wait=900
  while ! curl -sf "http://127.0.0.1:${GPU3_PORT}/health" >/dev/null 2>&1; do
    if [ "$waited" -ge "$max_wait" ]; then
      log "ERROR: $alias did not become healthy within ${max_wait}s"
      tail -80 "$serve_log" || true
      return 1
    fi
    if grep -qE "CUDA out of memory|RuntimeError|ValueError|Engine core initialization failed" "$serve_log" 2>/dev/null; then
      log "ERROR: $alias startup error"
      grep -E "CUDA out of memory|RuntimeError|ValueError|Engine core initialization failed" "$serve_log" | tail -20 || true
      return 1
    fi
    sleep 10
    waited=$((waited + 10))
  done
  log "$alias is healthy after ${waited}s"
}

write_model_config() {
  local alias="$1"
  local out_root="$2"
  local tmp_cfg="$3"
  python3 - "$alias" "$out_root" "$tmp_cfg" <<'PY'
import sys
from pathlib import Path
import yaml

alias, out_root, tmp_cfg = sys.argv[1:4]
cfg = yaml.safe_load(Path("configs/r6/r6_preflight_new_models.yaml").read_text())
cfg["models"] = [alias]
cfg["output_root"] = out_root
Path(tmp_cfg).write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
PY
}

run_preflight_for_model() {
  local alias="$1"
  local out_root="${OUT_BASE}/${alias}"
  local tmp_cfg="/tmp/r6_preflight_${alias}_${STAMP}.yaml"

  if [ -e "$out_root" ]; then
    log "ERROR: refusing to reuse existing output root: $out_root"
    return 2
  fi
  mkdir -p "$out_root"
  write_model_config "$alias" "$out_root" "$tmp_cfg"

  "${CONDA_R6[@]}" scripts/r6/run_r6_live.py \
    --phase preflight \
    --config "$tmp_cfg" \
    --output-root "$out_root" \
    --live || {
      rm -f "$tmp_cfg"
      return 1
    }

  "${CONDA_R6[@]}" scripts/r6/final_integrity_audit_r6.py \
    --root "$out_root" \
    --report "reports/r6_sensitivity/R6_PREFLIGHT_${alias}_INTEGRITY_${STAMP}.md" || {
      rm -f "$tmp_cfg"
      return 1
    }
  "${CONDA_R6[@]}" scripts/r6/extract_r6_metrics.py --root "$out_root" || {
    rm -f "$tmp_cfg"
    return 1
  }

  rm -f "$tmp_cfg"
}

mkdir -p "$OUT_BASE" "$LOG_DIR"
log "START $(date -u +%FT%TZ)"
log "Output base: $OUT_BASE"
log "Models: ${MODELS_TO_RUN[*]}"

PASSED=()
FAILED=()

for alias in "${MODELS_TO_RUN[@]}"; do
  log "━━━ $alias ━━━━━━━━━━━━━━━━━━━━━━━━━━"
  model_path="${MODEL_PATH[$alias]:-}"
  if [ -z "$model_path" ]; then
    log "FAIL $alias: unknown alias"
    FAILED+=("${alias}:unknown_alias")
    continue
  fi
  if [ ! -f "${model_path}/config.json" ]; then
    log "SKIP $alias: missing ${model_path}/config.json"
    FAILED+=("${alias}:not_downloaded")
    continue
  fi

  kill_gpu3_server
  if ! serve_model_gpu3 "$alias"; then
    FAILED+=("${alias}:serve_failed")
    kill_gpu3_server
    continue
  fi

  if run_preflight_for_model "$alias"; then
    PASSED+=("$alias")
  else
    FAILED+=("${alias}:preflight_failed")
  fi
  kill_gpu3_server
done

log "PASSED: ${PASSED[*]:-none}"
log "FAILED: ${FAILED[*]:-none}"
log "DONE $(date -u +%FT%TZ)"

if [ "${#FAILED[@]}" -gt 0 ]; then
  exit 1
fi
