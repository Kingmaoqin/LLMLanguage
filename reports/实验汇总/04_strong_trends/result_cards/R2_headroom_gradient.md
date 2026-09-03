# Result Card R2 — Clarification Suppression scales with Oversight Headroom (STRONG TREND)
- Module: M3/M4, Trend 1 (headroom→controllability). Mechanism-motivated subgroup (pre-specified).
- Pooled: −0.50 (see R1). Subgroup by baseline-clarification tercile (R9v2 Qwen-72B):
  LOW +0.077 [−0.15,+0.31] p=1.0 (no room) | MID −0.256 [−0.77,+0.23] | HIGH −1.333 [−2.03,−0.69] p=.003, same-dir 69%.
- Trend: monotonic LOW→MID→HIGH. N=13 tasks/tercile.
- Mechanism: oversight headroom is the attackable resource; attack cuts hardest exactly where the agent normally asks the human most (i.e., high-stakes/ambiguous tasks).
- Exact claim: "the more oversight headroom a task has, the more strongly benign pressure suppresses it (monotonic, up to −1.33 turns)."
- Strength: STRONG TREND (~12/15). Priority: P0.
- Data: 04_strong_trends/data/headroom_clarification_task_level.csv; tables/headroom_summary.csv. Fig: figB.
