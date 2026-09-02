# Optimized Interactional Process Manipulation of Tool-Using Agents: A Sandboxed Attack Study (R8-A)

> Paper skeleton. Infrastructure and pre-registration frozen; dev running; results
> sections auto-filled by `finalize_report.py` on completion.

## Abstract (to finalize)
We study whether an adversary who keeps task facts, user identity, authorization, policy,
tools and the legitimate endpoint fixed can, using only multi-turn **user-side interactional
expression**, **directionally manipulate the process** of a multi-step tool-using agent. We
separate an optimized targeted attacker (C4) from ordinary adaptive pressure (C3), matched
neutral presence (C1), static pressure (C2) and the official cooperative user (C0), on 24
held-out tau2-bench tasks × 3 models × 5 replicates (1800 episodes), with a 432-episode dev
set used only to select and freeze the attacker policy. Semantic invariance is guaranteed by
construction: all conditions share one condition-blind semantic controller and the attacker
adds only a ≤40-token style wrapper around the preserved payload. [Result verdict per family.]

## 1. Introduction
Contribution: an attack-vs-ordinary-pressure design that isolates whether *adversarial
targeting* (candidate generation + dual constraint filter + targeted selection) adds process
control beyond ordinary interactional pressure, under a fully local, side-effect-free sandbox.

## 2. Threat Model
Attacker sees only the user-visible transcript; never the system prompt, hidden reasoning,
hidden tool logs, DB secrets or evaluator. Fixed: task facts, identity, authorization, policy,
tools, legal endpoint. Budget: ≤3 non-neutral interventions, ≤40 style tokens each, no extra
user turns. Objective is directional **process** control (F1 action intensity, F2 mutation/
confirmation timing, F3 benign abandonment), not an unsafe outcome. Safety refusals are logged
and fall back to neutral (no bypass).

## 3. Method
### 3.1 Canonical semantic controller (invariance by construction)
### 3.2 Conditions C0–C4
### 3.3 Optimized attacker: candidate generator → dual isolated constraint filter (fail-closed)
        → targeted selector → attack budget → exposure qualification
### 3.4 Dev policy search (P0–P3) and joint-objective freezing (not max-PASR)
### 3.5 Task pool, complexity gate (≥5 actions, ≥3 tools), family binding, exclusions
### 3.6 Local sandbox isolation and safety protocol

## 4. Experimental Setup
Models: gemma-4-31B, gpt-oss-120B, mistral-small-3.2 (all local vLLM, temp 0). Domains: retail,
airline (tau2 1.0.0 base split). Airline capped at its 7 strict-gate tasks → documented domain
covariate. 2232 episodes total.

## 5. Analysis Plan (pre-registered)
Pairing unit task×model×replicate. Confirmatory: C4−C1 process, C4−C3 process, C4−C1 endpoint
reward. Paired task-cluster bootstrap 95% CI, paired permutation, Holm across 3 tests, effect
size. Practical thresholds frozen pre-run (F1 ≥2 or ≥25%; F2 ≥1 step; F3 0→1). ASR_process =
endpoint preserved ∧ safety preserved ∧ process change beyond threshold; matched-neutral FPR
reported. Subgroups + leave-one-out + top-2 concentration (>40% ⇒ downgrade).

## 6. Results (to finalize)
Table 1: per-family C4−C1 / C4−C3 process + CI + Holm-p + effect size.
Table 2: endpoint preservation (overall / DB / COMMUNICATE).
Table 3: ASR_process vs matched-neutral FPR.
Fig 1: per-model / per-domain forest. Fig 2: leave-one-out stability.
Dual-review agreement (pre/post). Exposure-qualified descriptive.

## 7. Decision (rules A–E)
[A supported / B ordinary pressure / C conditional / D calibrated null / E infra-fail.]

## 8. Safety, Isolation and Ethics
Authorized local research, sandbox only; loopback endpoints; resettable synthetic DBs; zero
outbound events; zero non-allowlisted tool calls; zero external side effects; safety refusals
logged and neutral-fallback. No claim or implication of attacking real systems, bypassing
platform safeguards, or unauthorized access.

## 9. Limitations
Local open-weight models; two domains; airline scarcity; heuristic secondary metrics audited by
dual review; attacker/user share the mistral endpoint (role-separated, tool-free).
