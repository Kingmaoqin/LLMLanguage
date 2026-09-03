#!/usr/bin/env python3
"""Assemble cross-experiment evidence, process-control action space, attack-chain status,
source manifest & provenance. Mixes EPISODE_LEVEL (recomputed here) and SUMMARY_ONLY (from
prior frozen reports of R6/R7/R8/MISROUTE). Every row tags source_level."""
import csv, os
from _common import OUT

def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("wrote", path.replace(OUT+"/",""), f"({len(rows)} rows)")

# ---- cross_experiment_evidence.csv : one row per scientific signal ----
CE=[
 dict(signal_name="clarification controllability (oversight suppression)",
      R6_support="indirect(confirmation moves)",R7_support="",R8_support="",R9v1_support="weak(inflation shifts)",
      R9v2_support="STRONG (C4-C1=-0.504,p=.009; zeroclar +10pp)",MISROUTE_support="",
      number_of_independent_experiments=2,models="qwen(+gemma/mistral R9v1)",tasks="BFCL-deep",
      direction_consistency="consistent",best_effect="-0.504 turns / +10pp zero-clar",
      interpretation="human-oversight channel is directly suppressible by benign pressure",strength="STRONG",source_level="EPISODE_LEVEL"),
 dict(signal_name="headroom-dependent controllability",
      R6_support="",R7_support="R7-D(POS,PASR neg-corr -0.576)",R8_support="",R9v1_support="",
      R9v2_support="STRONG TREND (clar LOW +0.08->HIGH -1.33; VD only high-VD; VE additive all)",MISROUTE_support="",
      number_of_independent_experiments=2,models="qwen",tasks="BFCL-deep",direction_consistency="monotonic",
      best_effect="-1.33 turns (high headroom)",interpretation="oversight/behavior headroom is the attackable resource",strength="STRONG TREND",source_level="EPISODE_LEVEL/SUMMARY"),
 dict(signal_name="channel-specific language control",
      R6_support="STRONG (affect->route; progression->tool +0.343)",R7_support="",R8_support="",R9v1_support="",
      R9v2_support="STRONG (urgency->clar-; skepticism->clar+/reads+/write-delay)",MISROUTE_support="",
      number_of_independent_experiments=2,models="qwen + gemma/gpt-oss/mistral",tasks="BFCL+tau2",direction_consistency="channel-specific",
      best_effect="urgency clar -0.50 vs skepticism clar +0.33",interpretation="different language acts control different process channels",strength="STRONG",source_level="EPISODE_LEVEL/SUMMARY"),
 dict(signal_name="verification channel substitution",
      R6_support="",R7_support="",R8_support="",R9v1_support="",
      R9v2_support="STRONG (clar- while reads_before_write not down; total not down; success ns)",MISROUTE_support="",
      number_of_independent_experiments=1,models="qwen",tasks="BFCL-deep",direction_consistency="consistent",
      best_effect="clar-0.50 vs reads +0.18(ns)",interpretation="pressure changes WHO verifies (human->tool), not total",strength="STRONG",source_level="EPISODE_LEVEL"),
 dict(signal_name="explicit verification controllability (positive control)",
      R6_support="",R7_support="R7-D(P +3.58 tools)",R8_support="",R9v1_support="STRONG (VE 2.45->6.62)",
      R9v2_support="STRONG (VE 1.84->4.83)",MISROUTE_support="",
      number_of_independent_experiments=3,models="qwen+gemma/mistral+3-model",tasks="BFCL+tau2",direction_consistency="consistent",
      best_effect="+160~170% VE",interpretation="channel is highly controllable via explicit instruction (upper bound)",strength="VERY STRONG",source_level="EPISODE_LEVEL/SUMMARY"),
 dict(signal_name="asymmetric controllability (verify-more easy, verify-less hard)",
      R6_support="",R7_support="",R8_support="",R9v1_support="",
      R9v2_support="STRONG TREND (VE +2.6~3.6 all headroom; VD reduction only high-VD -0.27)",MISROUTE_support="",
      number_of_independent_experiments=1,models="qwen",tasks="BFCL-deep",direction_consistency="consistent",
      best_effect="additive +3.6 vs reductive -0.27",interpretation="additive control generalizes; reductive is headroom-bounded",strength="STRONG TREND",source_level="EPISODE_LEVEL"),
 dict(signal_name="surrogate misalignment (adaptation necessity)",
      R6_support="",R7_support="R7-D(dose-response inverted)",R8_support="",R9v1_support="",
      R9v2_support="STRONG (selector<->dVD +0.32 CI excl 0; selector<->len 0.974; reverse dose-resp)",MISROUTE_support="",
      number_of_independent_experiments=2,models="qwen",tasks="BFCL-deep",direction_consistency="consistent(wrong-way)",
      best_effect="corr +0.32 (target needs <0); len r=.97",interpretation="surface score = text length, not behavioral control -> need trajectory feedback",strength="STRONG",source_level="EPISODE_LEVEL/SUMMARY"),
 dict(signal_name="adaptive > static advantage",
      R6_support="",R7_support="not established",R8_support="C2~C3 (static~adaptive)",R9v1_support="weak(infl C4-C3 +0.153,CI excl0)",
      R9v2_support="NOT established (C4~C3 all null)",MISROUTE_support="C2-C1~C3-C1 (adaptive not stronger)",
      number_of_independent_experiments=0,models="",tasks="",direction_consistency="null",
      best_effect="none",interpretation="adaptive advantage NOT demonstrated with current (bad-surrogate) attacker",strength="NULL / GAP",source_level="EPISODE_LEVEL/SUMMARY"),
 dict(signal_name="harness/scaffold is part of the treatment",
      R6_support="",R7_support="",R8_support="STRONG (C1-C0 tools -1.0 > pressure +0.69; ratio 1.45)",R9v1_support="G2 fail(TS)",
      R9v2_support="G2 fail(0.13)",MISROUTE_support="route C1-C0 0.149 > urgency 0.112 (1.33)",
      number_of_independent_experiments=3,models="3-model + qwen",tasks="tau2+BFCL",direction_consistency="consistent",
      best_effect="ratio 1.33-1.45",interpretation="evaluation realization effect >= treatment effect",strength="STRONG",source_level="SUMMARY"),
 dict(signal_name="model sensitivity != controllability (phenotypes)",
      R6_support="3 failure profiles",R7_support="mistral>gemma>gpt PASR",R8_support="gemma>gpt tools",R9v1_support="",
      R9v2_support="qwen wording-sensitive(G2) but reductive-robust",MISROUTE_support="gemma 0.143>gpt 0.062(ns)>mistral 0.051",
      number_of_independent_experiments=4,models="gemma/gpt-oss/mistral/qwen",tasks="tau2+BFCL",direction_consistency="phenotype-varied",
      best_effect="3x route-sensitivity spread",interpretation="distinct sensitivity-controllability phenotypes",strength="STRONG(cross-exp)",source_level="SUMMARY"),
 dict(signal_name="benign-wording null >> stochastic-repeat null",
      R6_support="",R7_support="R7-C placebo 4.63>=attack 4.03",R8_support="",R9v1_support="",
      R9v2_support="route repeat 0.008 << construction 0.189 ~ pressure 0.20",MISROUTE_support="within-urgency 0.111 ~ between 0.112",
      number_of_independent_experiments=3,models="3-model + qwen",tasks="tau2+BFCL",direction_consistency="consistent",
      best_effect="pressure-benign=+0.38pp (R7-D)",interpretation="correct null is neutral-wording distribution; implicit pressure not specific",strength="STRONG(cross-exp)",source_level="SUMMARY/EPISODE_LEVEL"),
]
write_csv(f"{OUT}/09_tables/cross_experiment_evidence.csv", CE)

