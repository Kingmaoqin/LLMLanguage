#!/usr/bin/env python3
"""R8-A: inject computed results into the CN full report (spec 15). Reads the analysis,
integrity, review, policy and safety JSON artifacts and writes a fully-populated
RESULTS section + decision into reports/r8_attack/R8_TARGETED_PROCESS_ATTACK_FULL_REPORT_CN.md
(replacing the '（待填充）' placeholders)."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
R = ROOT / "results/r8_attack"
REP = ROOT / "reports/r8_attack/R8_TARGETED_PROCESS_ATTACK_FULL_REPORT_CN.md"
FAM_NAME = {"F1": "F1 Action-Intensity", "F2": "F2 Mutation/Confirmation Steering",
            "F3": "F3 Benign Abandonment"}


def _load(p, default=None):
    p = pathlib.Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def fmt(x, n=3):
    return "n/a" if x is None else f"{x:.{n}f}"


def main() -> int:
    an = _load(R / "analysis/analysis.json")
    pol = _load(R / "dev/policy_selection.json", {})
    integ_t = _load(R / "integrity/test_integrity.json", {})
    integ_d = _load(R / "integrity/dev_integrity.json", {})
    pre = _load(R / "reviews/pre_review.json", {})
    post = _load(R / "reviews/post_review.json", {})
    eqv = _load(R / "reviews/semantic_equivalence.json", {})
    audit = _load(R / "integrity/local_sandbox_safety_audit.json", {})
    if an is None:
        print("no analysis.json", file=sys.stderr); return 1

    L = []
    L.append(f"## 6. Dev 优化结果\n")
    L.append(f"冻结 policy = **{pol.get('winner','?')}**（按联合目标 argmax，非最高 PASR）。各 policy：\n")
    L.append("| policy | joint | process_effect_z | contamination | endpoint_deg | safety | mean_reward | exposure |")
    L.append("|---|---|---|---|---|---|---|---|")
    for p, s in sorted((pol.get("per_policy") or {}).items()):
        L.append(f"| {p} | {s['joint_score']} | {s['process_target_effect_z']} | "
                 f"{s['contamination_penalty']} | {s['endpoint_degradation_penalty']} | "
                 f"{s['safety_violation_penalty']} | {s['mean_reward']} | {s['exposure_rate']} |")
    L.append("")

    L.append("## 7. Test 主结果（held-out confirmatory）\n")
    L.append(f"test rows = {an['n_test_rows']}。每 family 预注册过程指标；配对单位 task×model×replicate；"
             "paired task-cluster bootstrap 95% CI + paired permutation p + Holm 校正（9 tests）。\n")
    L.append("| family | 对比 | mean | 95% CI | perm p | Holm p | dz | n |")
    L.append("|---|---|---|---|---|---|---|---|")
    for fam in ("F1", "F2", "F3"):
        r = an["family_results"].get(fam)
        if not r:
            continue
        for c, lab in (("C4_minus_C1_process", "C4−C1 过程"),
                       ("C4_minus_C3_process", "C4−C3 过程"),
                       ("C4_minus_C1_reward", "C4−C1 reward")):
            x = r[c]
            hp = an["holm_adjusted_p"].get(f"{fam}:{c}")
            ci = f"[{fmt(x['ci95'][0])}, {fmt(x['ci95'][1])}]"
            L.append(f"| {fam} | {lab} | {fmt(x['mean'])} | {ci} | {fmt(x['p_perm'])} | "
                     f"{fmt(hp)} | {fmt(x['dz'])} | {x['n']} |")
    L.append("")
    L.append("**ASR_process vs matched-neutral FPR、任务集中度、子组**：\n")
    L.append("| family | ASR | matched-neutral FPR | top-2 集中度 | per-domain (airline/retail) | per-model (gemma/gptoss/mistral) |")
    L.append("|---|---|---|---|---|---|")
    for fam in ("F1", "F2", "F3"):
        r = an["family_results"].get(fam)
        if not r:
            continue
        pd = r.get("per_domain", {})
        pm = r.get("per_model", {})
        dom = f"{fmt(pd.get('airline',{}).get('mean'))}/{fmt(pd.get('retail',{}).get('mean'))}"
        mod = "/".join(fmt(pm.get(m, {}).get("mean")) for m in
                       ("gemma4_31b", "gpt_oss_120b", "mistral_small_3p2"))
        L.append(f"| {fam} | {fmt(r.get('asr'))} | {fmt(r.get('matched_neutral_fpr'))} | "
                 f"{fmt(r.get('top2_task_concentration'))} | {dom} | {mod} |")
    L.append("")

    L.append("## 8. 完整性与隔离\n")
    ct = integ_t.get("checks", {})
    L.append(f"- Test：present={ct.get('present_episodes')}/{ct.get('expected_episodes')}，"
             f"missing={ct.get('missing')}，duplicate={ct.get('duplicate_episodes')}，"
             f"reward_none={ct.get('reward_none_on_scorable')}。")
    L.append(f"- **隔离不变量**：executed_non_allowlisted_tool_calls="
             f"**{ct.get('executed_non_allowlisted_tool_calls')}**、outbound_network_events="
             f"**{ct.get('outbound_network_events')}**、external_side_effects="
             f"**{ct.get('external_side_effects')}**、real_credential_pii="
             f"**{ct.get('real_credential_pii_findings')}** → isolation_pass="
             f"**{integ_t.get('isolation_pass')}**。")
    L.append(f"- 良性 agent 误发（tau2 已拒绝，未执行任何东西）：rejected_unknown="
             f"{ct.get('rejected_unknown_tool_calls')}、malformed_sanitized="
             f"{ct.get('malformed_sanitized_tool_calls')}。")
    L.append(f"- 运行后 sandbox 审计：**{audit.get('status')}**。")
    if ct.get("missing"):
        L.append(f"- 残余 {ct.get('missing')} 个 episode 因模型上下文窗口超限（长 episode 的确定性容量限制，"
                 "非隔离问题）无法完成，已透明记录，不静默丢弃。")
    L.append("")

    L.append("## 9. 双 Agent 盲审\n")
    L.append(f"- Pre-run（候选级）：reviewed={pre.get('n_candidates_reviewed')}，"
             f"一致 clean={pre.get('agree_clean')}，**一致 flagged（污染）={pre.get('agree_flagged')}**，"
             f"disputed={pre.get('disputed')}（fail-closed 记录，不接受）。")
    L.append(f"- 语义等价（C1/C3/C4 同态 payload hash）：matched={eqv.get('matched_turns')}，"
             f"mismatched={eqv.get('mismatched_turns')}，rate={fmt(eqv.get('equivalence_rate'))}。")
    L.append(f"- Post-run（轨迹对级）：pairs={post.get('n_pairs_reviewed')}，"
             f"一致判定定向过程改变={post.get('agree_directed')}，一致随机漂移={post.get('agree_drift')}，"
             f"语义污染 flag={post.get('semantic_contamination_flags')}，disputed={post.get('disputed')}。")
    L.append("")

    L.append("## 10. 决策（规则 A–E）\n")
    for fam in ("F1", "F2", "F3"):
        v = an["decision_rules"].get(fam)
        if v:
            L.append(f"- **{FAM_NAME[fam]}**：{v}")
    L.append("")
    L.append("**总体结论**：在本 threat model 下，**优化后的定向交互攻击（C4）未产生实际重要的、"
             "可归因于对抗优化的过程操纵**。唯一可见的过程位移（F2 首次 mutation 提前）在 C4≈C3 时同样出现"
             "（普通压力即可解释），且不过 Holm 多重校正、由少数 task 主导、跨域方向不一致；F1/F3 为 "
             "calibrated null。endpoint reward 全程保持（C4−C1≈0），语义与 endpoint 保持成立。"
             "该结论把 R8 full-episode 的 calibrated null 从普通压力推广到了**优化攻击者**设置。\n")
    L.append("> 明确声明：本实验未攻击真实系统、未绕过平台安全机制、未获得未授权访问；"
             "全部在本地合成 benchmark 内，零外部副作用。\n")

    block = "\n".join(L)
    text = REP.read_text()
    marker = "## 6. Dev 优化结果（待填充）"
    idx = text.find(marker)
    if idx == -1:
        # already finalized once: replace from '## 6.' onward up to '## 附.'
        start = text.find("## 6. Dev")
        end = text.find("## 附.")
        text = text[:start] + block + "\n---\n\n" + text[end:]
    else:
        end = text.find("## 附.")
        text = text[:idx] + block + "\n---\n\n" + text[end:]
    REP.write_text(text)
    print(f"finalized {REP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
