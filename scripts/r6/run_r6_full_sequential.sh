#!/usr/bin/env bash
# R6 full experiment sequential model runner.
#
# This script is intentionally gated. It will not run unless:
#   R6_ALLOW_FULL=1 bash scripts/r6/run_r6_full_sequential.sh
#
# It writes to a fresh timestamped root by default:
#   results/r6_sensitivity/full_main_seq_<UTC timestamp>

set -euo pipefail

cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2

if [ "${R6_ALLOW_FULL:-0}" != "1" ]; then
  echo "[r6-full-seq] REFUSING: set R6_ALLOW_FULL=1 only after preflight/integrity/report gates pass."
  exit 2
fi

CONDA_VLLM=(conda run -n p08_skilloverload)
CONDA_R6=(conda run -n agentsearch python)
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_ROOT="${R6_FULL_ROOT:-results/r6_sensitivity/full_main_seq_${STAMP}}"
LOG_DIR="logs"
GPU3_PORT=8007

GPU3_MODELS=(mistral_small_3p2)

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

log() { echo "[r6-full-seq] $*"; }

model_args() {
  case "$1" in
    mistral_small_3p2)
      printf '%s\n' \
        "--max-model-len" "16384" \
        "--gpu-memory-utilization" "0.90" \
        "--enable-auto-tool-choice" \
        "--tool-call-parser" "mistral" \
        "--limit-mm-per-prompt" '{"image":0}'
      ;;
    gemma3_27b)
      printf '%s\n' "--max-model-len" "32768" "--gpu-memory-utilization" "0.90" \
        "--enable-auto-tool-choice" "--tool-call-parser" "pythonic"
      ;;
    olmo2_32b)
      printf '%s\n' "--max-model-len" "4096" "--gpu-memory-utilization" "0.92" \
        "--enable-auto-tool-choice" "--tool-call-parser" "pythonic"
      ;;
    phi4_reasoning)
      printf '%s\n' "--max-model-len" "32768" "--gpu-memory-utilization" "0.85" \
        "--enable-auto-tool-choice" "--tool-call-parser" "pythonic"
      ;;
    *)
      log "ERROR: unknown GPU3 model $1"
      return 2
      ;;
  esac
}

kill_gpu3() {
  pkill -f -- "--port ${GPU3_PORT}" 2>/dev/null || true
  pkill -f -- "port ${GPU3_PORT}" 2>/dev/null || true
  sleep 5
}

serve_gpu3() {
  local alias="$1"
  local model_path="${MODEL_PATH[$alias]:-}"
  local served_id="${MODEL_SERVED_ID[$alias]:-}"
  local serve_log="${LOG_DIR}/serve_gpu3_${alias}_full_${STAMP}.log"
  local args=()
  mapfile -t args < <(model_args "$alias")

  if [ ! -f "${model_path}/config.json" ]; then
    log "ERROR: missing ${model_path}/config.json"
    return 2
  fi

  CUDA_VISIBLE_DEVICES=3 nohup "${CONDA_VLLM[@]}" vllm serve \
    "$model_path" \
    --port "$GPU3_PORT" \
    --served-model-name "$served_id" \
    --tensor-parallel-size 1 \
    "${args[@]}" \
    > "$serve_log" 2>&1 &

  local waited=0
  while ! curl -sf "http://127.0.0.1:${GPU3_PORT}/health" >/dev/null 2>&1; do
    sleep 10
    waited=$((waited + 10))
    if [ "$waited" -ge 900 ]; then
      log "ERROR: $alias startup timeout"
      tail -80 "$serve_log" || true
      return 1
    fi
  done
}

write_cfg() {
  local aliases_csv="$1"
  local tmp_cfg="$2"
  python3 - "$aliases_csv" "$OUT_ROOT" "$tmp_cfg" <<'PY'
import sys
from pathlib import Path
import yaml

aliases = [x for x in sys.argv[1].split(",") if x]
out_root, tmp_cfg = sys.argv[2:4]
cfg = yaml.safe_load(Path("configs/r6/r6_full_main_v2.yaml").read_text())
cfg["models"] = aliases
cfg["output_root"] = out_root
Path(tmp_cfg).write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
PY
}

mkdir -p "$OUT_ROOT" "$LOG_DIR"
if [ "${R6_RESUME:-0}" != "1" ] && [ -n "$(find "$OUT_ROOT" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
  log "ERROR: refusing to use non-empty output root: $OUT_ROOT"
  exit 2
fi

log "START $(date -u +%FT%TZ)"
log "Output: $OUT_ROOT"

BASE_CFG="/tmp/r6_full_baselines_${STAMP}.yaml"
write_cfg "gemma4_31b,gpt_oss_120b" "$BASE_CFG"
"${CONDA_R6[@]}" scripts/r6/run_r6_live.py \
  --phase full \
  --config "$BASE_CFG" \
  --output-root "$OUT_ROOT" \
  --live \
  --skip-existing \
  --allow-live-pilot-full || {
    rm -f "$BASE_CFG"
    exit 1
  }
rm -f "$BASE_CFG"

for alias in "${GPU3_MODELS[@]}"; do
  kill_gpu3
  serve_gpu3 "$alias"
  TMP_CFG="/tmp/r6_full_${alias}_${STAMP}.yaml"
  write_cfg "$alias" "$TMP_CFG"
  "${CONDA_R6[@]}" scripts/r6/run_r6_live.py \
    --phase full \
    --config "$TMP_CFG" \
    --output-root "$OUT_ROOT" \
    --live \
    --skip-existing \
    --allow-live-pilot-full || {
      rm -f "$TMP_CFG"
      kill_gpu3
      exit 1
    }
  rm -f "$TMP_CFG"
  kill_gpu3
done

"${CONDA_R6[@]}" scripts/r6/final_integrity_audit_r6.py \
  --root "$OUT_ROOT" \
  --report "reports/r6_sensitivity/R6_FULL_INTEGRITY_${STAMP}.md"
"${CONDA_R6[@]}" scripts/r6/extract_r6_metrics.py --root "$OUT_ROOT"
"${CONDA_R6[@]}" scripts/r6/statistical_analysis_r6.py \
  --root "$OUT_ROOT" \
  --report "reports/r6_sensitivity/R6_STATISTICAL_ANALYSIS_${STAMP}.md"
"${CONDA_R6[@]}" scripts/r6/analyze_r6_interactional_profile.py \
  --root "$OUT_ROOT" \
  --report "reports/r6_sensitivity/R6_INTERACTIONAL_ROBUSTNESS_PROFILE_${STAMP}.md"

log "DONE $(date -u +%FT%TZ)"