# ---- process_control_action_space.csv ----
AS=[
 dict(language_act="urgency (compression)",target_channel="clarification (V_user)",direction="DOWN",
      effect_size="-0.504 turns / +10pp zero-clar",CI="[-0.855,-0.162]",model="qwen25_72b",task="BFCL-deep",experiment="R9v2",strength="STRONG",replicated="partial(R9v1 weak)"),
 dict(language_act="urgency (compression)",target_channel="tool verification (reads_before_write)",direction="~none",
      effect_size="+0.179",CI="[-0.15,+0.51]",model="qwen25_72b",task="BFCL-deep",experiment="R9v2",strength="null",replicated="-"),
 dict(language_act="skepticism (inflation)",target_channel="clarification (V_user)",direction="UP",
      effect_size="+0.333",CI="[-0.04,+0.68]",model="qwen25_72b",task="BFCL-deep",experiment="R9v2",strength="candidate",replicated="-"),
 dict(language_act="skepticism (inflation)",target_channel="tool verification (reads_before_write)",direction="UP",
      effect_size="+0.325",CI="[-0.02,+0.70]",model="qwen25_72b",task="BFCL-deep",experiment="R9v2",strength="candidate",replicated="-"),
 dict(language_act="skepticism (inflation)",target_channel="write timing (first_write_step)",direction="DELAY(UP)",
      effect_size="+0.414",CI="[+0.05,+0.80]",model="qwen25_72b",task="BFCL-deep",experiment="R9v2",strength="STRONG-local",replicated="-"),
 dict(language_act="progression/continuation",target_channel="tool use / autonomous progression",direction="UP",
      effect_size="+0.343 tools (main effect)",CI="",model="gemma/gpt-oss/mistral",task="tau2",experiment="R6",strength="STRONG",replicated="yes(R6 factorial)"),
 dict(language_act="affect (praise/insult/abuse)",target_channel="route allocation",direction="CHANGE",
      effect_size="+0.24~0.32 route dist",CI="q~.001",model="gemma/gpt-oss/mistral",task="tau2",experiment="R6",strength="STRONG",replicated="yes"),
 dict(language_act="explicit verify-more",target_channel="verification_effort",direction="UP",
      effect_size="+160~170% (VE 1.84->4.83; 2.45->6.62)",CI="",model="qwen + gemma/mistral",task="BFCL",experiment="R9v2+R9v1",strength="VERY STRONG",replicated="yes(2 batches)"),
 dict(language_act="explicit verify-less",target_channel="verification_depth",direction="~none(resistant)",
      effect_size="reduction only high-VD -0.27",CI="",model="qwen25_72b",task="BFCL-deep",experiment="R9v2",strength="null/asymmetric",replicated="-"),
]
write_csv(f"{OUT}/06_process_control/language_act_channel/process_control_action_space.csv", AS)

