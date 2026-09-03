#!/usr/bin/env python3
"""Build all_files_inventory.csv + experiment_inventory.csv under 00_inventory/."""
import os, csv, time, re
from _common import REPO, OUT

ROOTS = ["/home/xqin5/llmlanguage"]
EXTS = {".csv",".tsv",".json",".jsonl",".parquet",".pkl",".npy",".npz",".log",".txt",".md",".ipynb",".py",".sh",".yaml",".yml",".pdf"}
KW_FAM = [("r9v2","R9v2"),("r9v1","R9v1"),("r9_attack","R9"),("r9v2_smoke","R9v2"),("misroute","MISROUTE"),
          ("tier_a","MISROUTE-tierA"),("r8_full_episode","R8"),("r8_attack","R8"),("r8b_attack","R8"),
          ("r7d_ipma","R7-D"),("r7c_ipma","R7-C"),("r7b_ipma","R7-B"),("r7_ipma","R7"),
          ("r6_sensitivity","R6"),("measurement_repair","R5"),("stage2_5b","R4"),("stage2_5","Stage2.5"),
          ("EACL","EACL"),("post_misroute","POST_MISROUTE")]
def fam(p):
    pl=p.lower()
    for k,v in KW_FAM:
        if k in pl: return v
    return ""
def role(p):
    pl=p.lower()
    if pl.endswith(".jsonl") and "episode" in pl: return "raw_episode_data"
    if pl.endswith((".csv",".tsv")): return "summary/analysis_table"
    if "analysis" in pl and pl.endswith(".json"): return "analysis_output"
    if pl.endswith(".py"): return "analysis_code"
    if pl.endswith((".png",".pdf",".svg")): return "figure"
    if pl.endswith(".md"): return "report/doc"
    if pl.endswith(".log"): return "log"
    if pl.endswith(".json"): return "config/frozen/manifest"
    return "other"
ATK = re.compile(r"attack|adaptive|clarif|verif|oversight|pressure|urgency|skeptic|pasr|asr", re.I)

os.makedirs(f"{OUT}/00_inventory", exist_ok=True)
rows=[]; fid=0
for root in ROOTS:
    for dp,dns,fns in os.walk(root):
        dns[:] = [d for d in dns if d not in {".git","__pycache__",".ipynb_checkpoints",".ruff_cache",".pytest_cache","node_modules"}]
        for fn in fns:
            ext=os.path.splitext(fn)[1].lower()
            if ext not in EXTS: continue
            ap=os.path.join(dp,fn)
            try: sstat=os.stat(ap)
            except OSError: continue
            rp=os.path.relpath(ap,"/home/xqin5/llmlanguage")
            fid+=1
            rows.append(dict(file_id=fid, absolute_path=ap, relative_path=rp, file_name=fn, extension=ext,
                size=sstat.st_size, modified_time=time.strftime("%Y-%m-%d",time.localtime(sstat.st_mtime)),
                experiment_family=fam(rp), likely_role=role(fn),
                contains_raw_episode_data=int(fn.endswith(".jsonl") and "episode" in fn.lower()),
                contains_summary_statistics=int(ext in {".csv",".tsv"} or ("analysis" in fn.lower() and ext==".json")),
                contains_analysis_code=int(ext==".py"),
                contains_figures=int(ext in {".png",".pdf",".svg"}),
                contains_attack_results=int(bool(ATK.search(rp))),
                notes=""))
