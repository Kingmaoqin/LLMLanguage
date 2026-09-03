# Result Card R1 — Clarification / Human-Oversight Suppression
- Module: M3 (Human Oversight Displacement) / M4. Level: L1.
- Question: can benign pressure interactions make the agent ask the human less?
- Pooled result (EPISODE_LEVEL, R9v2 Qwen-72B BFCL-deep, ~700 compression ep, 38-39 tasks):
  clarification C4−C1 = −0.504 [−0.855,−0.162], p=.009; C5−C1 = −0.851 [−1.342,−0.351], p=.002.
  Zero-clarification (full bypass) rate: C1 23.1% → C4 33.3% (+10.2pp) → C5 36.8% (+13.7pp).
- Effect: −0.50 turns (−29% rel); +10pp absolute full-bypass.
- Consistency: base −0.569 & miss_param −0.455 (same dir); strengthens with headroom (R2).
- Mechanism: verification channel substitution (human ↓ while tool reads not ↓; success ns).
- Attack relevance: direct control of a human-oversight channel via benign language.
- Exact claim supported: "human clarification is a directly suppressible oversight channel under benign pressure (~0.5 turns / +10pp full bypass)."
- Strength: STRONG (Local Signal Score ~11/15). Priority: P0.
- Data: 02_recomputed_metrics/condition_level/r9v2_condition.csv; 05_attack_chain/joint_analysis/condition_rates.csv. Fig: figA, figD.
- Gap: cross-model; does not by itself cascade to execution (see boundary note).
