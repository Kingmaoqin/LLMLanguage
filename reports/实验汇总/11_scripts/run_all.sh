#!/bin/bash
# Reproduce all 实验汇总 tables & figures from raw episode data (read-only sources).
cd "$(dirname "$0")"
for s in 01_inventory 02_recompute_core_metrics 03_headroom_analysis 04_language_channel_matrix 05_joint_oversight_execution 06_cross_experiment_evidence 07_generate_figures; do
  echo "== $s =="; python3 "$s.py" || exit 1
done
echo "DONE. Outputs under ../ (00_inventory, 02_recomputed_metrics, 04_strong_trends, 05_attack_chain, 06_process_control, 07_adaptive_static, 09_tables, 10_figures)."
