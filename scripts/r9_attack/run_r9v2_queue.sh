#!/bin/bash
# R9v2 BFCL-deep queued full run. Waits for GPU3 to free NATURALLY (user's leftover task
# finishes on its own -- we never kill it), deploys llama there, ensures qwen is alive on
# GPU1, then runs the full BFCL-deep pipeline. Fully detached; resumable (ResultsSink dedup).
set -u
cd /home/xqin5/llmlanguage/ir_mstu_stage2
export R9_BFCL_CATEGORIES="multi_turn_base,multi_turn_miss_param"
export R9_INCLUDE_TS=0
export R9_RESULTS_SUBDIR=r9v2
P08=/home/xqin5/.conda/envs/p08_skilloverload/bin
R9=/home/xqin5/.conda/envs/r9_bfcl/bin/python
QLOG=reports/r9_attack/r9v2_queue.log
log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*" >> "$QLOG"; }

log "queue started; waiting for GPU3 to free (never killing the user's task)"
# 1. wait until GPU3 used memory drops below 12GB (leftover task finished)
while true; do
  u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 3 2>/dev/null | tr -d ' ')
  [ -n "$u" ] && [ "$u" -lt 12000 ] 2>/dev/null && { log "GPU3 free (${u} MiB used)"; break; }
  sleep 120
done

deploy(){ # port dev served model parser
  local port=$1 dev=$2 served=$3 model=$4 parser=$5 lg=$6
  if curl -s -m 4 http://127.0.0.1:$port/v1/models 2>/dev/null | grep -q "$served"; then return 0; fi
  log "deploying $served on GPU$dev:$port"
  CUDA_VISIBLE_DEVICES=$dev nohup $P08/vllm serve "$model" \
    --served-model-name "$served" --port $port --max-model-len 16384 \
    --gpu-memory-utilization 0.90 --quantization awq_marlin \
    --enable-auto-tool-choice --tool-call-parser "$parser" \
    </dev/null > "$lg" 2>&1 &
}

# 2. deploy llama on the freed GPU3; ensure qwen still alive on GPU1 (redeploy if it died)
deploy 8009 3 llama33-70b-awq casperhansen/llama-3.3-70b-instruct-awq llama3_json reports/r9_attack/vllm_llama70b.log
deploy 8010 1 qwen25-72b Qwen/Qwen2.5-72B-Instruct-AWQ hermes reports/r9_attack/vllm_qwen72b.log

# 3. wait for BOTH servers ready
log "waiting for both servers ready"
while ! (curl -s -m 4 http://127.0.0.1:8010/v1/models 2>/dev/null | grep -q qwen25-72b \
      && curl -s -m 4 http://127.0.0.1:8009/v1/models 2>/dev/null | grep -q llama33-70b-awq); do
  sleep 20
done
log "both servers up; verifying tool-calling"
sleep 5

# 4. run the full BFCL-deep pipeline (splits already frozen -> skip to canonical).
# conf-repeats=3: test 80 tasks x 6 conditions x 3 x 2 models ~= 2880 episodes (~10h).
log "launching full BFCL-deep pipeline"
$R9 -u scripts/r9_attack/run_full_pipeline.py \
  --candidates qwen25_72b llama33_70b --skip-to canonical \
  --cal-repeats 2 --dev-repeats 3 --conf-repeats 3 --confounder-repeats 3 \
  >> reports/r9_attack/r9v2_pipeline.log 2>&1
log "pipeline exited rc=$?"
