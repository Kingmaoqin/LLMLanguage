#!/bin/bash
# Unattended auto-push daemon for the E1 power run.
# Every INTERVAL: regenerate derived E1 summaries (ASR + bootstrap CI), commit small
# derived tables + reports, push to r9 branch AND merge->main. When the run finishes:
# add the full raw episodes, do a FINAL commit+push, free the GPU, and exit.
# Survives session end (launch with: setsid nohup ... & disown). Only this daemon commits.
set -u
REPO=/home/xqin5/llmlanguage/ir_mstu_stage2
HUI=/home/xqin5/llmlanguage/实验汇总
BRANCH=r9-mechanism-aligned-process-attack
R9=/home/xqin5/.conda/envs/r9_bfcl/bin/python
INTERVAL=${1:-1800}        # seconds between checkpoints (default 30 min)
MAX_ITERS=${2:-60}         # safety cap (60 * 30min = 30h)
LOG=$REPO/reports/r9_attack/auto_push.log
cd "$REPO" || exit 1
log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }

publish(){  # $1 = commit message ; $2 = "final" to also add raw episodes
  local msg="$1" final="${2:-}"
  git -C "$REPO" checkout "$BRANCH" -q 2>/dev/null
  # sync 实验汇总 report package into repo (derived CSVs live here)
  rsync -a --delete --exclude '__pycache__' "$HUI"/ "$REPO/reports/实验汇总/" 2>/dev/null
  git add -A -- "reports/实验汇总/" 2>/dev/null
  git add scripts/r9_attack/e1_autopush_regen.py scripts/r9_attack/auto_push_results.sh scripts/r9_attack/run_e1_power.sh 2>/dev/null
  git add -f results/e1_power/summaries/*.csv results/e1_power/summaries/STATUS.txt 2>/dev/null
  if [ "$final" = "final" ]; then
    git add -f results/e1_power/confirmatory/confirmatory_episodes.jsonl 2>/dev/null
    git add -f results/e1_power/confirmatory/*.json 2>/dev/null
  fi
  if git diff --cached --quiet; then log "no changes to commit"; return 0; fi
  git commit -q -F - <<COMMIT
$msg

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
COMMIT
  if git push origin "$BRANCH" >>"$LOG" 2>&1; then log "pushed $BRANCH"; else log "push $BRANCH FAILED"; fi
  # best-effort merge -> main
  git fetch origin -q 2>>"$LOG"
  if git checkout -B _autopm origin/main -q 2>>"$LOG"; then
    if git merge "$BRANCH" --no-edit -m "auto: merge E1 results into main" >>"$LOG" 2>&1; then
      git push origin _autopm:main >>"$LOG" 2>&1 && log "pushed main" || log "push main FAILED"
    else
      git merge --abort 2>/dev/null; log "merge->main conflict, aborted (r9 still has everything)"
    fi
    git checkout "$BRANCH" -q 2>/dev/null
    git branch -D _autopm -q 2>/dev/null
  fi
}

log "=== auto-push daemon started (interval=${INTERVAL}s, max=${MAX_ITERS}) ==="
i=0
while [ $i -lt $MAX_ITERS ]; do
  i=$((i+1))
  status=$($R9 "$REPO/scripts/r9_attack/e1_autopush_regen.py" 2>>"$LOG")
  log "iter $i: $status"
  if echo "$status" | grep -q "^DONE"; then
    log "run finished -> final publish"
    # ensure the run's own post-analysis (ASR+CI in e1_power_run.log) had time to write
    sleep 20
    $R9 "$REPO/scripts/r9_attack/e1_autopush_regen.py" >>"$LOG" 2>&1
    publish "auto: E1 power run COMPLETE — end-to-end ASR (repeats=6) + bootstrap CI [final]" final
    # free GPU: kill our own qwen vLLM on :8010 (only if owned by us)
    for pid in $(pgrep -f "vllm serve Qwen/Qwen2.5-72B-Instruct-AWQ.*--port 8010"); do
      owner=$(ps -o user= -p "$pid" 2>/dev/null | tr -d ' ')
      if [ "$owner" = "xqin5" ]; then kill "$pid" 2>/dev/null && log "freed GPU: killed vLLM pid $pid"; fi
    done
    log "=== daemon done, exiting ==="
    exit 0
  fi
  publish "auto: E1 results checkpoint ($(date '+%m-%d %H:%M')) — partial, run in progress"
  sleep "$INTERVAL"
done
log "=== max iters reached, final publish + exit ==="
$R9 "$REPO/scripts/r9_attack/e1_autopush_regen.py" >>"$LOG" 2>&1
publish "auto: E1 results (max-iters safety stop)" final
exit 0
