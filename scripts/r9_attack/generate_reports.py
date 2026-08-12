#!/usr/bin/env python3
"""Generate the R9 deliverable reports (spec 21) from the frozen result artifacts.

Reads the calibration decision, frozen attackers, confirmatory analysis, integrity check,
and dual-review outputs, and writes the four spec-21 markdown reports plus the final
[R9 STATUS] block. Everything is derived from files on disk, so the reports never diverge
from the evidence (the same principle as check_integrity's double recompute).
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.common import paths  # noqa: E402
from scripts.r9_attack.common.io_utils import read_json, write_atomic  # noqa: E402


def _load(path: pathlib.Path, default=None):
    try:
        return read_json(path)
    except Exception:
        return default


def _fmt_gate(gates: dict) -> str:
    if not gates:
        return "- (analysis not run)\n"
    lines = []
    g1 = gates.get("G1_baseline_capability", {})
    lines.append(f"- G1 baseline capability: " + ", ".join(f"{b}={'PASS' if v.get('pass') else 'FAIL'}" for b, v in g1.items()))
    g2 = gates.get("G2_scaffold_neutrality", {})
    lines.append(f"- G2 scaffold neutrality: " + ", ".join(f"{b}={'PASS' if v.get('pass') else 'FAIL'}" for b, v in g2.items()))
    g3 = gates.get("G3_positive_control", {})
    lines.append(f"- G3 positive control: " + ", ".join(f"{f}={'PASS' if v.get('pass') else 'FAIL'}" for f, v in g3.items()))
    g4 = gates.get("G4_attack_exposure", {})
    lines.append(f"- G4 attack exposure: {'PASS' if g4.get('pass') else 'FAIL'} "
                 f"(mean_iv={g4.get('mean_interventions', 0):.2f}, fallback={g4.get('neutral_fallback_rate', 0):.2f}, "
                 f"adaptive={g4.get('adaptive_share', 0):.2f})")
    lines.append(f"- ALL GATES PASS: {gates.get('all_pass')}")
    return "\n".join(lines) + "\n"


def _fmt_tests(tests: dict) -> str:
    if not tests:
        return "- (no confirmatory tests)\n"
    lines = []
    for name, t in tests.items():
        b = t.get("bootstrap", {})
        lines.append(
            f"- **{name}** ({t.get('contrast')}): mean={b.get('mean', 0):.3f} "
            f"CI=[{b.get('ci_low', 0):.3f}, {b.get('ci_high', 0):.3f}] "
            f"p_holm={t.get('p_holm', 1):.3f} d={t.get('standardized_effect', 0):.2f} "
            f"| endpoint {t.get('endpoint_transitions')} "
            f"| top2_task_share={t.get('concentration', {}).get('top2', 0):.2f}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    paths.ensure_dirs()
    calibration = _load(paths.SELECTED_MODELS, {})
    analysis = _load(paths.CONFIRMATORY / "analysis.json", {})
    integrity = _load(paths.CONFIRMATORY / "confirmatory_episodes_integrity.json", {})
    safety = _load(paths.SAFETY_AUDIT, {})
    env_manifest = _load(paths.ENVIRONMENT_MANIFEST, {})
    prereview = _load(paths.REVIEWS / "pre_run_review.json", {})
    postreview = _load(paths.REVIEWS / "post_run_review.json", {})
    confounder = _load(paths.CONFOUNDERS / "interaction.json", {})
    comp_attacker = _load(paths.COMPRESSION_ATTACKER, {})
    infl_attacker = _load(paths.INFLATION_ATTACKER, {})
    thresholds = _load(paths.PRACTICAL_THRESHOLDS, {})

    decision = analysis.get("decision", {})
    gates = analysis.get("gates", {})
    tests = analysis.get("tests", {})
    asr = analysis.get("asr_fpr", {})

    # --- Main report -------------------------------------------------------
    main_md = f"""# R9 Mechanism-Aligned Interactional Process Attacks — Full Report (spec 21)

Branch: `r9-mechanism-aligned-process-attack`
Scale: faithful-reduced (all stages / conditions / both benchmarks / both families / gates /
integrity / dual review present; episode counts reduced from the spec budget — see
`R9_EXECUTION_NOTES_CN.md`). Confirmatory uses the frozen-attacker fast path (spec 8.6/§2).

## 1. Authorized local sandbox scope (spec 0.2)
- Status: **{safety.get('status', 'MISSING')}**; outbound network blocked (active probe), all
  endpoints loopback/internal, attacker/reviewer tool access = none, synthetic resettable state.

