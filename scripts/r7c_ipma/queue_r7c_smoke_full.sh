#!/usr/bin/env bash
# R7-C/IPMA smoke/full queue with explicit R7-C assets and audit postprocess.
#
# Smoke:
#   R7C_ALLOW_SMOKE=1 bash scripts/r7c_ipma/queue_r7c_smoke_full.sh smoke
# Plan-only smoke/full, no model calls:
#   bash scripts/r7c_ipma/queue_r7c_smoke_full.sh smoke plan
#
# Full, after smoke and user review:
#   R7C_ALLOW_FULL=1 R7C_SMOKE_ROOT=results/r7c_ipma/smoke/live_... \
#     bash scripts/r7c_ipma/queue_r7c_smoke_full.sh full

set -uo pipefail
cd /home/xqin5/llmlanguage/ir_mstu_stage2 || exit 2

MODE="${1:-smoke}"
DRY_RUN="${2:-}"
case "$MODE" in
  smoke) PHASE="dev"; CFG="configs/r7c_ipma/r7c_smoke.yaml"; ALLOW_ENV="${R7C_ALLOW_SMOKE:-0}" ;;
  full) PHASE="full"; CFG="configs/r7c_ipma/r7c_full.yaml"; ALLOW_ENV="${R7C_ALLOW_FULL:-0}" ;;
  *) echo "[r7c-queue] usage: $0 smoke|full" >&2; exit 2 ;;
esac

STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_ROOT="${R7C_OUT_ROOT:-results/r7c_ipma/${MODE}/live_${STAMP}}"
LOG_DIR="logs"
mkdir -p "$LOG_DIR" "$OUT_ROOT"

PYTHON="${R7C_PYTHON:-python}"
RUNNER="scripts/r7b_ipma/run_r7b_live.py"
REGISTRY="data/r7c_ipma/r7c_task_registry.csv"
TEMPLATES="data/r7c_ipma/frozen/r7c_frozen_templates.jsonl"
TASKS="data/r7c_ipma/r7c_tasks.yaml"
POLICIES="data/r7c_ipma/r7c_task_user_policies.yaml"
ANNOTATIONS="data/r7c_ipma/r7c_task_policy_annotations.yaml"
SEED_STATES="data/r7c_ipma/r7c_seed_states.yaml"
SEMANTIC_OUT="results/r7c_ipma/template_audit/llm_semantic_judgments.csv"

log() { printf '[r7c-queue] %s %s\n' "$(date -u +%FT%TZ)" "$*"; }

if [ "$DRY_RUN" != "plan" ] && [ "$MODE" = "smoke" ] && [ "$ALLOW_ENV" != "1" ]; then
  log "REFUSING: set R7C_ALLOW_SMOKE=1 to run live smoke."
  exit 2
fi
if [ "$DRY_RUN" != "plan" ] && [ "$MODE" = "full" ] && [ "$ALLOW_ENV" != "1" ]; then
  log "REFUSING: set R7C_ALLOW_FULL=1 to run full after smoke review."
  exit 2
fi
if [ "$DRY_RUN" != "plan" ] && [ "$MODE" = "full" ]; then
  if [ -z "${R7C_SMOKE_ROOT:-}" ]; then
    log "REFUSING: set R7C_SMOKE_ROOT to a passed smoke run root before full."
    exit 2
  fi
  "$PYTHON" scripts/r7c_ipma/verify_r7c_smoke_gate.py --smoke-root "$R7C_SMOKE_ROOT" || exit $?
fi

ALLOW_FULL_ARGS=()
if [ "$MODE" = "full" ]; then
  ALLOW_FULL_ARGS=(--allow-full)
fi

run_live() {
  log "run live mode=${MODE}; out_root=${OUT_ROOT}"
  LIVE_ARGS=()
  if [ "$DRY_RUN" != "plan" ]; then
    LIVE_ARGS=(--live --skip-existing)
  fi
  "$PYTHON" "$RUNNER" \
    --phase "$PHASE" \
    --config "$CFG" \
    --output-root "$OUT_ROOT" \
    --registry "$REGISTRY" \
    --templates "$TEMPLATES" \
    --tasks-path "$TASKS" \
    --policies-path "$POLICIES" \
    --annotations-path "$ANNOTATIONS" \
    --seed-states-path "$SEED_STATES" \
    --run-label r7c \
    "${LIVE_ARGS[@]}" \
    "${ALLOW_FULL_ARGS[@]}"
}

postprocess() {
  log "postprocess: semantic + pairing + endpoint + PASR + stats"
  "$PYTHON" scripts/r7b_ipma/judge_template_semantic_invariance.py \
    --templates "$TEMPLATES" \
    --out_csv "$SEMANTIC_OUT" \
    --report "reports/r7c_ipma/R7C_TEMPLATE_SEMANTIC_AUDIT_${STAMP}.md" || return $?
  "$PYTHON" scripts/r7b_ipma/check_pairing_invariants.py \
    --trace_root "$OUT_ROOT" \
    --out_csv "$OUT_ROOT/integrity/pairing_invariant_report.csv" \
    --report "reports/r7c_ipma/R7C_PAIRING_INVARIANT_AUDIT_${STAMP}.md" || return $?
  "$PYTHON" scripts/r7b_ipma/evaluate_endpoint_from_snapshot.py \
    --trace_root "$OUT_ROOT" \
    --registry "$REGISTRY" \
    --out_csv "$OUT_ROOT/endpoint/endpoint_oracle_per_run.csv" \
    --report "reports/r7c_ipma/R7C_ENDPOINT_ORACLE_AUDIT_${STAMP}.md" || return $?
  "$PYTHON" scripts/r7b_ipma/compute_pasr_metrics.py \
    --trace_root "$OUT_ROOT" \
    --registry "$REGISTRY" \
    --endpoint "$OUT_ROOT/endpoint/endpoint_oracle_per_run.csv" \
    --pairing "$OUT_ROOT/integrity/pairing_invariant_report.csv" \
    --semantic "$SEMANTIC_OUT" \
    --out_dir "$OUT_ROOT/metrics" \
    --report "reports/r7c_ipma/R7C_PASR_RECOMPUTE_AUDIT_${STAMP}.md" || return $?
  "$PYTHON" scripts/r7b_ipma/run_statistical_analysis.py \
    --pairs "$OUT_ROOT/metrics/r7b_pairs.csv" \
    --out_dir "$OUT_ROOT/analysis" \
    --report "reports/r7c_ipma/R7C_STATISTICAL_ANALYSIS_${STAMP}.md" || return $?
}

run_live
RC=$?
if [ "$RC" -ne 0 ]; then
  log "live run failed rc=${RC}; endpoint/table evidence may be in ${OUT_ROOT}"
  exit "$RC"
fi
if [ "$DRY_RUN" = "plan" ]; then
  log "PLAN DONE mode=${MODE}; out_root=${OUT_ROOT}"
  exit 0
fi

postprocess
RC=$?
if [ "$RC" -ne 0 ]; then
  log "postprocess failed rc=${RC}"
  exit "$RC"
fi

log "DONE mode=${MODE}; out_root=${OUT_ROOT}"
