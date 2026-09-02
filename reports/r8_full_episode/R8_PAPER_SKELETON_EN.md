# Paper skeleton (EN) — Full-Episode Interactional Robustness of Tool-Using LLM Agents

**Working title:** *Outcome-Safe, Process-Nearly-Invariant: Do Urgency and Frustration Change Tool-Using Agents Over a Full Multi-Step Episode?*

**One-line claim:** Holding task, identity, facts, decisions, tools, policy, initial DB, official evaluator, and budget fixed, ordinary user urgency/frustration expressed across a complete tau2 episode does **not** change task success and moves tool-use process only **below pre-registered practical-importance thresholds** — with a single domain-specific (airline) frustration→tool-intensity signal as the one pre-registerable exception.

## Abstract (draft)
Prior work (R7) showed outcome-safe ≠ process-robust under a shared-prefix/suffix design but could not experimentally identify a confirmatory interactional-manipulation effect. We abandon suffix trimming and P-responsive eligibility and instead run full multi-step episodes on the official tau2-bench (retail+airline, native orchestrator + native evaluator). Across 36 tasks × 3 models × 5 user conditions × 5 replicates (2700 episodes, 2680 analyzed), we contrast a matched neutral controller (C1) against static urgency (C2), adaptive urgency+continuation (C3), and adaptive frustration (C4), with the official cooperative simulator (C0) as a scaffold check. Co-primary outcomes are official reward (P1) and total tool calls (P2). Pressure does not change reward (C3−C1 +0.02, C4−C1 −0.01; excludes 5pp) and increases tool calls only sub-threshold (C3 +0.50, C4 +0.69 calls < 1.0). A calibrated-null decision holds pooled; airline frustration shows an above-threshold exploratory signal (+1.4 calls). A significant scaffold effect (C1−C0: −11pp reward) cautions against cross-simulator comparison.

## 1. Introduction
- Gap: does *interactional style over a whole episode* (not a trimmed suffix) steer a tool-using agent's outcome or process, holding everything task-relevant fixed?
- Contribution: (i) a condition-blind Canonical Semantic Controller + frozen style renderer that varies ONLY interactional expression; (ii) a pre-registered, ITT, dual-review pipeline on the official native benchmark; (iii) calibrated-null primary + exploratory domain heterogeneity + scaffold-effect diagnosis.

## 2. Related work
tau2-bench; user-simulator process metrics; interactional/social-engineering pressure on LLMs; R7 (suffix design, non-identifiability); ITT and calibrated nulls in ML eval.

## 3. Method
- **Design:** 36 tasks (retail 6/6/6, airline 4/4/10 read/single/compound; airline asymmetry justified by domain structure), 3 models, C0–C4, 5 reps = 2700 episodes. Pairing unit (domain,task,model,rep).
- **Conditions:** C0 official; C1 matched neutral (main control); C2 static urgency; C3 adaptive urgency+continuation; C4 adaptive frustration (deterministic level 0–3 from agent-VISIBLE behavior only).
- **Invariance:** one condition-blind semantic controller (reuses tau2 neutral guidelines) + frozen finite-state style renderer; forbidden-phrase guard on style text; pre-run dual semantic review (contamination=0, C3>C1 urgency, C4>C1 frustration).
- **Native execution:** tau2 Orchestrator + `evaluate_simulation` (DB + COMMUNICATE); no evaluator fork.
- **Analysis (pre-registered):** paired risk/mean diff; task-cluster bootstrap 95% CI; clustered permutation; Holm over 4 primary tests; McNemar; practical thresholds (reward 5pp; tools ≥1 call & ≥15%); heterogeneity; concentration (top-k, Herfindahl, LOO); endpoint-preserved (both-success, selection-biased); decision rules R1–R5. ITT: all frozen episodes, no eligibility filtering.

## 4. Results
- **Integrity:** 2680/2700 (0.74% documented mistral context-overflow exclusion), 0 dup/reward-None/hash/DB-leak/double-impl-mismatch.
- **P1 reward (null):** C3−C1 +0.024 (Holm .75), C4−C1 −0.006 (Holm .88); CIs exclude 5pp.
- **P2 tools (sub-threshold):** C3−C1 +0.50 (Holm .089), C4−C1 +0.69 (Holm .054); < 1.0-call threshold.
- **Controls:** C2−C1 tools +0.49 (static ≈ adaptive, both sub-threshold); C1−C0 reward −0.11 / tools −1.0 (scaffold effect).
- **Heterogeneity (exploratory):** airline C4−C1 +1.41 (>threshold) vs retail −0.04; compound +0.98 / read +0.81 / single +0.10; all 3 models same-direction positive.
- **Concentration:** diffuse (top2 0.23, Herfindahl 0.059, LOO [0.57,0.76]).
- **Endpoint-preserved:** C3/C4 +0.37/+0.36 tools among both-success (median 0).
- **Post-run mechanism review:** low agreement (inconclusive), consistent with a small/ambiguous process effect.

## 5. Discussion
- Ordinary full-episode pressure is outcome-safe and process-near-invariant at practical scale; loose process metrics can overstate vulnerability.
- The airline frustration signal is the one pre-registerable exception → conditional, domain-dependent process sensitivity.
- Scaffold effect: custom simulators change absolute rates → within-scaffold contrasts only.

## 6. Limitations
- Reward is single-source (native evaluator). Post-run mechanism review under-powered (n<300). airline type-asymmetry (4/4/10). 20 mistral context exclusions. Online-vLLM reproducibility depends on batch-invariance (not bit-exact). Dual review is agent-based, not human.

## 7. Conclusion
Calibrated null (R4) for pooled urgency/frustration process/outcome effects over full multi-step tau2 episodes; an exploratory airline-specific frustration→tool-intensity signal warrants a pre-registered follow-up. No confirmatory IPMA claim.

## Forbidden (do NOT write)
"adaptive IPMA works"; "universal attack"; "no effect whatsoever"; "process-robustness demonstrated as a defense".

## Figures/tables (planned)
T1 design+integrity; T2 P1/P2 primary with CI+Holm; F1 forest plot C3/C4−C1 by domain/type/model; F2 condition means (reward, tools); T3 controls (C2−C1, C1−C0); T4 concentration/LOO; F3 endpoint-preserved.
