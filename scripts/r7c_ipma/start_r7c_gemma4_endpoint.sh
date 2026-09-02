#!/usr/bin/env bash
# Start the R7-C Gemma4 endpoint only when :8005 is not already serving g4.

set -uo pipefail
cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2

PORT="${R7C_GEMMA_PORT:-8005}"
SERVED_ID="${R7C_GEMMA_SERVED_ID:-g4}"
WEIGHTS="${R7C_GEMMA_WEIGHTS:-/home/xqin5/hf_p08_models/gemma-4-31B-it}"
CONDA_ENV="${R7C_VLLM_ENV:-p08_skilloverload}"
GPU="${R7C_GEMMA_GPU:-}"
LOG_DIR="${R7C_LOG_DIR:-logs}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/serve_gemma4_31b_r7c_${STAMP}.log"
PID_FILE="${LOG_DIR}/serve_gemma4_31b_r7c.pid"

mkdir -p "$LOG_DIR"

endpoint_up() {
  curl -sf -m 8 "http://127.0.0.1:${PORT}/v1/models" 2>/dev/null \
    | python3 -c "import sys,json
try:
    ids=[x.get('id') for x in json.load(sys.stdin).get('data',[])]
except Exception:
    ids=[]
sys.exit(0 if '${SERVED_ID}' in ids else 1)" 2>/dev/null
}

freest_gpu() {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits 2>/dev/null \
    | tr -d ' ' | awk -F, '{print $2, $1}' | sort -rn | head -1 | awk '{print $2}'
}

if endpoint_up; then
  echo "[r7c-gemma] endpoint already up on :${PORT} with served_id=${SERVED_ID}"
  exit 0
fi

if [ ! -f "${WEIGHTS}/config.json" ]; then
  echo "[r7c-gemma] missing ${WEIGHTS}/config.json" >&2
  exit 2
fi

if [ -z "$GPU" ]; then
  GPU="$(freest_gpu)"
fi
if [ -z "$GPU" ]; then
  echo "[r7c-gemma] could not select a GPU" >&2
  exit 3
fi

echo "[r7c-gemma] starting Gemma4 on GPU ${GPU}, port ${PORT}; log=${LOG_FILE}"
CUDA_VISIBLE_DEVICES="$GPU" HF_HUB_OFFLINE=1 nohup conda run -n "$CONDA_ENV" vllm serve "$WEIGHTS" \
  --port "$PORT" --served-model-name "$SERVED_ID" \
  --enable-auto-tool-choice --tool-call-parser gemma4 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization "${R7C_GEMMA_GPU_MEMORY_UTILIZATION:-0.86}" \
  --max-model-len "${R7C_GEMMA_MAX_MODEL_LEN:-16384}" \
  --max-num-batched-tokens "${R7C_GEMMA_MAX_NUM_BATCHED_TOKENS:-8192}" \
  > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

for _ in $(seq 1 180); do
  if endpoint_up; then
    echo "[r7c-gemma] endpoint up on :${PORT}; pid=$(cat "$PID_FILE")"
    exit 0
  fi
  sleep 10
done

echo "[r7c-gemma] startup timeout; tailing log" >&2
tail -80 "$LOG_FILE" >&2 || true
exit 1