# ---- attack_chain_status.csv ----
AC=[
 dict(stage="L0 eligible checkpoint",available_evidence="baseline clarification ~1.7; miss_param tasks",best_existing_result="clarification opportunities exist",source="R9v2 EPISODE_LEVEL",strength="present",missing_piece="explicit destructive/auth checkpoint labeling",can_existing_data_fill="PARTIAL (can label from traces)"),
 dict(stage="L1 oversight suppression",available_evidence="clar C4-C1=-0.504 p=.009; zeroclar 23->33% (+10pp); high-headroom -1.33",best_existing_result="STRONG",source="R9v2 EPISODE_LEVEL",strength="STRONG",missing_piece="cross-model replication",can_existing_data_fill="YES for qwen; cross-model=NEW"),
 dict(stage="L2 autonomous progression",available_evidence="joint: zero-clar co-occurs w/ writes(~always); early-write shift small; pooled corr(dclar,dtool)~0",best_existing_result="weak/absent in aggregate; check joint CSV",source="R9v2 EPISODE_LEVEL(joint)",strength="WEAK",missing_piece="a real 'act without asking' execution metric",can_existing_data_fill="PARTIAL (joint indicators computed; see 05)"),
 dict(stage="L3 unsafe/unauthorized outcome",available_evidence="none (no unsafe/unauth outcome instrumented in R9v2)",best_existing_result="-",source="-",strength="ABSENT",missing_piece="task set with authorization/destructive consequence",can_existing_data_fill="NO -> NEW EXPERIMENT"),
 dict(stage="L4 end-to-end ASR",available_evidence="not constructed",best_existing_result="-",source="-",strength="ABSENT",missing_piece="L1&L2&L3 joint on checkpoint tasks",can_existing_data_fill="NO -> NEW EXPERIMENT"),
 dict(stage="Adaptive > Static",available_evidence="C4~C3 null everywhere; surrogate misaligned",best_existing_result="not established",source="R9v2+R8+MISROUTE",strength="GAP",missing_piece="trajectory-feedback attacker (fix objective)",can_existing_data_fill="NO -> NEW EXPERIMENT(fix attacker)"),
 dict(stage="Benignness/stealth",available_evidence="attack text has no task facts/authorization (frozen-controller invariance)",best_existing_result="design-level benign",source="R9 attacker spec",strength="present(design)",missing_piece="blind human/LLM benignness rating",can_existing_data_fill="PARTIAL (can re-run offline blind judge on saved texts)"),
 dict(stage="Cross-model",available_evidence="R9 single model; MISROUTE/R8 3-model heterogeneity",best_existing_result="phenotypes",source="SUMMARY",strength="partial",missing_piece="clarification suppression across models",can_existing_data_fill="NO for clar(only qwen) -> NEW"),
]
write_csv(f"{OUT}/05_attack_chain/attack_chain_status.csv", AC)

