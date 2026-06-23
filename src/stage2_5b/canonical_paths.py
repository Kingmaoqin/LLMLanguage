"""Single source of truth for the Stage-2.5b round-4 (R4) canonical artifact paths.

All active Stage-2.5b scripts must default to these roots. The legacy round-3
``full_blocks_retail8_confirmatory_v2_atomic`` root and the pre-R4
``results/stage2_5b_analysis`` / ``figures/stage2_5b`` directories are retained for
historical audit only and may be reached *exclusively* via explicit command-line
arguments — never as a default.

Paths are repo-relative POSIX strings so they can be used directly as argparse
defaults and asserted verbatim in tests. Scripts join them onto their own ``ROOT``.
"""

from __future__ import annotations

# R4 confirmatory result root (2 models x 8 retail tasks x 6 conditions x 5 seeds).
R4_RESULTS_ROOT = "results/stage2_5b_repair/r4_confirmatory_canonical"

# R4 analysis tables (paired contrasts, equivalence, per-task diagnostics, ...).
R4_ANALYSIS_ROOT = "results/stage2_5b_analysis_r4"

# R4 report figures.
R4_FIGURES_ROOT = "figures/stage2_5b_r4"

# R4 report directory (checkpoints, audits, final reports).
R4_REPORTS_ROOT = "reports/stage2_5b"

# R4 final integrity (G11) report consumed by analyze_confirmatory.py.
R4_INTEGRITY_CSV = "results/stage2_5b_repair/r4_final_integrity_report.csv"

# Derived analysis-file defaults (kept here so every consumer agrees byte-for-byte).
R4_MATCHED_PAIRS = f"{R4_ANALYSIS_ROOT}/matched_pairs.csv"
R4_PAIRED_CONTRASTS = f"{R4_ANALYSIS_ROOT}/paired_contrasts_task_cluster_bootstrap.csv"
R4_EQUIVALENCE_RESULTS = f"{R4_ANALYSIS_ROOT}/equivalence_results.csv"

# Legacy roots — explicit-only, NEVER a default. Listed so tests can assert that no
# active default equals any of these.
LEGACY_RESULTS_ROOTS = (
    "results/stage2_5b_repair/full_blocks_retail8_confirmatory_v2_atomic",
    "results/stage2_5b_repair/full_blocks_retail8_confirmatory_4gpu",
    "results/stage2_5b_repair/full_blocks_retail8_confirmatory",
)
LEGACY_ANALYSIS_ROOT = "results/stage2_5b_analysis"
LEGACY_FIGURES_ROOT = "figures/stage2_5b"