## 2. Benchmarks / versions (spec 3)
- BFCL multi_turn_base (bfcl-eval), native `multi_turn_checker`.
- ToolSandbox multi-user-turn (Apple), native milestone evaluator; one subprocess per episode.
- Split counts: {env_manifest.get('counts')}; family balance: {env_manifest.get('family_balance')};
  non-overlapping: {env_manifest.get('non_overlapping')}.

## 3. Neutral model calibration + selection (spec 6)
- Decision: **{calibration.get('status')}**; selected: {calibration.get('selected_models')}.
- Per-model: {json.dumps(calibration.get('per_model', {}), ensure_ascii=False)[:1200]}

## 4. Frozen attackers (spec 8.6/13)
- Compression policy hash: {comp_attacker.get('policy_hash', 'n/a')}
- Inflation policy hash: {infl_attacker.get('policy_hash', 'n/a')}
- Practical thresholds: {json.dumps(thresholds, ensure_ascii=False)[:400]}

## 5. Confirmatory accounting + integrity (spec 18)
- Integrity: **{integrity.get('status', 'MISSING')}**; hard-fail flags: {integrity.get('hard_fail', {})}
- Double recompute mismatches: {integrity.get('double_recompute', {}).get('n_mismatch')}
- Accounting: {json.dumps(integrity.get('accounting', {}), ensure_ascii=False)[:600]}

## 6. Global gates (spec 12)
{_fmt_gate(gates)}

## 7. Confirmatory process tests (spec 14)
{_fmt_tests(tests)}

## 8. Endpoint-preserved ASR / matched-neutral FPR (spec 11.4)
- {json.dumps(asr, ensure_ascii=False)[:600]}

## 9. Pre-run + post-run dual review (spec 15)
- Pre-run (library/candidates): reviewed={prereview.get('n_candidates_reviewed')} pass_rate={prereview.get('pass_rate')}
- Post-run (trajectories): reviewed={postreview.get('n_reviewed')} agreement={postreview.get('agreement_rate')} labels={postreview.get('confirmed_label_counts')}
- Method: dual-independent-agent review (NOT human-validated).

## 10. Confounder / boundary module (spec 16)
- Interactions: {json.dumps(confounder, ensure_ascii=False)[:600]}

## 11. Decision (spec 19)
- **{decision.get('code')} — {decision.get('label')}**

{status_block(safety, env_manifest, calibration, gates, tests, asr, decision, integrity, postreview, confounder)}
"""
    out = write_atomic(paths.REPORTS / "R9_MECHANISM_ALIGNED_ATTACK_FULL_REPORT_CN.md", main_md)
    print(f"[reports] wrote {out}")
    print(status_block(safety, env_manifest, calibration, gates, tests, asr, decision, integrity, postreview, confounder))
    return 0


def status_block(safety, env, calibration, gates, tests, asr, decision, integrity, postreview, confounder) -> str:
    def t(name):
        x = tests.get(name, {})
        b = x.get("bootstrap", {})
        return f"mean={b.get('mean', 0):.3f} CI=[{b.get('ci_low', 0):.3f},{b.get('ci_high', 0):.3f}] p_holm={x.get('p_holm', 1):.3f}"
    return f"""## [R9 STATUS]

Safety scope:
- {safety.get('status', 'MISSING')}

Benchmarks/versions:
- BFCL multi_turn_base + ToolSandbox multi-user-turn (native evaluators)

Selected models:
- {calibration.get('selected_models')}

Episode accounting:
- {integrity.get('accounting', {}).get('n_records')} confirmatory records; recompute mismatches={integrity.get('double_recompute', {}).get('n_mismatch')}

Global gates:
- all_pass={gates.get('all_pass')}

Compression:
- C4-C1: {t('compression_C4_C1')}
- C4-C3: {t('compression_C4_C3')}
- ASR/FPR: {asr.get('compression', {})}

Inflation:
- C4-C1: {t('inflation_C4_C1')}
- C4-C3: {t('inflation_C4_C3')}
- ASR/FPR: {asr.get('inflation', {})}

Boundary/confounder:
- {json.dumps(confounder, ensure_ascii=False)[:300]}

Dual review:
- post-run agreement={postreview.get('agreement_rate')} labels={postreview.get('confirmed_label_counts')}

Decision:
- {decision.get('code')} — {decision.get('label')}
"""


if __name__ == "__main__":
    raise SystemExit(main())
