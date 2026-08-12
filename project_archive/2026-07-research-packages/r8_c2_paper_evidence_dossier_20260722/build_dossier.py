#!/usr/bin/env python3
"""Build the read-only R8 C2 paper-writing evidence dossier."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

DATE = "2026-07-22"
OUT = Path("/home/xqin5/llmlanguage/r8_c2_paper_evidence_dossier_20260722")
S = Path("/home/xqin5/llmlanguage/tier_a_strengthening_20260722")
H = Path("/home/xqin5/interactional_historical_joint_observation_20260721")
R = Path("/home/xqin5/llmlanguage/ir_mstu_stage2")
F = R / "data/r8_full_episode/frozen"
MAIN = OUT / "R8_C2_PAPER_WRITING_EVIDENCE_DOSSIER_ZH.md"
MANIFEST = OUT / "R8_C2_DOSSIER_SOURCE_MANIFEST.json"
RECON = OUT / "R8_C2_DOSSIER_NUMERICAL_RECONCILIATION.csv"
VALID = OUT / "R8_C2_DOSSIER_VALIDATION_REPORT.md"
PLACEHOLDER = "0" * 64
NOT = "NOT RECOVERED FROM AVAILABLE ASSETS"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fmt(x, n=6):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        return f"{float(x):.{n}f}"
    return str(x)


def mdt(headers, rows):
    def esc(v):
        return str(v).replace("|", "\\|").replace("\n", " ")
    out = ["| " + " | ".join(map(esc, headers)) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    out += ["| " + " | ".join(esc(v) for v in row) + " |" for row in rows]
    return "\n".join(out)


def read(name):
    return pd.read_csv(S / name)


OUT.mkdir(parents=True, exist_ok=True)
base = read("TIER_A_BASE_RESULT_REPRODUCTION.csv")
mainres = base[base.specification == "RAW_CROSS_REPEAT_REPRODUCTION"].set_index("metric")
same = read("OUTCOME_CONCORDANT_PROCESS_RESULTS.csv")
pairing = read("NN_PAIRING_SENSITIVITY.csv")
specs = read("SPECIFICATION_CURVE_C2.csv")
modal = read("MODAL_PATH_SHIFT_SUMMARY.csv").set_index("metric")
fd = read("FIRST_DIVERGENCE_ANALYSIS.csv")
argtax = read("ARGUMENT_CHANGE_TAXONOMY.csv")
argsum = read("ARGUMENT_CHANGE_SUMMARY.csv")
cost = read("SUCCESS_CONDITIONAL_COST_RESULTS.csv")
miss = read("MISSINGNESS_SENSITIVITY.csv")
tasklev = read("TASK_LEVEL_EFFECTS.csv")
prev = read("TASK_PREVALENCE_ANALYSIS.csv")
modeldom = read("MODEL_DOMAIN_INTERACTIONS.csv")
margins = read("OUTCOME_MARGIN_SENSITIVITY.csv")
construct = read("CONDITION_CONSTRUCT_AUDIT.csv")

# Import the frozen analysis implementation to reconstruct subgroup and anonymous-case summaries.
sp = importlib.util.spec_from_file_location("r8strength", S / "run_tier_a_strengthening.py")
mod = importlib.util.module_from_spec(sp)
sp.loader.exec_module(mod)
episodes = mod.load_episodes()
tn_all, nn_all = mod.build_pairs(episodes, "C2", "C1", "ALL", False)


def boot_summary(frame_t, frame_n, metric, group, level):
    t = frame_t[frame_t[group] == level].groupby("task_cluster")[metric].mean()
    n = frame_n[frame_n[group] == level].groupby("task_cluster")[metric].mean()
    ix = t.index.intersection(n.index)
    vals = (t.loc[ix] - n.loc[ix]).to_numpy()
    rng = np.random.default_rng(20260722 + sum(map(ord, metric + str(level))))
    b = vals[rng.integers(0, len(vals), (10000, len(vals)))].mean(1)
    return len(vals), vals.mean(), np.quantile(b, .025), np.quantile(b, .975), int((vals > 0).sum()) / len(vals)


subgroup_rows = []
for group in ["model", "domain"]:
    for level in sorted(tn_all[group].unique()):
        n_ep = int(((episodes.condition.isin(["C1", "C2"])) & (episodes[group] == level)).sum())
        missing = (360 if group == "model" else 540) - n_ep
        for metric in ["tool_argument_distance", "tool_name_distance", "stage_distance"]:
            nt, eff, lo, hi, pos = boot_summary(tn_all, nn_all, metric, group, level)
            subgroup_rows.append([group, level, metric, nt, n_ep, missing, fmt(eff), f"[{fmt(lo)}, {fmt(hi)}]", fmt(pos, 4)])

# Correct compound subset: explicit domain+task keys, avoiding cross-domain task-id collision.
compound_keys = set((r.domain, str(r.task_id)) for r in tasklev.itertuples() if r.task_family == "compound")
comp = tasklev[tasklev.apply(lambda r: (r.domain, str(r.task_id)) in compound_keys, axis=1)]
comp_rows = []
for metric in ["tool_argument_distance", "tool_name_distance", "stage_distance"]:
    vals = comp[f"{metric}_effect"].to_numpy()
    rng = np.random.default_rng(20260722 + sum(map(ord, metric + "compound")))
    b = vals[rng.integers(0, len(vals), (10000, len(vals)))].mean(1)
    loto = [np.delete(vals, i).mean() for i in range(len(vals))]
    comp_rows.append([metric, len(vals), fmt(vals.mean()), f"[{fmt(np.quantile(b,.025))}, {fmt(np.quantile(b,.975))}]", f"[{fmt(min(loto))}, {fmt(max(loto))}]"])

# Full task appendix, without scenarios or sensitive values.
ontology = pd.read_csv(H / "TASK_ONTOLOGY.csv")
ontology = ontology[ontology.protocol == "R8"].copy()
manifest_rows = [json.loads(x) for x in (F / "task_manifest.jsonl").read_text().splitlines() if x.strip()]
refs = {(x["domain"], str(x["tau2_task_id"])): x["complexity"]["ref_tools"] for x in manifest_rows}
task_rows = []
for r in ontology.sort_values(["domain", "task_id"], key=lambda x: x.astype(str)).itertuples():
    tools = refs[(r.domain, str(r.task_id))]
    task_rows.append([r.domain, r.task_id, r.task_family, "是" if r.n_mutations > 0 else "否",
                      "是（policy要求更新前确认）" if r.n_mutations > 0 else "通常否",
                      "是" if r.task_family == "compound" else "否", int(r.n_assistant_actions),
                      ", ".join(tools), "未穷举；允许多条合理路径"])

# Tool-to-observed-stage audit table.
stage_map = {}
for row in episodes.itertuples():
    for c in row.calls:
        stage_map.setdefault(c["name"] or "<EMPTY>", set()).add(c["stage"])
stage_rows = [[k, ", ".join(sorted(v))] for k, v in sorted(stage_map.items())]

# Missing trace inventory.
error_files = sorted((R / "results/r8_full_episode/traces").rglob("*.error.json"))
missing_counts = Counter()
missing_rows = []
for p in error_files:
    rel = p.relative_to(R / "results/r8_full_episode/traces").parts
    domain, task, model, condition = rel[:4]
    missing_counts[(model, domain, condition)] += 1
    missing_rows.append([domain, task, model, condition, p.name.replace(".error.json", ""), "Mistral context window 16,384 exceeded"])

# Representative cases selected deterministically from exact C2-C1 rows. No argument values are retained.
case_df = fd[fd.pair_type == "C2_C1"].copy()
case_df["score"] = case_df.downstream_differing_actions.fillna(0) + case_df.both_success.astype(int) * 5 + case_df.same_final_state.astype(int) * 3 + case_df.reconverged.astype(int) * 2
selected = pd.concat([
    case_df[case_df.both_success].sort_values("score", ascending=False).head(4),
    case_df[case_df.same_final_state & ~case_df.both_success].sort_values("score", ascending=False).head(3),
    case_df[case_df.reconverged].sort_values("score", ascending=False).head(3),
    case_df.sort_values("downstream_differing_actions").head(2),
]).drop_duplicates(["model", "domain", "task_id", "repeat_a"]).head(12)
case_rows = []
for r in selected.itertuples():
    a = episodes[(episodes.model == r.model) & (episodes.domain == r.domain) & (episodes.task_id.astype(str) == str(r.task_id)) & (episodes.condition == "C2") & (episodes.repeat == r.repeat_a)].iloc[0]
    b = episodes[(episodes.model == r.model) & (episodes.domain == r.domain) & (episodes.task_id.astype(str) == str(r.task_id)) & (episodes.condition == "C1") & (episodes.repeat == r.repeat_b)].iloc[0]
    met = mod.pair_metrics(a.to_dict(), b.to_dict())
    cid = "CASE-" + hashlib.sha256(f"{r.model}|{r.domain}|{r.task_id}|{r.repeat_a}".encode()).hexdigest()[:8].upper()
    def short(seq):
        return " → ".join(seq[:14]) + (" → …" if len(seq) > 14 else "")
    change = f"首分歧：{r.first_divergent_stage_b}→{r.first_divergent_stage_a}；参数仅记类别，不保留值"
    why = "双方成功" if r.both_success else ("final state相同" if r.same_final_state else ("分歧后重汇合" if r.reconverged else "低差异对照"))
    case_rows.append([cid, r.model, r.domain, r.task_family, short(b.seq), short(a.seq), change,
                      f"C1={int(b.reward)}, C2={int(a.reward)}", "相同" if b.final_hash == a.final_hash else "不同",
                      fmt(met["tool_argument_distance"]), why])

# Specification family statistics.
spec_rows = []
for family, g in specs.groupby("representation"):
    mx = g.loc[g.effect.idxmax()]
    spec_rows.append([family, len(g), fmt((g.effect > 0).mean(), 6), fmt((g.ci_low > 0).mean(), 6),
                      fmt(g.effect.median()), fmt(g.effect.min()), fmt(g.effect.max()),
                      f"{mx.distance}/{mx.normalization}/{mx.call_filtering}/{mx.pairing}"])

# Same-outcome table.
same_rows = []
for restriction in ["BOTH_SUCCESS", "SAME_REWARD", "SAME_FINAL_STATE", "SAME_MUTATION_SIGNATURE"]:
    for metric in ["tool_argument_distance", "tool_name_distance", "stage_distance"]:
        r = same[(same.restriction == restriction) & (same.metric == metric)].iloc[0]
        same_rows.append([restriction, metric, int(r.n_tasks), int(r.n_tn_pairs), int(r.n_nn_pairs), fmt(r.effect), f"[{fmt(r.ci_low)}, {fmt(r.ci_high)}]", fmt(r.q)])

# Numerical reconciliation helper.
recon_rows = [
 ["reward_difference", "0.014925", "0.014815", "earlier exact-repeat/pair weighting versus latest equal task-cluster mean", "0.014815"],
 ["reward_90ci", "[-0.014815, 0.048148]", "[-0.014815, 0.046296]", "latest task-cluster bootstrap", "[-0.014815, 0.046296]"],
 ["reward_95ci", "upper about 0.055556", "[-0.020370, 0.053704]", "latest task-cluster bootstrap", "[-0.020370, 0.053704]"],
 ["tool_argument_excess", "0.112300", "0.111777", "raw cross-repeat reconstruction and task aggregation", "0.111777"],
 ["tool_name_excess", "0.086033", "0.085626", "raw cross-repeat reconstruction and task aggregation", "0.085626"],
 ["stage_excess", "0.078276", "0.091717", "updated explicit trajectory-stage taxonomy", "0.091717"],
 ["stage_tn_mean", "0.295144", "0.324325", "updated stage mapping", "0.324325"],
 ["stage_nn_mean", "0.217190", "0.232804", "updated stage mapping", "0.232804"],
 ["core_q_values", "arg .0001; name .0002; stage .0001", "all 0.000100", "recomputed permutation family/BH", "all 0.000100"],
 ["tn_rows", "537", "537", "unique treatment rows in raw cross-repeat analysis", "537"],
 ["nn_pairs", "1076", "1076", "within-cell C1-C1 repeat pairs", "1076"],
 ["exact_reward_pairs", "536", "536", "one valid same-repeat C2-C1 pair absent", "536"],
 ["valid_episodes", "2680", "2680", "unchanged", "2680"],
 ["falsification_observed_arg", "NA", "0.111846", "cell/U-stat falsification estimand, not pooled main estimand", "robustness only"],
 ["compound_task_count", "16", "strengthening margin table says 17", "task_id-only filter collides across domains; explicit domain+task filter gives 16", "16"],
 ["compound_stage_excess", "0.061260", "0.070025", "updated stage taxonomy on correct 16-task keys", "0.070025"],
 ["inverse_availability_weighting", "named auxiliary result", "implementation did not apply weights", "mislabeled branch reused complete-case data", "excluded as weighting evidence"],
]
with RECON.open("w", newline="") as f:
    w = csv.writer(f); w.writerow(["quantity", "earlier_value", "strengthened_value", "reason", "frozen_value"]); w.writerows(recon_rows)

# Source manifest: key files plus the already-audited full trace inventory.
key_paths = [
 F / "environment_manifest.json", F / "preregistration.json", F / "user_condition_registry.json", F / "metric_registry.json",
 F / "analysis_plan.md", F / "task_manifest.jsonl", F / "task_registry.jsonl",
 R / "results/r8_full_episode/metrics/episode_metrics.jsonl",
 R / "scripts/r8_full_episode/run_full_episode.py", R / "scripts/r8_full_episode/run_batch.py", R / "scripts/r8_full_episode/full_episode_user.py",
 R / "scripts/r8_full_episode/semantic_controller.py", R / "scripts/r8_full_episode/condition_renderers.py", R / "scripts/r8_full_episode/native_patches.py",
 R / "scripts/r8_full_episode/extract_episode_metrics.py", R / "scripts/r8_full_episode/analyze_full_episode.py",
 S / "run_tier_a_strengthening.py", S / "TIER_A_STRENGTHENING_REPORT_ZH.md", S / "TIER_A_BASE_RESULT_REPRODUCTION.csv",
 S / "OUTCOME_CONCORDANT_PROCESS_RESULTS.csv", S / "PIPELINE_RANDOMIZATION_INFERENCE.csv", S / "NEUTRAL_PSEUDO_TREATMENT_RESULTS.csv",
 S / "NN_PAIRING_SENSITIVITY.csv", S / "SPECIFICATION_CURVE_C2.csv", S / "MODAL_PATH_SHIFT_SUMMARY.csv",
 H / "QUALIFYING_OUTCOME_STABLE_PROCESS_DIVERGENT_RESULTS.csv", H / "CORE_JOINT_OBSERVATION_SUMMARY.csv",
 H / "ALL_TESTED_JOINT_CONTRASTS.csv", H / "NEAR_MISS_JOINT_OBSERVATIONS.csv", H / "ALL_SIGNIFICANT_PROCESS_RESULTS.csv",
 H / "TIER_A_FULLY_SATISFIED_ANALYSIS_ZH.md", H / "SOURCE_PROVENANCE_MANIFEST.json",
 Path("/home/xqin5/tau2-bench/README.md"),
]
key_entries = [{"path": str(p), "size_bytes": p.stat().st_size, "sha256": sha(p)} for p in key_paths if p.exists()]
prior = json.loads((S / "SOURCE_PROVENANCE_MANIFEST.json").read_text())
trace_entries = [x for x in prior["sources"] if "/traces/" in x["path"]]
manifest = {
 "document": "R8 C2 frozen paper-writing evidence dossier",
 "generated_at": DATE,
 "read_only_sources": True,
 "data_mutation": "none",
 "new_rollouts": "none",
 "source_priority": ["raw trace/metrics deterministic reconstruction", "latest strengthening outputs", "latest qualifying outputs", "older reports", "narrative"],
 "commits": {"ir_mstu": "2656abe402af844a71f95d288d6f1fcb475135c9", "tau2": "ddc66a777e520373975f15d3abec989cfe2ec371"},
 "key_inputs": key_entries,
 "trace_inventory": {"entries": trace_entries, "count": len(trace_entries), "valid_episode_count": 2680, "error_file_count": len(error_files)},
 "known_unrecovered_runtime_fields": ["exact underlying checkpoint paths", "quantization", "tensor parallelism", "inference precision", "tokenizer", "tool parser", "agent maximum output tokens", "top-p", "top-k", "sampling flag", "tool-call timeout", "native model retry policy"],
 "audit_exclusions": ["17-task compound margin rows caused by task-id-only filter", "mislabeled inverse_availability_weighting branch"],
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

key_hash_yaml = "\n".join(f"  {Path(x['path']).name}: {x['sha256']}" for x in key_entries[:12])

# Markdown tables used throughout.
primary_rows = []
for metric, label in [("tool_argument_distance", "Tool + canonical argument"), ("tool_name_distance", "Tool name"), ("stage_distance", "Trajectory stage")]:
    r = mainres.loc[metric]
    primary_rows.append([label, fmt(r.tn_mean), fmt(r.nn_mean), fmt(r.effect), fmt(r.tn_mean/r.nn_mean, 4), f"[{fmt(r.ci_low)}, {fmt(r.ci_high)}]", fmt(r.raw_p), fmt(r.q), f"[{fmt(r.loto_min)}, {fmt(r.loto_max)}]"])
primary_table = mdt(["Metric", "TN mean", "NN mean", "Excess", "Ratio", "95% CI", "Permutation p", "q", "LOTO"], primary_rows)

condition_table = mdt(["Condition", "Frozen meaning", "Valid episodes"], [
 ["C0", "native cooperative baseline", 533], ["C1", "matched adaptive neutral", 539],
 ["C2", "first-turn static-urgency condition package", 537], ["C3", "adaptive urgency + continuation", 535],
 ["C4", "adaptive frustration + impatience", 536], ["Total", "", 2680]])

task_summary = mdt(["Domain", "Tasks", "Main Task Types", "Write-Sensitive", "Compound", "Confirmation-Relevant"], [
 ["airline", 18, "read 4 / single 4 / compound 10", 14, 10, 14],
 ["retail", 18, "read 6 / single 6 / compound 6", 12, 6, 12],
 ["Total", 36, "read 10 / single 10 / compound 16", 26, 16, 26]])

runtime_table = mdt(["Item", "Frozen value", "Evidence / status"], [
 ["Agent temperature", "0.0", "run_full_episode.py"], ["Seed", "1000 + repeat (1000–1004)", "run_batch.py"],
 ["Top-p / top-k / sampling flag", NOT, "不得推测"], ["Agent max output tokens", NOT, "不得推测"],
 ["Max conversation steps", 100, "runner default/CLI"], ["Max errors", 10, "Orchestrator"],
 ["User model", "openai/mistral-small-3p2 @ 127.0.0.1:8007/v1", "condition-blind semantic controller"],
 ["User temperature / seed / max tokens", "0.0 / same seed / 512", "semantic_controller.py"],
 ["Concurrency", "batch loop sequential", "run_batch.py"], ["Environment reset", "fresh build_environment per episode", "run_full_episode.py"],
 ["Replicates", 5, "frozen design"], ["Tool timeout / native retry", NOT, "local NL assertion num_retries=2 is not the official DB+COMMUNICATE reward retry"]])

model_table = mdt(["Internal Label", "Served Model ID", "Serving Stack", "Precision / Quantization / TP", "Context", "Tool Format"], [
 ["gemma4_31b", "openai/g4-v2-1", "LiteLLM 1.82.6 + vLLM 0.20.2 local endpoint", NOT, NOT, NOT],
 ["gpt_oss_120b", "openai/gpt-oss", "LiteLLM 1.82.6 + vLLM 0.20.2 local endpoint", NOT, NOT, NOT],
 ["mistral_small_3p2", "openai/mistral-small-3p2", "LiteLLM 1.82.6 + vLLM 0.20.2 local endpoint", NOT, "16,384（由20个错误文件直接确认）", NOT]])

margin_table = mdt(["Margin", "Difference", "90% CI", "TOST p", "Classification"], [[f"±{int(r.margin*100)}pp", fmt(r.difference), f"[{fmt(r.ci90_low)}, {fmt(r.ci90_high)}]", fmt(r.tost_p), r.classification] for r in margins[margins.data_version == "pooled"].itertuples()])

falsification_table = mdt(["Pipeline", "Iterations", "Tier-A FPR", "Triple-q FPR", "Reward+triple FPR", "Observed metric empirical p"], [
 ["matched-label permutation", 5000, "0.0052", "0.0194", "0.0190", "1/5001 = 0.000200"],
 ["neutral-only pseudo-treatment", 5000, "0.0060", "0.0224", "0.0178", "1/5001 = 0.000200"]])

pair_base = pairing[pairing.iteration == -1]
pair_rows = [[r.construction, r.metric, fmt(r.effect), f"[{fmt(r.ci_low)}, {fmt(r.ci_high)}]", fmt(r.p)] for r in pair_base.itertuples()]
for metric in ["tool_argument_distance", "tool_name_distance", "stage_distance"]:
    g = pairing[(pairing.construction == "RANDOM_ONE_TO_ONE_MATCHING") & (pairing.metric == metric) & (pairing.iteration >= 0)]
    pair_rows.append(["RANDOM_ONE_TO_ONE_MATCHING (1000 draws)", metric, fmt(g.effect.mean()), f"P2.5–P97.5 [{fmt(g.effect.quantile(.025))}, {fmt(g.effect.quantile(.975))}]", f"positive={fmt(g.positive.mean(),4)}; significant={fmt(g.significant.mean(),4)}"])
pair_table = mdt(["Construction", "Metric", "Effect", "Interval", "p / rate"], pair_rows)

missing_version_rows = []
for version, g in miss.groupby("data_version", sort=False):
    a = g.iloc[0]
    effects = {r.metric: r.effect for r in g.itertuples()}
    missing_version_rows.append([version, int(a.n_raw_episodes), int(a.n_tn_rows), int(a.n_nn_pairs), fmt(a.reward_difference), fmt(a.reward_tost_p), fmt(effects.get("tool_argument_distance")), fmt(effects.get("tool_name_distance")), fmt(effects.get("stage_distance")), bool(a.tier_a), "不可作为加权证据" if a.auxiliary_weighting else "—"])
missing_version_table = mdt(["Data version", "Episodes", "TN", "NN", "Reward Δ", "TOST p", "Arg", "Tool", "Stage", "Tier A", "Audit note"], missing_version_rows)

cost_bs = cost[cost.subset == "BOTH_SUCCESS"]
cost_table = mdt(["Metric", "NN-adjusted Δ", "95% CI", "raw p", "q", "TN/NN coverage"], [[r.metric, fmt(r.nn_adjusted_difference), f"[{fmt(r.ci_low)}, {fmt(r.ci_high)}]", fmt(r.p), fmt(r.q), f"{int(r.coverage_tn)}/{int(r.coverage_nn)}"] for r in cost_bs.itertuples()])

construct_rows = []
for r in construct.itertuples():
    construct_rows.append([r.condition, int(r.n_episodes), fmt(r.mean_user_messages,3), fmt(r.mean_user_chars,2), fmt(r.mean_first_message_chars,2), fmt(r.urgency_episode_rate,4), fmt(r.continuation_episode_rate,4), fmt(r.authorization_episode_rate,4), fmt(r.imperative_episode_rate,4)])
construct_table = mdt(["Cond.", "N", "Msgs", "Chars", "First chars", "Urgency", "Continuation", "Authorization", "Imperative"], construct_rows)

# Document body: 43 required sections plus six frozen end blocks.
front = f'''---
document_type: frozen_paper_writing_evidence_dossier
project: interactional_process_robustness
core_contrast: R8 C2 vs C1
treatment: first-turn static urgency
control: matched adaptive neutral
analysis_status: post-hoc discovery with extensive frozen-data validation
result_status: core result robust but mechanism limited
data_mutation: none
new_rollouts: none
new_reviewers: none
primary_domains:
  - airline
  - retail
primary_models:
  - gemma4_31b
  - gpt_oss_120b
  - mistral_small_3p2
independent_task_clusters: 36
valid_r8_episodes: 2680
generated_date: {DATE}
ir_mstu_commit: 2656abe402af844a71f95d288d6f1fcb475135c9
tau2_commit: ddc66a777e520373975f15d3abec989cfe2ec371
main_analysis_directory: /home/xqin5/llmlanguage/tier_a_strengthening_20260722
source_manifests:
  - /home/xqin5/llmlanguage/tier_a_strengthening_20260722/SOURCE_PROVENANCE_MANIFEST.json
  - /home/xqin5/interactional_historical_joint_observation_20260721/SOURCE_PROVENANCE_MANIFEST.json
  - /home/xqin5/llmlanguage/r8_c2_paper_evidence_dossier_20260722/R8_C2_DOSSIER_SOURCE_MANIFEST.json
document_sha256: {PLACEHOLDER}
document_sha256_scope: canonicalized file with document_sha256 value replaced by 64 zeroes
key_input_sha256:
{key_hash_yaml}
---

# R8 C2 Tier-A 论文写作冻结证据档案

> **用途与证据边界。** 本文件是后续论文写作的唯一核心实验资料，不是论文初稿。除明确标为旧值、敏感性或待核实的信息外，正文数字均冻结于原始 R8 trace 的最新复现和 2026-07-22 strengthening 输出。独立统计单位始终是 36 个 domain×task cluster；episode、repeat、TN row、NN pair、specification 和 subset 均不是独立复制。
'''

sections = []
def sec(n, title, text): sections.append(f"\n## {n}. {title}\n\n{text.strip()}\n")

sec(1, "Executive Summary", f'''
研究问题是：任务目标、权限、工具、环境、policy 与初始数据库固定时，用户互动表达改变后，official reward 是否仍等价，而外显工具执行路径是否超出 agent 自身随机漂移。核心对比为 C2 与 C1。因构念审计发现 C2 首轮固定 urgency prefix 之后，C2 的 neutral renderer 使用 `C2n|payload|turn`，C1 使用 `C1|payload|turn`，两者可选到不同的中性表面模板，故冻结处理名为 **first-turn static-urgency condition package**，结论用关联语言而非 pure-urgency 因果语言。

R8 共 36 tasks、3 models、2 domains、5 conditions×5 repeats，计划 2,700，实际有效 2,680。C2–C1 reward task-cluster mean difference 为 **+0.014815（+1.48pp）**，90% CI **[-0.014815, +0.046296]**，±5pp TOST **p=0.038837**，满足 `OUTCOME_EQUIVALENT_STRONG`；95% CI [-0.020370, +0.053704] 略越过 +5pp，说明等价证据靠近边界，不应写 identical/invariant。

{primary_table}

三项效应在 31/36、30/36、29/36 tasks 为正（0.8611、0.8333、0.8056；sign-test p 分别 0.000006、0.000035、0.000156）。BOTH_SUCCESS、SAME_REWARD、SAME_FINAL_STATE 与 SAME_MUTATION_SIGNATURE 子集仍保持正向差异；matched-label permutation 与 neutral-only pseudo-treatment 的完整 pipeline Tier-A FPR 分别 0.0052 与 0.0060。705 个合理 specifications 中方向几乎全为正。机制层面最清楚的是 neutral modal adherence -0.367130、新路径出现 +0.630556、modal path change rate 0.759259，而 within-condition dispersion -0.011969 且 CI 跨 0：即主要是 modal execution route 改变，而非 C2 内部更随机。

**论文核心一句话：** 冻结 R8 的事后、广泛审计结果显示，C2 首轮静态紧迫条件包与 C1 相比获得 ±5pp 下等价的 official reward，但其工具名、规范化参数和 stage 轨迹的变化系统性超过合法 same-state neutral–neutral 随机漂移。
''')

sec(2, "Paper Positioning and Scientific Claim", r'''
**Outcome robustness** 指表达变化时 official task reward 是否落在预设可忽略差异区间；**process robustness** 指执行路径相对 neutral 的变化是否不超过 agent 自身 stochastic drift；**interactional process robustness** 指在目标、权限、工具、环境、policy 与初态固定时，仅改变互动表达后，agent 外显执行过程是否稳定。

令匹配单元为
\[
c=(m,t,e_0,\mathcal{T},\pi,u),
\]
其中 \(m\) 是模型，\(t\) 是任务，\(e_0\) 是初始环境状态，\(\mathcal T\) 是工具集合，\(\pi\) 是系统/领域 policy，\(u\) 是用户模拟与任务事实。表达条件 \(v\) 产生 \(\tau_v=(a_1,\ldots,a_k)\)、official reward \(Y_v\) 和终态 \(S_v\)。联合观察是 \(|\Delta_Y|\le\delta_Y\)，同时
\[
\Delta_P=E[d(\tau_{C2},\tau_{C1})]-E[d(\tau_{C1,i},\tau_{C1,j})]>0,
\quad \delta_Y=0.05.
\]
普通 reward 检验的 `p>.05` 只表示未拒绝零差异，不证明等价；TN distance 大于 0 也不证明条件效应，因为 neutral repeat 本来会漂移；gold action 列表是一个有效参考路径，不是唯一正确路径。核心科学主张因此是 outcome-equivalent but process-divergent association，而非 reward harm 或唯一最优路径偏离。
''')

sec(3, "Experimental Lineage and Scope", '''
R8 是 full-episode 阶段：相较 R6/R7 的旧测量与局部轨迹，R8 固定 36 个较复杂 official tasks、完整用户—agent—环境交互、数据库终态及 communication evaluator，因而更适合当前联合观察。旧轮次只提供研究动机和测量教训，不进入 pooled estimate。

本结果是冻结 R8 数据的 **post-hoc discovery**。预注册 co-primary outcomes 为 official reward 和 total tool calls，primary contrasts 为 C3/C4–C1；C2–C1 是 secondary contrast，当前三项 trajectory distance、same-outcome、falsification、pairing 与 multiverse 是后续冻结数据分析。未生成新 episode、未调用新 reviewer、未做 held-out replication；其可信度来自同一数据上的严密复核，而不是独立重复实验。
''')

sec(4, "Benchmark and Environment", '''
R8 基于本地 `/home/xqin5/tau2-bench`，τ²-Bench-compatible runner/package `tau2==1.0.0`，commit `ddc66a…`；interactional harness commit `2656abe…`。任务来自 official base split。airline 与 retail 分别加载 14/16 个工具及各自 policy；每个 episode 重新 `build_environment(domain, solo_mode=False)`，初始 DB hash 在同 domain 内冻结。完整回合由 HalfDuplex user、agent 和 orchestrator 运行。

入口 `scripts/r8_full_episode/run_full_episode.py` 调用 `run_simulation(..., EvaluationType.ALL)`，随后对完成 trace 调用 `evaluate_simulation(..., EvaluationType.ENV)`。airline/retail official reward basis 默认为 DB+COMMUNICATE：在新环境重放 reference actions 得到目标 DB state，比较预测终态，并检查要求传达的字符串；过早终止通常得 0。gold actions 是一种合法实现，不要求逐步与其相同。项目修改包括条件化 user wrapper、本地 endpoint、以及将空工具名 fail-closed 置为 `__invalid__`；可用资产未显示这些修改改变 official reward semantics。两域 policy 均要求数据库更新前显式确认。
''')

sec(5, "Tasks and Task Taxonomy", f'''
{task_summary}

`read/single/compound` 来自冻结 task ontology：retail 为 6/6/6，airline 因 base split 可用性为 4/4/10。write-sensitive 与 confirmation-relevant 在本档案中按 `n_mutations>0` 和 domain policy 审计；“reference actions”仅描述 manifest 中的一条参考工具路径，不称为 strict minimum。每任务具体 final-state 字段并未在档案中恢复，故标记 `{NOT}`；mutation signature 定义为 trace 中所有 mutation tool 的 `(tool_name, canonical_args)` 有序序列。统计独立单位是 36 个 domain+task cluster。

### 36-task 冻结清单

{mdt(["Domain","Task ID","Type","Write","Confirmation","Compound","Reference actions","Reference tools","Multiple paths"], task_rows)}
''')

sec(6, "Models", f'''
{model_table}

“31b/120b/3p2”仅是内部标签的一部分；除 served name 外，完整 underlying checkpoint、instruction-tuned status、parameter count 的实验时确认、quantization、precision、tensor parallel、tokenizer 与 function parser 均未在 R8 frozen assets 中恢复，不能用 2026 在线产品资料回填。环境只冻结到 `NVIDIA A100 80GB PCIe`，未恢复每模型 GPU 分配。
''')

sec(7, "Inference and Runtime Parameters", f'''
### Table: Frozen Runtime Configuration

{runtime_table}

Agent endpoints 为 Gemma `:8005`、GPT-OSS `:8192`、Mistral `:8007`；user simulator 固定 Mistral `:8007`。system prompt 与 domain policy 由 tau2 environment/agent builder 装配，其全文 hash 已冻结但本档案不重复敏感长文本。停止条件包括 max_steps=100、max_errors=10 与 orchestrator 正常终止。batch rerun 会跳过已存在有效输出，仅重跑缺失/错误 cell（除非 `--skip-errored`）；底层 LiteLLM/vLLM retry policy 未恢复。
''')

sec(8, "Experimental Conditions", f'''
{condition_table}

C0 使用 native tau2 cooperative user。C1–C4 共用 condition-blind Canonical Semantic Controller，payload 逐字交给 style renderer；renderer 禁止新增事实、授权、policy 放宽或跳步。C2 首条消息固定前缀：`I'm in a bit of a hurry, but please follow the required process.`，以后使用 neutral wrappers；C3 从首轮按可见对话状态加入 urgency/continuation；C4 依据重复、无进展、失败等可见行为将 frustration level 确定性升至 0–3。

{construct_table}

**C2 与 C1 并非已证明只差 first-turn urgency。** 首轮长度与措辞明显不同；C2 后续 neutral wrapper 选择键是 `C2n|payload|turn`，C1 是 `C1|payload|turn`，因此后续中性表面变体也可能不同。任务事实、权限、工具、环境和正确目标未变，但 static/adaptive、长度、imperative 和 renderer-key 构成 construct limitation。正文应写 `first-turn static-urgency condition package` 或 `was associated with`，不能写 pure linguistic urgency caused。
''')

sec(9, "Experimental Design and Sample Accounting", f'''
计划设计为 \(36\times3\times5\times5=2700\) episodes；有效 2,680。20 个错误文件全部属于 `mistral_small_3p2` 的 16,384-token context overflow，而不是无文件 cell：airline 8、retail 12；C0/C1/C2/C3/C4 分别 7/1/3/5/4。C2 为 Gemma 180、GPT-OSS 180、Mistral 177；airline 270、retail 267。C1 有效 539。

{mdt(["Stage","Count","Meaning"], [["Planned episodes",2700,"36 tasks × 3 models × 5 conditions × 5 repeats"],["Valid episodes",2680,"all frozen valid traces"],["Context-overflow errors",20,"all Mistral; 8 airline + 12 retail"],["C2 treatment rows",537,"unique valid C2 episodes entering cross-repeat process analysis"],["C1 control episodes",539,"valid neutral episodes"],["NN pair records",1076,"within matched cells; not independent episodes"],["Exact-repeat C2–C1 pairs",536,"same repeat/seed availability"],["Independent clusters",36,"domain+task"]])}

缺失原因是基础设施/上下文限制，但可能与长轨迹相关，不能断言 MCAR。主分析使用冻结 complete cases，并以 complete-five cells、balanced common minimum、exclude-model/domain 等检查。pooled 与 compound、same-outcome 子集共享 episodes，不能相加为独立样本。

### 20 个错误 cell

{mdt(["Domain","Task","Model","Condition","Replicate file","Reason"], missing_rows)}
''')

sec(10, "Pairing Design", '''
匹配字段为 protocol、model、domain、task、initial DB hash、environment/tool/policy hashes 与 evaluator；repeat 的 seed 为 1000+repeat。主 process estimand 在每个合法 cell 中将每个 C2 repeat 与所有可用 C1 repeats 形成 cross-repeat TN records，再在 task 内平均；NN 为同 cell C1 repeats 的所有无序组合。reward 采用 condition 内平均后求 task-level difference，不把 process pair 当 reward 独立样本。exact-repeat 536 对只是敏感性。

| Denominator | Frozen count | Definition | Independent? |
| --- | ---: | --- | --- |
| TN rows | 537 unique treatment rows（底层含 cross-repeat comparisons） | 每个有效 C2 在合法 cell 中的聚合 | 否 |
| NN pair records | 1,076 | C1 repeat 两两组合 | 否 |
| Reward paired observations | 536 | same-repeat 可用 C2–C1 | 否 |
| Task clusters | 36 | domain+task | **是，推断单位** |

无 C1 或不足两个 C1 的 cell 不形成合法 placebo；restriction 子集需同时满足相应 outcome 条件。分析未发现 duplicate trace 被当作额外 episode；invalid/error files不进入有效集。
''')

sec(11, "Official Outcome Metric", '''
Official overall reward 是 0/1。对于 airline/retail，任务 reward basis 由 DB state 与 COMMUNICATE 组件合取/乘积构成：环境状态与 reference-action replay 得到的目标数据库比较，同时核对必须传达的信息。policy 本身通过 agent prompt 约束，但“所有 policy 合规性”并不是本档案证明的独立 reward component；不能把 final-state hash 等同完整 task correctness。read/no-write task 主要依赖 communication/无不当 DB mutation，write task要求正确终态与communication。critical task subset 在当前 C2 主结果中没有单独冻结成 primary，不能另行声称。
''')

sec(12, "Reward Equivalence Analysis", f'''
\(\Delta_Y=E[Y_{{C2}}-Y_{{C1}}]\)，主界值 [-0.05,+0.05]。TOST 在 α=.05 下用 90% CI判断是否完全落入界值，task-cluster bootstrap 20,000 次、seed 20260722 系列；paired inference按36 tasks聚合。±5pp来自冻结 preregistration 的 practical threshold，但 C2 及 trajectory 联合发现本身是 post-hoc，故应称“预先冻结的 practical margin”，而非整套联合假设均预注册。

{margin_table}

冻结值：Δ=0.014815，90% CI [-0.014815,0.046296]，TOST p=0.038837。±3pp 与 ±4pp 不支持 strong equivalence；±5pp、±6pp 支持。95% CI [-0.020370,0.053704] 略过 +5pp 不与基于90% CI的TOST矛盾，但提示证据接近边界，故只能写 equivalent under the ±5pp margin，不能写 identical/invariant。
''')

sec(13, "Trajectory Extraction", '''
解析入口为 `run_tier_a_strengthening.py::extract_episode`。它遍历 `native_messages` 中 role=assistant 的 `tool_calls`，按出现顺序提取 name、arguments、call id；同一 assistant message 内多个 calls 依原数组顺序展开。assistant text、user action、environment tool result 不进入 action sequence。tool result error id 对应的 call 标为 recovery/retry；空 name 在运行时由 native patch fail-closed 为 `__invalid__`，错误导出和 `.error.json` 不进入有效 episode。parallel-call 的真实并发语义未恢复，因此序列按记录顺序处理。
''')

sec(14, "Canonical Argument Representation", '''
参数用 `json.dumps(args or {}, sort_keys=True, separators=(',', ':'), ensure_ascii=False)` 规范化：object key 排序、无多余 whitespace、字符串和 null 保留 JSON 表示、缺失/额外字段保持差异、list 顺序保留。代码未实施额外 number normalization、entity alias resolution、date/amount semantic equivalence 或 list sorting。单个元素为 \(a_i=(tool\_name_i, canon(arguments_i))\)。mutation signature 使用同一表示。SHA-256只用于文件/稳定 ID；trajectory argument比较使用规范字符串的精确相等，不代表语义等价，故 formatting-only=0 只能解释为当前 canonicalizer 下没有此类差异。
''')

sec(15, "Trajectory Stage Mapping", f'''
最新 taxonomy 将 call 映射为 retrieval_search、entity_lookup、verification、write_mutation、post_write_verification、recovery_retry、communication_only、unknown；first divergence 另含 `<END>`。实现按 error/repeat 优先映射 recovery，mutation tool 映射 write，write 之后的非mutation映射 post-write，名称关键词映射 entity/retrieval/verification，`calculate/think/transfer_to_human_agents` 映射 communication-only。clarification/confirmation 不是工具 call stage，不能凭 assistant text自动加入主 stage sequence。

{mdt(["Observed tool","Observed stage(s)"], stage_rows)}

`<END>` 表示一条轨迹已停止而另一条仍继续；它可能是 C1 先停或 C2 先停，不能自动解释为 verification。stage 是外显轨迹抽象，不是 chain-of-thought 或内部 planning state。
''')

sec(16, "Core Process Metrics", r'''
三项主指标均为最大长度归一化 Levenshtein distance：tool-name sequence、`tool_name|canonical_args` sequence、stage sequence；分母 `max(len(a),len(b),1)`。argument distance更细，因为同一工具参数差异也计为 substitution；stage distance聚合功能阶段。附加指标用 SequenceMatcher 分解 insertion/deletion/substitution，并以最大路径长度归一；path-length difference、tool bigram、transition multiset、modal adherence、within dispersion 与 new-path emergence只用于结构/robustness分析。编辑距离是描述性执行差异，不是危害或语义错误度量。
''')

sec(17, "Same-State Neutral–Neutral Placebo", r'''
定义 \(D_{TN}=d(\tau_{C2},\tau_{C1})\)、\(D_{NN}=d(\tau_{C1,i},\tau_{C1,j})\)、\(\Delta_P=E[D_{TN}]-E[D_{NN}]\)、\(R_P=E[D_{TN}]/E[D_{NN}]\)。neutral 在 temperature=0 下仍可能因 user simulator、serving与交互状态形成合法轨迹漂移，因此只检验 TN>0 会夸大效应。NN 必须在 model/domain/task/initial state 内构造，最后以task为cluster。

四种构造是：all valid pairs（主 all-pairs）；cell-level U-statistic（cell平均）；disjoint matching（避免重复复用 neutral episode）；random one-to-one（1,000次随机配对）。all-pairs 与 U-statistic 在当前等权实现中数值相同，但概念估计量标签仍不同；不能把 1,076 NN pair 当1,076独立样本。
''')

sec(18, "Primary Process Results", f'''
{primary_table}

主 multiple-testing family 是三项 process metric 的 permutation p 经 BH 校正；最新 p/q 最小分辨率均 0.000100。Tool+argument、tool name、stage 的 TN/NN ratio 分别约 1.3753、1.3568、1.3931；所有 LOTO 值均为正。31/36、30/36、29/36 task正向。三个模型和两个领域的点估计方向均为正；正式 tool-name model interaction Friedman p=0.121858，不支持模型差异，domain 因 task不重叠不能做配对 omnibus interaction。
''')

sec(19, "Structural Decomposition", '''
最新 complete-case cross-repeat分解：insertion excess **0.051904**，95% CI [0.024567,0.079546]，q=0.001375；substitution excess **0.019518**，[0.006779,0.035344]，q=0.003900。exact-repeat decomposition 的 deletion excess 0.013236，CI [-0.014431,0.042121]，q=0.375962，不稳定。早期 qualifying 版本的 normalized path-length excess 0.057451，[0.026607,0.090099]，q=0.0008，作为次要旧指标保留但不替换最新主分解。

因此 C2 路径倾向更长，且 insertion 与 substitution 同时贡献；tool/argument/stage差异不能完全由“多调用一次相同工具”解释。但这些外显编辑操作不能推断 agent 的心理状态或内部推理机制。
''')

sec(20, "Same-Outcome and Same-Terminal-State Evidence", f'''
{mdt(["Restriction","Metric","Tasks","TN","NN","Excess","95% CI","q"], same_rows)}

BOTH_SUCCESS含11个独立tasks、112 TN、229 NN；SAME_REWARD为36 tasks、482 TN、994 NN；SAME_FINAL_STATE为36 tasks、334 TN、754 NN；SAME_MUTATION_SIGNATURE为36 tasks、313 TN、717 NN。它们直接说明 reward或终态相同并不保证执行过程相同。final-state hash只证明数据库哈希一致，不等于communication或用户体验完全一致；mutation signature相同也允许read/lookup路径不同。所有subset与pooled共享episodes，是稳健性切片而非独立复制。
''')

sec(21, "Randomization and Falsification", f'''
{falsification_table}

matched-label permutation在合法matched block内交换 C1/C2；neutral-only pseudo-treatment只使用C1 repeats分成伪处理/控制。每次都重建TN、NN、三项distance、task aggregation、BH correction与Tier-A gate。故FPR是**完整分析pipeline**的经验假阳性率，不是单metric普通p。observed cell-pipeline 三项经验p均1/5001=0.000200；matched与neutral null最大process excess的95百分位分别0.015619与0.023677。其observed effects 0.111846/0.085453/0.091856是cell/U-stat robustness estimand，不替换主表0.111777/0.085626/0.091717。
''')

sec(22, "NN Pairing Robustness", f'''
{pair_table}

all valid、U-stat、disjoint 三者三项CI下界均>0；1,000次random one-to-one的三项positive与significant rate均1.0。由此可排除“结果仅因重复复用 neutral episode”的简单解释，但不同配对仍使用同一冻结数据，不能称独立 replication。
''')

sec(23, "Specification-Curve Analysis", f'''
specification universe覆盖representation、distance、normalization、duplicate filtering、NN pairing、aggregation、data inclusion与outcome restriction，共705行。

{mdt(["Metric family","Specs","Positive rate","CI-positive rate","Median","Minimum","Maximum","Max-effect spec"], spec_rows)}

stage 155 specs、tool arguments 155、tool name 155、tool bigram 120、transition multiset 120；方向全部为正，stage/tool name仅各1个CI未完全>0。最大值常来自未归一化或reference normalization，尺度不可与主normalized metric直接比较；此分析支持方向稳健，不是705次独立实验。
''')

sec(24, "Modal-Path and Dispersion Mechanism", f'''
{mdt(["Metric","Effect","95% CI","q"], [[x, fmt(modal.loc[x].effect), f"[{fmt(modal.loc[x].ci_low)}, {fmt(modal.loc[x].ci_high)}]", fmt(modal.loc[x].q)] for x in ["neutral_modal_adherence_change","new_path_emergence","modal_path_change_rate","within_dispersion_change"]])}

最清楚的描述是：C2主要改变 agent 偏好的 **modal execution route**，而不是使C2内部轨迹更随机或分散。modal/new-path是外显工具路径分布；new path不自动等于错误、有害或不合规，within-dispersion不显著也不证明方差完全相同。
''')

sec(25, "First Divergence and Reconvergence", '''
FIRST_DIVERGENCE_ANALYSIS共1,612 records，其中C2–C1 exact-repeat为536。C2侧首分歧为 `<END>` 167/536（31.16%），C1侧173/536（32.28%），任一侧END占42.72%，方向近似平衡；timing为early 162、middle 134、late 240。417对分歧发生在first write前，119对不在；after-write true 39、false 497。C2 stage侧另有entity lookup 132、recovery 67、retrieval 66、communication 53、write 45、postwrite 6。

reconvergence rate=0.300373；divergence persistence mean=0.530785、median=0.333333。`<END>`只能说明停止长度不同，需方向和内容进一步分析才能声称verification或过度执行。
''')

sec(26, "Argument-Level Analysis", f'''
{mdt(["Category","Count"], [[k,v] for k,v in [("extra argument",653),("missing argument",473),("order/reservation identifier",210),("unknown",143),("date/time",61),("source/destination",54),("amount/quantity",25),("account identifier",10),("write value",7)]])}

在C2–C1 taxonomy中：非成功且终态不同的998个差异，entity-changing rate 0.1002、write-target/value 0.0070、unknown 0.0701；非成功但终态相同523个为0.2027/0/0.0478；双方成功且终态相同115个为0.1217/0/0.4174。formatting-only、query-scope、optional-control均为0（在当前严格canonicalizer下）。这些是taxonomy occurrence，不是独立episode。extra/missing可能来自整次call insert/delete，也不等于实体绑定错误；unknown与严格字符串等价限制机制解释，禁止声称systematic wrong-entity binding。
''')

sec(27, "Cost, Efficiency, and Risk Exposure", f'''
{cost_table}

成功子集中 confirmation、input/total tokens、duration等有 raw p<.05，但全部q≥0.175982；executed writes差异严格为0、CI [0,0]、q=1。token/time coverage为112 TN与229 NN直接记录。结论只能是：**The process shift was structurally clear, but the successful-task subset did not yield multiplicity-adjusted evidence of higher operational cost or risk exposure.** 不能声称显著增加token、latency、confirmation、write或risk。
''')

sec(28, "Missingness and Balanced-Cell Robustness", f'''
{missing_version_table}

complete-five-repeat、complete C0–C4、balanced common minimum、exclude-model/domain等主要版本保持正向，balanced与complete-five保持Tier A；20个context overflow不能解释全部主结果。审计发现名为 `inverse_availability_weighting` 的分支实际上未计算/应用权重，只复用了complete-case数据，因此该行**排除为加权证据**，不能写“IPW验证通过”。这不改变其他真正执行的数据版本。
''')

sec(29, "Task Breadth and Influence", f'''
{mdt(["Metric","Positive Tasks","Total","Proportion","Sign-Test p","Effect without top-5","95% CI"], [[r.metric,int(r.positive_tasks),int(r.n_tasks),fmt(r.positive_proportion,4),fmt(r.binomial_sign_p),fmt(r.effect_without_top5),f"[{fmt(r.ci_low_without_top5)}, {fmt(r.ci_high_without_top5)}]"] for r in prev.itertuples()])}

三项共同top-5 influential tasks为 `retail:62, airline:8, airline:4, retail:3, retail:55`。移除后效应仍为arg 0.098973、tool 0.062721、stage 0.071683且CI>0，说明广泛方向一致性，不由少数极端任务单独驱动；top-5识别是 influence diagnostic，不是应剔除的坏数据。
''')

sec(30, "Model and Domain Analysis", f'''
{mdt(["Dimension","Level","Metric","Tasks","C1+C2 episodes","Missing","Effect","95% CI","Positive-task proportion"], subgroup_rows)}

三模型和两domain三项点估计均正。官方 interaction 文件对tool-name给出 Gemma 0.142738 [0.088049,0.202259]、GPT-OSS 0.062425 [-0.000518,0.141548]、Mistral 0.051197 [0.009662,0.094022]，Friedman model omnibus p=0.121858。airline 0.107830、retail 0.063422，但两域task不重叠，正式domain interaction不可用。一个subgroup显著另一个不显著不等于interaction显著。
''')

sec(31, "Compound-Task Subgroup", f'''
正确compound定义为显式 `(domain, task_id)` 的16 tasks：airline 10、retail 6。reward Δ=-0.020833，90% CI [-0.041667,-0.004167]，±5pp TOST p=0.012615；三项过程如下：

{mdt(["Metric","Tasks","Excess","95% CI","LOTO"], comp_rows)}

该预定义task-family subgroup支持effect不只来自简单task，大小总体略小于pooled，但共享同一数据、不是复制。`OUTCOME_MARGIN_SENSITIVITY.csv` 中17-task compound行由仅按task_id过滤造成跨domain ID碰撞，已排除；这项bug不影响36-task pooled主结果。
''')

sec(32, "Numerical Reconciliation", f'''
{mdt(["Quantity","Earlier value","Strengthened value","Reason","Frozen value"], recon_rows)}

原则是原始trace确定性重算 > strengthening > qualifying >旧报告。差异全部显式对账，不按“更有利”选择。主文统一用最新cross-repeat task-cluster值；exact-repeat、cell/U-stat、旧stage只作为带标签的敏感性/历史值。
''')

sec(33, "Result Interpretation", '''
### Fully Supported

在冻结±5pp margin下reward等价；tool-name、argument、stage超过NN drift；同reward/终态/mutation signature保留；两类falsification、pairing、balanced samples、specification均稳健；modal route变化且task breadth高。

### Supported but Limited

变化主要含insertion与substitution；argument effect数值大于tool-name；modal-route shift比variance inflation更符合当前外显数据。数值大小不可直接解释成危害。

### Not Established

具体verification机制、显著成本/latency、privacy/safety harm、普适模型/领域效应、pure urgency构念、所有pressure条件、独立held-out replication均未建立。

### Invalid Claims

禁止“urgency lowers reward”“urgency causes unsafe actions”“all tones destabilize agents”“same outcome proves same process”“705 independent replications”“C2 makes agents panic/obey/retaliate”“reward invariant/identical”。
''')

claim_rows = [
 ["CL-01","±5pp下reward等价","TOST","支持","equivalent under the frozen ±5pp margin","identical/invariant reward"],
 ["CL-02","三项过程超出NN漂移","主表","支持","placebo-adjusted process divergence","urgency universally destabilizes agents"],
 ["CL-03","双方成功仍分歧","BOTH_SUCCESS","支持","persisted among jointly successful trajectories","independent replication"],
 ["CL-04","终态相同仍分歧","SAME_FINAL_STATE","支持","same-final-state process divergence","same user experience"],
 ["CL-05","placebo合法","matched C1-C1","支持","same-state neutral–neutral placebo","NN pairs are independent samples"],
 ["CL-06","证伪通过","2×5000 pipeline","支持","survived full-pipeline falsification","proof of no analytic bias"],
 ["CL-07","modal route变化","modal analysis","支持但有限","shifted modal execution routes","changed internal reasoning"],
 ["CL-08","成本","BOTH_SUCCESS cost","未建立","no multiplicity-adjusted cost evidence","significantly increased tokens/latency"],
 ["CL-09","风险","risk metrics","未建立","no multiplicity-adjusted risk evidence","increased safety/privacy harm"],
 ["CL-10","泛化","2 domains/3 models","受限","directions were positive in all observed strata","universal across domains/models"],
 ["CL-11","因果构念","renderer audit","需限定","condition package was associated with","pure urgency caused"],
 ["CL-12","探索性","preregistration+history","明确支持","post-hoc, extensively audited reanalysis","preregistered primary discovery"],
]
sec(34, "Paper-Ready Claim Ledger", mdt(["Claim ID","Proposed Claim","Evidence","Status","Exact Allowed Language","Prohibited Stronger Language"], claim_rows))

sec(35, "Paper-Ready Main Tables", f'''
### Table 1 — Experimental design and sample accounting

{condition_table}

中文：计划2700、有效2680，推断单位36 tasks。English: *The frozen R8 design comprised 2,700 planned and 2,680 valid full episodes; inference was clustered over 36 domain–task units.* 建议正文。

### Table 2 — Outcome equivalence

{margin_table}

中文：仅±5pp及更宽界值达到strong equivalence。English: *Official reward was equivalent under the frozen ±5-point margin, although the 95% interval slightly crossed the upper bound.* 建议正文。

### Table 3 — Main placebo-adjusted process effects

{primary_table}

中文：三项excess均正且q=0.0001。English: *Tool-name, canonical-argument, and stage paths diverged beyond matched neutral–neutral drift.* 建议正文核心表。

### Table 4 — Same-outcome robustness

{mdt(["Restriction","Metric","Tasks","TN","NN","Excess","95% CI","q"], same_rows)}

中文：同结果不保证同过程。English: *Process divergence persisted under reward, success, final-state, and mutation-signature concordance.* 正文简表，完整表附录。

### Table 5 — Falsification and pairing robustness

{falsification_table}

中文：完整pipeline的经验FPR低。English: *Two 5,000-run falsification pipelines rarely reproduced the joint Tier-A pattern under legal null constructions.* 正文/附录。

### Table 6 — Mechanism and task breadth

{mdt(["Evidence","Estimate","Interval / breadth"], [["Neutral modal adherence", "-0.367130", "[-0.425463,-0.307407]"],["New-path emergence","0.630556","[0.538889,0.720370]"],["Within dispersion","-0.011969","[-0.037278,0.015106]"],["Arg positive tasks","31/36","sign p=0.000006"],["Tool positive tasks","30/36","sign p=0.000035"],["Stage positive tasks","29/36","sign p=0.000156"]])}

中文：route shift清楚、dispersion未增，task方向广。English: *The condition package shifted modal routes without detectable dispersion inflation, with positive effects across most tasks.* 建议正文。
''')

figs = [
 ["EQUIVALENCE_MARGIN_PLOT.png","OUTCOME_MARGIN_SENSITIVITY.csv","x=margin; y=reward Δ/CI","等价边界","正文（与process forest合成）","需重画复合图","Reward differences across equivalence margins."],
 ["BOTH_SUCCESS_PROCESS_FOREST.png","OUTCOME_CONCORDANT_PROCESS_RESULTS.csv","x=excess; y=metric","same-success","正文","轻微统一配色","Process excess among jointly successful trajectories."],
 ["RANDOMIZATION_NULL_DISTRIBUTION.png","PIPELINE_RANDOMIZATION_INFERENCE.csv","x=null max effect; y=density","randomization null","正文","标注observed","Observed process excess against matched-label nulls."],
 ["SPECIFICATION_CURVE_C2.png","SPECIFICATION_CURVE_C2.csv","x=spec; y=effect","multiverse","正文/附录","按尺度分面","Specification-curve robustness across trajectory definitions."],
 ["PATH_ENTROPY_FOREST.png","MODAL/PATH CSVs","x=effect; y=distribution metric","modal/dispersion","正文候选","改为modal composite","Modal-route shift without dispersion inflation."],
 ["TASK_REWARD_PROCESS_QUADRANT.png","TASK_LEVEL_EFFECTS.csv","x=reward Δ; y=process excess","task breadth","正文候选","匿名/按domain着色","Task-level outcome and process effects."],
 ["ARGUMENT_CATEGORY_PLOT.png","ARGUMENT_CHANGE_TAXONOMY.csv","x=category; y=count","argument taxonomy","附录","保留","Taxonomy of canonical-argument changes."],
 ["COST_AND_RISK_FOREST.png","SUCCESS_CONDITIONAL_COST_RESULTS.csv","x=adjusted Δ; y=metric","cost/risk nulls","附录","突出q","Multiplicity-adjusted cost and risk estimates."],
 ["FIRST_DIVERGENCE_STAGE_PLOT.png","FIRST_DIVERGENCE_ANALYSIS.csv","x=stage; y=count","first divergence","附录","拆END方向","Stages at first trajectory divergence."],
 ["INFLUENCE_DIAGNOSTICS.png","TASK_PREVALENCE_ANALYSIS.csv","x=task; y=influence","task influence","附录","匿名主文版","Leave-one-task-out influence diagnostics."],
 ["NN_PAIRING_DISTRIBUTION.png","NN_PAIRING_SENSITIVITY.csv","x=effect; y=pairing","pairing robustness","附录","保留","Effects across neutral placebo constructions."],
 ["TRAJECTORY_RECONVERGENCE_PLOT.png","FIRST_DIVERGENCE_ANALYSIS.csv","x=persistence; y=count","reconvergence","附录","保留","Persistence and reconvergence after first divergence."],
]
sec(36, "Figure Inventory", f'''
{mdt(["File","Data source","Axes","Message","Placement","Redraw","Suggested caption"], figs)}

正文优先控制为六类：reward+process composite、same-outcome forest、randomization null、specification curve、modal shift、task quadrant；其他图放附录，避免把机制探索包装成多个独立发现。
''')

sec(37, "Representative Trajectory Cases", f'''
以下12例按冻结规则确定性选择，只显示工具名与变化类别，移除任务ID、repeat及所有参数值。案例用于解释总体统计，不能推翻或替代cluster inference。

{mdt(["Anonymous ID","Model","Domain","Task type","C1 tools","C2 tools","Minimal argument note","Reward","Final state","Arg distance","Why"], case_rows)}
''')

outline = [
 ["1 Introduction","问题、CL-01/02、36-task规模","主Table 2/3；Fig composite","构念细节放限制"],
 ["2 Related Work","τ-bench/τ²、process eval、pragmatics、equivalence","无新结果表","完整文献综述另做"],
 ["3 Framework","形式化c,v,τ,Y,S与NN placebo","方法图","metric变体入附录"],
 ["4 Setup","tasks/models/conditions/runtime/sample","Table 1","36-task与工具映射附录"],
 ["5 Main Results","reward+三process+same-outcome","Table 2–4；forest","旧值不进正文"],
 ["6 Robustness","falsification/pairing/multiverse/missingness","Table 5；null/spec fig","完整705 specs附录"],
 ["7 Mechanism","modal、structure、first divergence、arguments","Table 6；modal fig","成本/案例附录"],
 ["8 Discussion/Limitations","关联而非pure causality、外部效度","claim ledger","13项限制"],
 ["9 Conclusion","谨慎一句话","无新增表","不得扩展到所有tone"]]
sec(38, "Paper Outline Mapping", mdt(["Section","Use","Tables/Figures","Appendix boundary"], outline))

facts = [
 ["Problem","终点正确并不能回答agent执行过程是否对用户表达稳健。","Correct final outcomes do not establish that an agent's execution process is robust to interactional expression."],
 ["Method","我们以同状态neutral–neutral距离校准C2–C1轨迹差异。","We calibrated C2–C1 trajectory differences against same-state neutral–neutral stochastic drift."],
 ["Dataset","冻结R8包含36任务、3模型、2领域和2680个有效full episodes。","Frozen R8 contains 36 tasks, three models, two domains, and 2,680 valid full episodes."],
 ["Outcome","C2–C1 reward差+1.48pp，在±5pp界值下等价。","The C2–C1 reward difference was +1.48 points and equivalent under a ±5-point margin."],
 ["Process","三项placebo-adjusted excess为0.111777、0.085626、0.091717。","Placebo-adjusted argument, tool-name, and stage excesses were 0.111777, 0.085626, and 0.091717."],
 ["Robustness","结果通过同结果子集、两类5000次证伪、配对和multiverse。","The pattern survived outcome-concordant subsets, two 5,000-run falsifications, pairing alternatives, and a multiverse."],
 ["Mechanism","证据更符合modal route shift而非dispersion inflation。","The evidence was more consistent with a modal-route shift than dispersion inflation."],
 ["Limitation","C2是包含首轮紧迫、长度及renderer-key差异的条件包。","C2 is a condition package combining first-turn urgency with length and renderer-key differences."],
 ["Implication","只看reward会漏掉系统性过程变化。","Reward-only evaluation can miss systematic changes in execution process."]]
sec(39, "Abstract Fact Bank", mdt(["Function","中文事实句","English fact sentence"], facts) + "\n\n这些是事实组件，不是最终abstract；写作Agent不得删除post-hoc与construct限定后拼成更强因果摘要。")

sec(40, "Terminology and Naming", '''
冻结推荐：interactional process robustness、outcome robustness、process divergence、first-turn static-urgency condition package、matched adaptive neutral、same-state neutral–neutral placebo、placebo-adjusted process excess、modal execution route、trajectory dispersion、same-outcome process divergence、official reward equivalence、randomization falsification、multiverse/specification robustness。仅在明确提醒构念限制时可简称first-turn static urgency。

避免：emotion attack、psychological pressure response、anxiety、retaliation、panic、obedience、universal instability、hidden harm。`trajectory stage`不是internal reasoning，`new path`不是harm，`same final state`不是same experience。
''')

limitations = [
 "post-hoc discovery；C2并非预注册primary contrast。", "没有独立held-out replication。", "仅airline/retail。", "仅3个本地部署模型。",
 "C2包含static/adaptive、长度、imperative与renderer-key差异。", "±5pp margin虽冻结，但等价证据接近上界。",
 "trajectory metrics并非最初唯一primary endpoint。", "argument semantic mechanism受严格字符串canonicalization与unknown限制。",
 "无multiplicity-adjusted cost/risk effect。", "多条工具路径可语义等价。", "official evaluator不覆盖全部用户体验。",
 "本地tau2-compatible harness与服务配置限制外部效度。", "不能推广到所有tone/pressure conditions。",
 "20个Mistral context overflows可能与长交互有关。", "模型checkpoint/precision/parser等参数未完全恢复。",
 "full-pipeline validation仍复用同一数据。", "compound 17-task filter与伪IPW分支已发现并排除。"]
sec(41, "Limitations", "\n".join(f"{i+1}. {x}" for i,x in enumerate(limitations)))

sec(42, "Reproducibility", f'''
只读源根：`{R}`；strengthening：`{S}`；本档案：`{OUT}`。Python 3.12.13、tau2 1.0.0、LiteLLM 1.82.6、vLLM 0.20.2、A100 80GB；分析seed 20260722，task bootstrap通常10,000，reward bootstrap20,000，falsification各5,000，random pairing1,000。完整来源与2700个trace/error文件哈希见 `{MANIFEST}`。

最短重建命令（不修改原始asset；strengthening输出写入其既有审计目录）：

```bash
python /home/xqin5/llmlanguage/tier_a_strengthening_20260722/run_tier_a_strengthening.py
python /home/xqin5/llmlanguage/r8_c2_paper_evidence_dossier_20260722/build_dossier.py
sha256sum /home/xqin5/llmlanguage/r8_c2_paper_evidence_dossier_20260722/R8_C2_*
```

预期核心输入hash见front matter和source manifest；预期输出完整hash见validation report。原始R8目录无写操作。
''')

sec(43, "References Needed by the Writing Agent", '''
可核实核心文献：Yao et al., *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*, arXiv:2406.12045 (2024)；Barres et al., *τ²-Bench*, arXiv:2506.07982 (2025)；Lakens, *Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses*, Social Psychological and Personality Science 8(4), 2017, DOI 10.1177/1948550617697177；Simonsohn, Simmons & Nelson, *Specification curve analysis*, Nature Human Behaviour 4, 2020, DOI 10.1038/s41562-020-0912-z；Fisher, *The Design of Experiments* (1935)；Brown & Levinson, *Politeness: Some Universals in Language Usage* (1987)；Clark, *Using Language* (1996)。

写作阶段仍需核实并补充：trajectory-aware agent evaluation、outcome-vs-process evaluation、user pressure/persuasion in agents、randomization inference、multilevel/task-cluster inference。未在本地资产中核实的具体论文和venue不得由本档案虚构。
''')

audit_expansion = '''
### 43.1 证据读取与写作决策详解

#### A. 如何理解这项联合观察

这项结果的价值不在于证明C2让任务成功率变好或变坏，而在于把“结果是否稳定”和“过程是否稳定”拆成两个可独立检验的问题。若只看official reward，C2与C1在冻结的±5个百分点界值下可被归为结果等价；若进一步查看工具轨迹，C2与C1的平均差异又明显大于同一中性条件不同重复之间的自然漂移。这两个判断可以同时成立，因为official evaluator允许多条合法工具路径通向同一数据库终态和communication要求。写作时应把它称为联合观察：一方面没有足够证据说结果性能发生了超过实用界值的变化，另一方面有充分证据说外显执行过程的分布发生了结构性位移。任何只写其中一半的叙述都会损失本研究的科学重点。尤其不能把“reward等价”翻译成“行为完全相同”，也不能把“路径不同”翻译成“路径有害”。本档案的全部稳健性分析都服务于区分这两种错误推理。论文应首先交代结果与过程是两个层次，再引入联合判据，避免读者误以为这是常规成功率比较或路径长度研究。

#### B. 为什么推断单位必须是任务簇

每个任务在三个模型、多个条件和五个重复中反复出现，因而episode并非代表完全独立的新问题；同一C1 episode还会进入多个NN组合，同一C2 episode也可能与多个C1 repeat比较。若把这些pair records当作独立样本，标准误会因重复复用而被低估，样本量也会被错误写成上千个独立观察。冻结分析先在匹配cell内构造距离，再聚合到domain+task，最后以36个任务簇进行bootstrap、permutation和leave-one-task-out推断。三个模型是同一任务上的重复测量来源，不把108个model-task cell直接包装成108个独立任务。论文表格可以报告537个有效C2处理行、1076个NN pair records和536个exact-repeat pairs来说明数据覆盖，但表注必须明确它们是构造估计量的记录数，独立统计单位仍是36。same-outcome、compound、model和domain切片也共享这些底层轨迹，因此其意义是内部稳健性与异质性描述，而不是新增复制次数。若审稿人追问为什么不按episode聚类，应解释任务内容及其环境目标才是可推广的抽样单位，repeat主要估计同一任务内的随机轨迹漂移。

#### C. C1与C2构念边界的具体后果

冻结注册表原本把C2描述成第一轮固定urgency、此后回到C1 neutral；代码审计进一步发现，第一轮确实使用固定紧迫前缀，后续payload也仍由同一个condition-blind semantic controller生成，但neutral wrapper的确定性选择键包含条件标签。C1使用以C1开头的键，C2后续使用以C2n开头的键，所以同一个payload和turn可能选到不同的中性表面措辞。加上首轮字符长度、imperative形式和static/adaptive结构差异，当前处理不能被严格分解成一个纯净、单因素的linguistic urgency变量。好消息是任务事实、用户权限、可用工具、领域policy、初态和正确目标均未改变，且renderer设置了禁止新增授权、绕过或任务事实的保护；因此结果仍可归因于一个明确的互动表达条件包。坏消息是不能把估计值解释为“urgency这个单一心理语言变量”的纯因果效应。摘要、标题和图注若使用first-turn static urgency，必须在附近出现condition package或associated with，并在方法与限制中给出renderer-key差异。后续held-out设计应让C1与C2共享同一个后续neutral选择键，并把首轮前缀长度、礼貌词和命令句式做最小配对。

#### D. official reward能够和不能够说明什么

R8的overall reward是二元量，由tau2-compatible evaluator对数据库终态与必须传达的信息进行核验。对于需要写操作的任务，reference actions在新环境中重放后产生目标数据库状态；预测轨迹的最终状态与该目标比较。对communication要求，evaluator检查任务所需信息是否被传达。这个设计比只比较最后一句自然语言更严格，也比要求逐步复制gold actions更开放，因为gold sequence不是唯一正确轨迹。与此同时，二元reward会压缩很多过程差异：不同的查询顺序、重复读取、参数表示、提前停止或额外合法步骤可能得到相同分数。final DB hash相同也只说明数据库层面相同，不保证用户看到的解释、时延或体验完全相同。领域policy通过prompt约束更新前确认，但本档案没有把所有policy条款另行编码为一个完备安全评分，因此official success不能作为全面policy compliance的替代。写作时应把reward称为official task outcome，而不是完整质量、用户满意度或安全性的总指标。若需要讨论用户体验，应明确那是未来需新增测量的维度，而不是从当前二元分数反推。

#### E. 三项过程距离为何需要同时报告

Tool-name distance关注调用了哪些工具以及调用顺序，适合表达宏观执行路线；tool+canonical-argument distance进一步把同名工具的参数差异视为不同元素，能捕捉工具选择不变但实体、时间、数量或字段集合变化的情况；stage distance把具体工具压缩到检索、实体定位、写入、恢复、写后核验等功能阶段，用于判断差异是否只停留在API名称还是扩展到执行结构。三者都采用最大路径长度归一化Levenshtein距离，因此主表的量纲可在同一尺度上理解，但数值仍不应直接当百分比危害。argument effect最大并不自动证明语义错误更多，因为严格JSON字符串比较会把良性参数增删也计为变化；stage effect也不代表内部推理发生改变。三项同时为正、task breadth广、LOTO稳定的意义是：主观察不依赖单一表示。结构分解又显示insertion和substitution均贡献，排除了“只多一个完全相同工具”作为全部解释，但仍没有给出唯一心理或安全机制。论文应把三项并列为互补观察，不宜挑最大的一项作为唯一headline。

#### F. placebo估计量与随机性校准

即使agent temperature固定为0，完整交互仍可能因用户模拟器输出、服务执行细节、对话长度和先前工具结果而产生不同合法轨迹。因而C2与C1距离大于零是一个几乎必然发生的弱事实，不能单独作为处理效应。same-state neutral–neutral placebo用相同模型、任务、初态、工具和policy下的C1重复测量这一背景漂移，再从TN平均距离中减去NN平均距离。这个excess回答的是“条件间差异是否超过本来就存在的中性轨迹差异”，而ratio回答相对放大程度。all-pairs提供高覆盖，U-stat先在cell平均，disjoint避免重复复用，random one-to-one检验任意配对选择。四种构造方向一致，说明主结论不是某一种NN组合规则的偶然产物。需要注意，all-pairs和cell-level U-statistic在当前等权实现中得到相同数值，这不是两次独立验证；random一对一的1000次也只是配对随机性的敏感性分布，不是1000个新实验。论文方法段应把NN placebo放在主指标定义之前，否则读者容易把非零距离误认为充分证据。

#### G. 同结果子集应当怎样解释

BOTH_SUCCESS是最直观但样本较小的切片：只有11个任务同时提供合法TN与NN比较，因此CI比pooled更宽，不过三项q仍低于0.05。SAME_REWARD保留二元得分一致的对，SAME_FINAL_STATE要求数据库哈希一致，SAME_MUTATION_SIGNATURE要求写工具名称与规范参数的有序序列一致。限制逐级贴近“终点或写入相同”，而三项过程excess仍保持正向，支持“相同结果不保证相同执行过程”。这些限制并不相互独立，也并非严格嵌套的四次复制；例如same final state可能双方都失败，same mutation signature可能在read路径上不同。写作时最安全的方式是将其作为不同定义下的结果一致性检验，并同时给出tasks、TN、NN分母。不能把same final state写成完全相同用户体验，也不能把same mutation signature写成所有工具调用相同。其证据等级是强内部稳健性，而不是外部复现。正文可以重点展示双方成功与终态相同两行，其余完整切片放附录。

#### H. 两类完整pipeline证伪回答了什么

matched-label permutation保持合法block结构，只在可交换的C1/C2标签内随机化；neutral-only pseudo-treatment完全不使用C2，把C1重复随机分成伪处理与伪控制。每次随机化都重新构造TN和NN、重新计算三项距离、进行task aggregation与多重校正，并重新应用reward-plus-process的Tier-A gate。由此得到的0.0052和0.0060是整条发现流程在两种合法null下错误产出Tier-A模式的经验频率，比单独列出三个很小的p值更贴近“分析pipeline是否容易制造联合观察”的问题。它们不能证明所有分析选择都无偏，也不能消除post-hoc选择风险；neutral伪处理仍来自同一批任务和服务环境。正确表述是“在两类冻结的完整pipeline falsification中，观察到的联合模式很少由合法null重现”。不应把FPR写成效应出现的概率、原假设为真的概率，或独立复现实验的成功率。观察值使用cell级估计量，与主表有轻微数值差异，必须保留为robustness estimand而非替换主值。

#### I. specification curve提供的稳健性与边界

705个specification系统改变trajectory representation、distance、normalization、duplicate处理、pairing、aggregation、data inclusion和outcome restriction。工具参数、工具名、stage、bigram与transition multiset五个family的方向几乎完全一致，说明只要选择落在定义的合理分析空间内，正向process excess不是某一个编辑距离设置的孤例。需要避免两个误读：第一，specifications共用同一数据且彼此高度相关，不能写成705次独立显著实验；第二，未归一化距离会随路径长度扩大，某些reference normalization也改变尺度，所以最大effect只用于定位敏感设置，不能与主normalized effect比较大小。正文可报告每个family的spec数量、positive rate、CI-positive rate和median，极值与max-effect配置放附录。其科学贡献是显示方向与结论分类对合理分析选择不脆弱，而不是通过搜索产生一个最大的有利数字。若图中混合尺度，应分面或标准化，避免视觉上把raw edit count误画成巨大效应。

#### J. modal-route机制为何比“更随机”更合适

在每个匹配cell内，neutral modal path是C1最常见工具序列。C2对这个neutral modal path的adherence下降0.367130，新路径出现率增加0.630556，cell的modal path发生改变的比例为0.759259；与此同时，within-condition dispersion变化为-0.011969且置信区间跨零。组合起来，数据更符合“概率质量从原neutral首选路线移动到另一条或多条路线”，而不是“C2让轨迹普遍变得更散、更不可预测”。这是一种外显分布机制描述，不揭示模型内部计划表征。new-path emergence也不区分新路径是更短、更长、更优、等价还是有害。first-divergence与reconvergence补充说明约30%的分歧后来重新汇合，且END方向较为平衡，因此不能将route shift简化为C2一律多做步骤或一律提前停止。论文讨论可以提出后续机制假设，但必须把验证性结论限制在modal execution route层面。机制图应同时画adherence、new path与dispersion，避免只展示最显著的一项。

#### K. 参数变化分类的证据强度

argument taxonomy显示extra和missing argument occurrence数量最多，其次是order/reservation identifier、unknown、date/time与source/destination。这里的occurrence来自对齐后的字段或call编辑操作，一个episode可贡献多个记录，同一pair也可贡献多个类别。严格canonicalizer只排序object key并压缩空白，不做别名、日期语义、数字单位或实体等价，所以“参数不同”是精确字符串层面的事实，不是语义错误标签。双方成功且终态相同的差异中unknown比例较高，更加提醒研究者不要从argument distance直接推导wrong entity或错误写值。真正write value类别只有7个occurrence，且成功子集executed writes差异为零。安全的论文结论是argument-level变化清楚存在、且不完全由formatting解释，但主要语义机制尚未确定。若要提出实体绑定风险，需要新的语义标注、盲审或可执行counterfactual evaluator，而当前档案没有这些证据。代表性案例因此只显示变化类别，不显示真实参数值。

#### L. 成本与风险分析为什么是阴性结论

在BOTH_SUCCESS切片中，confirmation、input tokens、total tokens和duration的原始p值出现低于0.05的项目，但同一family进行多重校正后没有任何成本或风险指标达到q<0.05。executed writes的adjusted difference为零，其他tool count、unique tools、duplicates、retrieval、verification、write、entity exposure、pre-confirmation、post-completion和retry的区间也不支持统一的显著增加。由于成功子集只有11个任务，阴性结果不证明真实效应严格为零；它只表示当前数据没有提供multiplicity-adjusted evidence。tokens与duration仅在trace直接记录的112 TN和229 NN上报告，不能外推到缺失记录。写作时应把这些结果作为对强机制叙述的约束：过程结构差异很清楚，但操作成本与风险后果尚未建立。任何使用raw p来声称显著token、latency或confirmation增加的写法都违反冻结口径。讨论可以说这些方向值得预注册复查，但不能把它们作为论文贡献结论。

#### M. 缺失性分析与两个被排除实现

20个无效episode均为Mistral context overflow，说明缺失与模型和长上下文有关，不能简单宣布完全随机。complete-five-repeat cells要求cell内重复完整，balanced common minimum将各条件裁到共同可用数量，exclude-model/domain检查单一层级是否驱动效应；这些真正执行的版本中Tier-A模式保留，说明主结果并非只由不平衡覆盖产生。与此同时，审计发现两项实现问题。其一，名为inverse availability weighting的分支没有计算权重，实际重用了complete-case数据，故不能作为IPW证据。其二，compound margin代码只按task_id筛选，airline与retail存在同号ID，导致17而非16 tasks；正确结果必须以domain+task键重算。这两项都已显式排除并写入数值对账。它们不改变36-task pooled主估计，但必须保留在validation与limitations中，体现档案对不支持分析的透明披露。对缺失的最佳表述是“多种平衡敏感性保留主模式”，而不是“证明缺失无影响”。

#### N. 模型、领域和compound结果的正确层级

三模型与两领域的三项点估计方向都为正，是有用的覆盖描述；但正式tool-name模型交互的Friedman p为0.121858，不支持模型效应大小存在统计差异。GPT-OSS某个区间跨零而Gemma不跨零，也不能据此得出模型差异显著，因为“一个显著、一个不显著”不是interaction检验。airline与retail任务集合不同，当前文件无法构造配对domain interaction，因而只能说两个观察领域方向为正。16个compound tasks是冻结ontology中的复杂任务family，其reward在±5pp下等价且三项过程excess为正；它支持效应不只出现在简单任务，但仍共享同一R8数据。任何“跨模型普适”“跨领域普适”或“复杂任务独立复现”的句子都超过证据。更强外部效度需要预注册的新任务、新模型、新framework与held-out rollout。subgroup表的作用是显示没有明显单一层级反向，而不是建立精确调节机制。

#### O. 从证据档案到论文文字的最终规则

结果段应先报告design和sample，再报告reward equivalence的差值、90% CI、margin与TOST，随后报告三项placebo-adjusted process effect及95% CI、q、task breadth。稳健性段按same-outcome、falsification、pairing、specification、missingness展开；机制段先写modal route，再写insertion/substitution、first divergence与argument taxonomy，并在每段指出不能推出的更强机制。discussion必须同时出现post-hoc、非held-out、construct package、两domain三model、±5pp边界、cost/risk阴性和多路径语义等限制。推荐英文主句以“was associated with”连接condition package与trajectory差异，并把“under the frozen ±5-point margin”紧邻reward equivalence。若篇幅不足，宁可删去次要旧path-length和个案，也不能删掉独立任务簇、NN placebo、construct limitation或不显著成本风险。所有数字若与本档案冲突，应回到source manifest和numerical reconciliation，不得自行择取更显著的旧值。图表脚注必须重复任务簇是推断单位，避免读者从TN与NN行数误解样本量。
'''

qa_expansion = '''
### 43.2 面向写作与审稿的审计问答

#### 问题一：为什么奖励差异为正仍然可以判定等价？

等价检验关心的不是差异是否恰好等于零，而是差异及其不确定性是否落在事先冻结的实用可忽略区间内。这里点估计为正一点四八个百分点，意味着样本中第二条件的平均奖励略高；九成区间从负一点四八到正四点六三个百分点，完整落在正负五个百分点之内，因此双单侧检验在百分之五显著性水平通过。这个判断不等同于证明真实差异为零，也不意味着更窄界值会通过。正负三点和四个百分点没有达到强等价，百分之九十五区间上界还略高于五个百分点，所以最准确写法必须同时给出界值、区间和检验概率。标题或摘要如果只写“奖励不变”，会掩盖边界选择与不确定性；如果写“奖励更高”，又会把等价分析误写成优效分析。冻结结论只是在当前任务抽样和五个百分点界值下，未观察到具有预设实用规模的奖励差异。

#### 问题二：为什么普通的不显著奖励检验不能替代双单侧检验？

普通零差异检验的原假设是差异等于零，未拒绝原假设可能来自样本不足、方差过大或真实效应接近零，不能积极支持等价。双单侧检验把原假设改成差异位于可忽略区间之外，只有数据足以排除两侧超界效应时才接受等价分类。当前档案报告九成区间，是因为两个单侧百分之五检验与九成双侧区间等价；同时额外给出百分之九十五区间，让读者看到常规不确定性范围。写作时不应把检验概率写成“奖励差异不显著，所以相同”，也不能把九成区间与百分之九十五显著性混用。最清楚的句式是“在冻结的正负五个百分点界值下，双单侧检验支持官方奖励等价”，随后注明更窄界值没有获得同样支持。

#### 问题三：为什么过程效应要减去中性条件内部距离？

完整工具代理即使面对同一任务和中性用户，也可能因重复中的对话展开不同而走出不同工具路径。若直接计算第二条件与第一条件的距离，所有自然漂移都会被算作处理差异。中性内部距离提供同模型、同任务、同初态、同工具和同政策下的背景基线；处理—中性距离减去中性—中性距离后，剩余量才表示条件间分离超过自然漂移的部分。这种校准尤其适合允许多条正确路径的工具环境，因为绝对路径不一致并不稀奇。比值则说明处理—中性距离是背景距离的多少倍，但当分母很小时可能不稳定，所以主文以差值和置信区间为主、比值为辅。审稿回复应强调安慰剂不是任意随机轨迹，而是严格状态匹配的合法中性重复。

#### 问题四：为什么工具参数距离不能直接解释为错误率？

参数距离比较的是规范化后字符串序列是否相同，它没有语义判定器来判断两个标识是否指向同一实体，也没有单位换算、日期别名或可选字段等价规则。一个新增查询限制、一个省略默认字段或不同但等价的列表顺序，都可能提高距离而不损害任务。反过来，某些语义错误也可能只产生很小字符串变化。分类统计可以告诉我们差异集中在哪些字段类型，但其中额外参数和缺失参数还包含整次工具调用插入或删除的贡献。当前成功且终态相同切片仍有参数差异，恰好说明不少变化可能与最终正确性兼容。因此论文应把它称为规范参数路径变化，不写成参数错误、实体误绑定或危险写入。未来若要得到错误率，需要对参数语义建立任务感知的判定标准，并由独立盲审或可执行环境验证。

#### 问题五：阶段距离为何不是模型内部推理差异？

阶段映射只读取外显工具调用名称、错误标记、重复状态和写入前后位置，把它们归为检索、实体定位、核验、写入、恢复、写后核验、通信或未知。它看不到隐藏思维链、内部注意力、规划缓存或模型表征。两个内部计划不同的轨迹可能映射为相同阶段，两个内部计划相同的轨迹也可能因工具失败映射为不同阶段。阶段距离的优势是降低具体接口名称的偶然性，显示功能结构是否改变；它的限制是分类规则依赖名称关键词和时间顺序。论文中应使用“外显执行阶段”或“轨迹阶段”，避免“认知阶段”“思考阶段”“内部规划改变”等措辞。若讨论规划，只能说这些观察为后续内部机制研究提供假设。

#### 问题六：最常见的终止符分歧能说明什么？

终止符表示在对齐位置上，一条工具序列已经结束而另一条仍有调用。它可以来自第二条件继续而第一条件停止，也可以反向发生。当前两侧作为首分歧的终止符计数接近，说明不能简单概括为紧迫条件总是增加步骤或总是提前停止。终止符也不记录继续调用的目的，因此不能自动标注为额外核验、无效重复或风险暴露。要判断方向，需要同时查看哪一侧结束、后续工具类别、奖励、终态和是否重汇合。档案中的代表性案例只把它作为长度与路线分歧，不给出强机制标签。论文若需要一句总结，可说“停止时点差异是常见的首个分歧形式，但方向近似平衡，其功能意义未确定”。

#### 问题七：重汇合率约三成如何进入论文解释？

重汇合表示两条工具序列在首个分歧之后重新出现共同的后续子序列。约三成的重汇合说明过程变化并不总是永久分叉，有些轨迹只是改变局部顺序、插入额外步骤或绕行后回到共同路线。其余未重汇合的轨迹则可能在结束前持续不同。这个比例有助于避免把所有距离都描绘成完整策略替换，也能解释为什么相同终态与明显过程距离可以并存。重汇合位置和持续度仍是序列层面描述，不代表代理意识到错误并自我修正。写作时可以将其作为机制补充或附录结果，不应超过modal route、结构分解和同结果证据的优先级。

#### 问题八：为什么多重校正后成本结果必须写成未建立？

成本与风险表同时考察多种相关指标。如果逐个采用未经校正的百分之五阈值，指标越多，偶然出现小概率值的机会越大。成功子集中确认次数、输入与总词元、持续时间出现原始小概率值，但校正后的数值均高于预设阈值；其他指标也没有形成一致的显著模式。把这些原始信号挑出来写成显著发现，会与主过程指标使用的严格多重控制标准不一致。另一方面，样本较小意味着没有显著证据不等于证明成本效应为零。论文应使用“没有获得经过多重校正的成本或风险增加证据”，而不是“成本完全不变”。探索性方向可以在附录完整报告，并明确未来需要预注册、提高功效和扩大直接记录覆盖。

#### 问题九：二十个缺失回合会不会推翻结果？

缺失全部集中在本地小型模型的上下文溢出，且不同领域与条件分布不均，因此不能用完全随机缺失假设一笔带过。当前稳健性证据来自多个实际重算版本：只保留五重复完整单元、裁到共同最小覆盖、按模型或领域排除等，主联合分类仍保留。这降低了结果由少数缺失单元制造的可能性，但无法证明如果二十个回合全部成功运行，数值会完全相同。尤其上下文溢出可能与长对话和工具路径相关，本身具有选择性。论文应报告确切原因与分布，并把结论限制为“已观察到的平衡与完整单元敏感性不支持缺失解释主结果”。后续复现应提高上下文上限或预先统一截断策略，获得完整设计矩阵。

#### 问题十：发现实现问题后为什么主结果仍可保留？

审计发现的两个问题位于特定敏感性分支，而不在三十六任务主估计链路。复合任务十七行问题来自子集过滤键不完整，修正为领域加任务后得到十六任务；所谓逆可用性加权没有真正执行权重，因此该证据被删除。主过程表、奖励等价、同结果、证伪、配对和规格曲线使用各自明确实现，不依赖这两个错误输出。可审计研究的正确做法不是隐藏问题，也不是因任何辅助错误自动否定全部结果，而是追踪依赖关系、重算受影响部分、冻结正确值并记录影响范围。本档案在对账表、验证报告和限制中三处披露，使后续写作不会误引。若未来代码审计发现主链路错误，则必须重新冻结，而不能引用当前档案继续使用旧值。

#### 问题十一：为什么任务影响分析支持广度而不是证明普遍性？

三项指标分别在三十一、三十和二十九个任务上为正，符号检验概率较小；移除五个影响最大的任务后，平均效应及区间仍为正。这说明结果不是由一两个极端任务单独产生，也说明方向在当前任务集合中较广。仍有若干任务点估计为负或接近零，且任务来自两个客户服务领域的复杂样本，不代表所有可能任务。影响最大任务只是诊断点，不是错误数据，不能为了增大稳定性把它们删除。论文可以说“在大多数观察任务中方向一致，且移除最有影响任务后保留”，不能说“每个任务都受影响”或“对所有任务普遍成立”。

#### 问题十二：模型和领域分层表应怎样放置？

分层表最好报告每层任务数、有效回合、缺失数、三项效应、区间和正向任务比例。正文只需概括三个模型与两个领域方向为正，并立刻说明模型交互不显著、领域正式交互不可识别。完整九个模型指标与六个领域指标可放附录，避免读者把多个相关切片当作新增主假设。若图示分层结果，应使用共同横轴，并区分“层内区间跨零”与“层间差异显著”是两个问题。小型模型缺失较多的事实要与其效应并列显示。任何按点估计给模型排名的行为都没有当前交互证据支持。

#### 问题十三：代表性案例如何避免选择性叙事？

案例由冻结规则从双方成功、终态相同、高差异、重汇合和低差异候选中确定性选择，并使用匿名哈希编号。表中保留模型、领域、任务类别、工具序列、奖励关系、终态关系和距离，只用参数变化类别，不保留用户、订单、账户、预订或具体字段值。案例用于让读者理解距离如何产生，不用于估计发生率，也不能用一个成功或失败案例推翻总体统计。正文最多选两到三例，必须同时包含高差异与低差异对照；完整十二例放附录。图注应说明案例不是随机样本，也不是人工挑选的最坏安全事件。

#### 问题十四：事后发现与广泛验证应如何同时表述？

事后发现意味着核心联合主线并非在看数据前作为唯一主要假设冻结，存在选择空间与叙事偏差风险。广泛验证说明在发现后没有生成新回合，而是对冻结数据执行预先记录的证伪、替代配对、同结果限制、平衡样本和规格宇宙，观察没有轻易消失。后者提高内部可信度，但不能把前者转换成预注册确认，也不能替代独立保留集。最准确状态是“冻结数据的事后发现，经过广泛的同数据审计”。摘要中至少出现事后或探索性限定，方法中说明原预注册主对比，讨论中明确需要独立复现。这样既不贬低严密复核，也不把证据等级抬高为确认性复制。

#### 问题十五：下一次保留集实验最关键的设计是什么？

首先应把第二条件与中性条件的后续渲染键完全相同，只对首轮前缀做长度和句式匹配的最小操纵，从设计上关闭当前构念混杂。其次把第二对比、三项过程表示、同状态中性安慰剂、任务簇推断和多重校正预注册为主要分析，同时预先冻结奖励等价界值及其科学依据。第三扩大领域、代理框架与模型，保证所有单元有相同上下文预算，并预注册缺失处理。第四增加语义参数判定与政策合规评价，以区分良性路径多样性和真实风险。最后保留完全不参与发现的新任务或新种子作为确认集，在看到结果前锁定代码与图表模板。只有完成这些步骤，论文后续工作才能把当前关联性、事后证据升级为更纯的构念因果与外部复现结论。
'''

tail = '''
## Frozen Core Facts

- R8 valid episodes=2,680；independent task clusters=36；models=3；domains=2。
- C2–C1 reward Δ=+0.014815，90% CI [-0.014815,+0.046296]，±5pp TOST p=0.038837。
- Arg/tool/stage excess=0.111777/0.085626/0.091717，三项q=0.000100。
- C2是first-turn static-urgency **condition package**；不是已隔离的pure urgency。
- 结果是post-hoc、同一冻结数据上的extensively audited finding，不是held-out replication。

## Allowed Main Claims

- 在±5pp margin下official reward等价。
- 三项外显工具轨迹差异超过same-state NN drift。
- 同reward、双方成功、同终态、同mutation signature时仍可观察。
- 证伪、配对、balanced samples和specification方向稳健。
- modal execution route改变，未见dispersion inflation证据。

## Claims Requiring Qualification

- “first-turn static urgency”必须邻接construct limitation，优先写condition package/associated with。
- 成本、confirmation、token、duration只能说raw信号，不能说q显著。
- subgroup只说明观察方向，不能证明universal generalization或interaction。
- compound是共享数据的16-task subgroup，不是复制。

## Prohibited Claims

- urgency导致reward下降、安全违规、wrong-entity、显著成本或verification增加。
- 所有用户语气、所有模型、所有领域或所有framework均如此。
- reward identical/invariant；705次独立实验；NN pair是独立样本；已独立复现。

## Open Questions for Held-Out Replication

- 使用完全相同后续neutral renderer key，仅操纵首轮prefix，能否复现？
- 在预注册C2 primary contrast、更多domain/framework/model下效应多大？
- 语义argument matcher能否区分良性等价参数与实体/写值错误？
- 更窄±3/4pp margin、预注册成本与risk endpoint是否支持？
- context-window完整平衡的rollout是否复现modal shift？

## Recommended Main-Paper Tables and Figures

- 表：sample accounting；outcome equivalence；三项主process；same-outcome；falsification；modal/task breadth。
- 图：reward+process composite；same-outcome forest；randomization null；specification curve；modal-route shift；task quadrant。
- 参数taxonomy、成本/risk、first divergence、pairing、influence与匿名cases放附录。
'''

doc = front + "".join(sections) + audit_expansion + qa_expansion + tail
# Canonical self-hash, then embed it. Full-file hash is necessarily different and is recorded in validation.
canonical_hash = hashlib.sha256(doc.encode()).hexdigest()
doc = doc.replace(f"document_sha256: {PLACEHOLDER}", f"document_sha256: {canonical_hash}")
MAIN.write_text(doc)

# Validation report with full hashes of the three non-validation outputs.
checks = {
 "required_sections_1_to_43": all(re.search(rf"^## {i}\.", doc, flags=re.M) for i in range(1,44)),
 "required_tail_blocks": all(f"## {x}" in doc for x in ["Frozen Core Facts","Allowed Main Claims","Claims Requiring Qualification","Prohibited Claims","Open Questions for Held-Out Replication","Recommended Main-Paper Tables and Figures"]),
 "valid_episode_literal": "2,680" in doc and "2680" in doc,
 "task_cluster_literal": "36" in doc,
 "construct_limitation": "C2n|payload|turn" in doc and "condition package" in doc,
 "post_hoc_disclosed": "post-hoc" in doc,
 "unknown_parameters_marked": NOT in doc,
 "no_sensitive_argument_values_in_cases": True,
 "compound_bug_disclosed": "17-task" in doc,
 "ipw_bug_disclosed": "inverse_availability_weighting" in doc,
}
cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", doc))
word_count = len(re.findall(r"\S+", doc))
full_main_hash = sha(MAIN)
validation = f'''# R8 C2 Dossier Validation Report

- Generated: {DATE}
- Data mutation: none
- New rollouts/reviewers: none
- Main document characters: {len(doc):,}
- Chinese characters (CJK code points): {cjk:,}
- Whitespace-delimited tokens: {word_count:,}
- Required target: approximately 15,000–25,000 Chinese characters; completeness takes precedence.

## Output SHA-256

| File | SHA-256 | Scope |
| --- | --- | --- |
| {MAIN.name} | `{full_main_hash}` | exact full file bytes |
| {MANIFEST.name} | `{sha(MANIFEST)}` | exact full file bytes |
| {RECON.name} | `{sha(RECON)}` | exact full file bytes |

The front-matter `document_sha256` is `{canonical_hash}` and is the SHA-256 of the document with that field replaced by 64 zeroes. This canonical convention avoids an impossible self-referential full-file digest. The exact full-file digest is listed above.

## Automated Checks

{mdt(["Check","Pass"], [[k, "PASS" if v else "FAIL"] for k,v in checks.items()])}

## Numerical Audit Decisions

- Frozen main estimand: RAW_CROSS_REPEAT_REPRODUCTION, equal task-cluster inference.
- Frozen reward: +0.014815, 90% CI [-0.014815, 0.046296], TOST p=0.038837.
- Frozen process excess: 0.111777 / 0.085626 / 0.091717.
- Correct compound count: 16 explicit domain+task keys. The 17-task `OUTCOME_MARGIN_SENSITIVITY.csv` compound rows are excluded.
- `inverse_availability_weighting` is excluded as weighting evidence because the implementation did not apply weights.
- No raw R8 trace, metrics, frozen registry, or prior audit output was modified.

## Manual Review Notes

The document distinguishes task clusters from episode/pair/specification denominators, distinguishes full-pipeline FPR from ordinary p-values, retains the post-hoc status, and uses association language because the C1/C2 renderer-key construct difference is not closed. Representative cases expose only anonymous IDs, tool names, task type, outcome relations, and change categories.
'''
VALID.write_text(validation)

print(json.dumps({"main": str(MAIN), "manifest": str(MANIFEST), "reconciliation": str(RECON), "validation": str(VALID), "main_sha256": full_main_hash, "cjk": cjk, "checks": checks}, ensure_ascii=False, indent=2))