with open(f"{OUT}/00_inventory/all_files_inventory.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("all_files_inventory.csv:",len(rows),"files")

# experiment inventory (one row per experiment/batch) — curated + auto counts
def count_jsonl(p):
    try: return sum(1 for _ in open(p))
    except OSError: return ""
EXP=[
 dict(experiment_id="R9v2", experiment_family="R9", model="Qwen2.5-72B-AWQ", benchmark="BFCL-deep(base+miss_param)",
      task_family="multi_turn", conditions="C0-C5 x {compression,inflation}", N=count_jsonl(f"{REPO}/results/r9v2/confirmatory/confirmatory_episodes.jsonl"),
      number_of_tasks="~80", repeats=3, main_outcomes="clarification,verification_depth/effort,reads_before_write,first_write,tools,success,selector_score",
      raw_data_path="ir_mstu_stage2/results/r9v2/confirmatory/confirmatory_episodes.jsonl",
      processed_data_path="实验汇总/02_recomputed_metrics/*", analysis_script_path="ir_mstu_stage2/scripts/r9_attack/analyze_confirmatory.py",
      existing_report_path="reports/post_misroute/POST_MISROUTE_FINAL_RESEARCH_REPORT_CN.md", status="complete", attack_relevance="HIGH (L1 oversight)"),
 dict(experiment_id="R9v1-clean", experiment_family="R9", model="gemma-4-31b + mistral-small-3.2", benchmark="BFCL + ToolSandbox",
      task_family="multi_turn", conditions="C0-C5 x {compression,inflation}", N=count_jsonl(f"{REPO}/results/r9_attack/confirmatory/confirmatory_episodes.jsonl"),
      number_of_tasks="~30", repeats=5, main_outcomes="same as R9v2 (weak inflation C4-C3 signal)",
      raw_data_path="ir_mstu_stage2/results/r9_attack/confirmatory/confirmatory_episodes.jsonl",
      processed_data_path="实验汇总/02_recomputed_metrics/*", analysis_script_path="ir_mstu_stage2/scripts/r9_attack/analyze_confirmatory.py",
      existing_report_path="reports/post_misroute/...", status="complete(F, setup-artifact)", attack_relevance="MED"),
 dict(experiment_id="R8", experiment_family="R8", model="gemma/gpt-oss/mistral", benchmark="tau2(airline+retail)",
      task_family="36 tasks", conditions="C0-C4", N=2680, number_of_tasks=36, repeats=5,
      main_outcomes="reward,tool_calls,route; scaffold C1-C0", raw_data_path="ir_mstu_stage2/results/r8_full_episode/",
      processed_data_path="(tier_a CSVs)", analysis_script_path="", existing_report_path="ir_mstu_stage2/reports/r8_full_episode/",
      status="complete(calibrated null)", attack_relevance="MED(scaffold,model heterogeneity)"),
 dict(experiment_id="MISROUTE-tierA", experiment_family="MISROUTE", model="gemma/gpt-oss/mistral", benchmark="tau2",
      task_family="36 tasks", conditions="C0-C3", N=2680, number_of_tasks=36, repeats=5,
      main_outcomes="tool/arg/stage route distance; model heterogeneity; C0-C1-C2-C3 triangle",
      raw_data_path="tier_a_strengthening_20260722/*.csv", processed_data_path="(summary CSVs)", analysis_script_path="tier_a_strengthening_20260722/run_tier_a_strengthening.py",
      existing_report_path="MISROUTEbenchmark/", status="complete", attack_relevance="MED(route realization)"),
 dict(experiment_id="R6", experiment_family="R6", model="gemma/gpt-oss/mistral", benchmark="tau2+minimal",
      task_family="30 tasks", conditions="8 (valence x pressure)", N=2160, number_of_tasks=30, repeats=3,
      main_outcomes="n_tool,n_mutation,confirmation_rate,route,success; affect vs progression",
      raw_data_path="ir_mstu_stage2/results/r6_sensitivity/full_main_seq_eligible_20260626/interactional_metrics/per_run_metrics.jsonl",
      processed_data_path="实验汇总/06_process_control/language_act_channel/", analysis_script_path="", existing_report_path="ir_mstu_stage2/reports/r6_sensitivity/",
      status="complete", attack_relevance="MED(language-act x channel)"),
 dict(experiment_id="R7-D", experiment_family="R7-D", model="gemma/gpt-oss/mistral", benchmark="tau2",
      task_family="probes", conditions="P0/P2/attack", N=420, number_of_tasks="~20", repeats="",
      main_outcomes="P0 1.44 / P2 3.65 / attack 4.03 PASR; stub env; corr(POS,PASR)=-0.576",
      raw_data_path="ir_mstu_stage2/results/r7d_ipma/", processed_data_path="(report)", analysis_script_path="",
      existing_report_path="ir_mstu_stage2/reports/r7d_ipma/STEP1_PLACEBO_SOURCE_AUDIT_CN.md", status="complete(SUMMARY_ONLY here)", attack_relevance="MED(null hierarchy)"),
 dict(experiment_id="R7-C", experiment_family="R7-C", model="gemma/gpt-oss/mistral", benchmark="tau2",
      task_family="48 tasks", conditions="C0-C5", N=2592, number_of_tasks=48, repeats=3,
      main_outcomes="strict PASR 4.03 <= placebo 4.63", raw_data_path="ir_mstu_stage2/results/r7c_ipma/",
      processed_data_path="(report)", analysis_script_path="", existing_report_path="ir_mstu_stage2/reports/r7c_ipma/", status="complete(SUMMARY_ONLY here)", attack_relevance="LOW-MED(placebo)"),
]
with open(f"{OUT}/00_inventory/experiment_inventory.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(EXP[0].keys())); w.writeheader(); w.writerows(EXP)
print("experiment_inventory.csv:",len(EXP),"experiments")
with open(f"{OUT}/00_inventory/README.md","w") as f:
    f.write("# 00_inventory\n\n- `all_files_inventory.csv`: 递归扫描 /home/xqin5/llmlanguage 下所有相关文件(csv/json/jsonl/py/md/log/pdf...),标注实验家族、角色、是否含原始 episode/汇总统计/分析代码/图/攻击结果。\n- `experiment_inventory.csv`: 每行一个实验批次(R9v2/R9v1/R8/MISROUTE/R6/R7-D/R7-C),含模型/基准/条件/N/任务数/主指标/原始数据路径/报告路径/攻击相关度。\n\nN 为自动读取的 jsonl 行数(episode-level 批次)或报告实测值。\n")
print("README.md written")