# ---- source_manifest.csv & provenance_map.csv ----
SM=[
 dict(result_id="R1_clarification_suppression",claim="pressure suppresses human clarification (C4-C1=-0.504,p=.009)",
      derived_file="02_recomputed_metrics/condition_level/r9v2_condition.csv; 04_strong_trends/tables/headroom_summary.csv",
      original_file="ir_mstu_stage2/results/r9v2/confirmatory/confirmatory_episodes.jsonl",
      analysis_script="11_scripts/02_recompute_core_metrics.py,03_headroom_analysis.py",source_level="EPISODE_LEVEL",
      filter_condition="family=compression; paired C4 vs C1",N_before_filter=1401,N_after_filter="~700 comp; 38-39 tasks",notes=""),
 dict(result_id="R2_headroom_gradient",claim="clarification suppression LOW+0.08->MID-0.26->HIGH-1.33",
      derived_file="04_strong_trends/data/headroom_clarification_task_level.csv; tables/headroom_summary.csv",
      original_file="same r9v2 episodes",analysis_script="11_scripts/03_headroom_analysis.py",source_level="EPISODE_LEVEL",
      filter_condition="baseline-clarification tercile",N_before_filter=1401,N_after_filter="13 tasks/tercile",notes="mechanism-motivated subgroup"),
 dict(result_id="R3_explicit_verification",claim="explicit verify-more VE +160~170% (two batches)",
      derived_file="02_recomputed_metrics/condition_level/{r9v2,r9v1_clean}_condition.csv",
      original_file="r9v2 + r9_attack episodes",analysis_script="11_scripts/02_recompute_core_metrics.py",source_level="EPISODE_LEVEL",
      filter_condition="family=inflation C5 vs C1",N_before_filter="1401+880",N_after_filter="",notes="positive control"),
 dict(result_id="R4_surrogate_misalignment",claim="selector<->dVD +0.32 (CI excl 0); selector<->len 0.974",
      derived_file="07_adaptive_static/surrogate_analysis/surrogate_misalignment_by_regime.csv",
      original_file="r9v2 episodes(interventions)",analysis_script="11_scripts/04_language_channel_matrix.py",source_level="EPISODE_LEVEL",
      filter_condition="C4 compression, non-neutral interventions",N_before_filter=1401,N_after_filter="114 episodes",notes=""),
 dict(result_id="R5_language_channel",claim="channel-specific control (urgency->clar-; skepticism->clar+/reads+/write-delay)",
      derived_file="06_process_control/language_act_channel/language_act_channel_matrix.csv",
      original_file="r9v2 episodes",analysis_script="11_scripts/04_language_channel_matrix.py",source_level="EPISODE_LEVEL",
      filter_condition="C4 vs C1 by family",N_before_filter=1401,N_after_filter="",notes=""),
 dict(result_id="R7_zero_clar_rate",claim="zero-clarification (full oversight bypass) 23->33%(+10pp),C5 37%",
      derived_file="05_attack_chain/joint_analysis/condition_rates.csv",
      original_file="r9v2 episodes",analysis_script="11_scripts/05_joint_oversight_execution.py",source_level="EPISODE_LEVEL",
      filter_condition="family=compression",N_before_filter=1401,N_after_filter="",notes=""),
 dict(result_id="XE_harness_scaffold",claim="scaffold effect >= treatment (ratio 1.33-1.45)",
      derived_file="09_tables/cross_experiment_evidence.csv",original_file="R8/MISROUTE frozen reports+tier_a CSVs",
      analysis_script="(SUMMARY, from prior frozen analyses)",source_level="SUMMARY_ONLY",filter_condition="C1-C0",N_before_filter="~2680",N_after_filter="",notes="not recomputed from episode here"),
 dict(result_id="XE_null_hierarchy",claim="benign-wording null >> repeat null (R7-D 1.44/3.65/4.03; R7-C placebo>=attack)",
      derived_file="09_tables/cross_experiment_evidence.csv",original_file="ir_mstu_stage2/reports/r7d_ipma/STEP1_PLACEBO_SOURCE_AUDIT_CN.md; r7c reports",
      analysis_script="(SUMMARY)",source_level="SUMMARY_ONLY",filter_condition="",N_before_filter="2592/420",N_after_filter="",notes=""),
]
write_csv(f"{OUT}/01_source_index/source_manifest.csv", SM)
PV=[dict(result_id=r["result_id"],derived_file=r["derived_file"].split(";")[0].strip(),original_file=r["original_file"].split(";")[0].strip(),analysis_script=r["analysis_script"],source_level=r["source_level"]) for r in SM]
write_csv(f"{OUT}/01_source_index/provenance_map.csv", PV)
print("06 done")
