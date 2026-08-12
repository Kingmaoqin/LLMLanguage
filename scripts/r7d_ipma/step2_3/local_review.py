#!/usr/bin/env python3
"""R7-D Step 2.3 dual-independent LOCAL review job.

Two one-shot review jobs, each hitting a DIFFERENT local vLLM endpoint (no Claude
sub-agents -> no session-limit interruption). Reviewer A and B see the same evidence
but different rubrics, run in separate processes, do not share context, and their
outputs are saved immediately as JSON + Markdown.

  Reviewer A (eligibility/construct/outcome-bias): are the T1 eligibility criteria
    (baseline+exposure+repro+positive-control) applied only to N0/N1/P (never A)? Is
    the candidate pool blind (task-type only, not PASR / mid-phase results)? Is the
    "expansion barely raised eligible count" conclusion honest?
  Reviewer B (T2 scorer-components/null-vs-artifact): is the 7-class T2 taxonomy
    grounded in the OFFICIAL scorer's DB + COMMUNICATE components (not a proxy)? Is
    the dominant "agent_did_not_execute_mutation" a REAL behavior or a measurement
    artifact? Were the zero communicate-fail classes reachable (is the null real)?
    Is the gemma context-window truncation caveat correctly disclosed?

Usage: local_review.py --reviewer A --endpoint http://127.0.0.1:8192/v1 --model gpt-oss
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]


def read(p, n=4000):
    fp = ROOT / p
    return fp.read_text()[:n] if fp.exists() else f"(missing {p})"


RUBRIC = {
    "A": """You are Reviewer A, an independent eligibility/construct/outcome-bias reviewer for R7-D Step 2.3.
This step ONLY expands the candidate pool (T1=8 tasks, T2=12 tasks; retail+airline; tau2 1.0.0) and re-measures
T1 eligibility + decomposes T2 failure. Adaptive treatment A is NOT run. Judge ONLY from the evidence. Be skeptical and concrete.
Answer each with verdict PASS/PARTIAL/FAIL and one sentence:
 A1. Is T1 eligibility decided ONLY from N0(repeat)/N1(neutral)/P(positive-control) branches, never from any treatment-A outcome?
 A2. Are the four T1 gates (baseline reward=1 >=4/5; exposure >=2 tool events >=4/5; reproducibility active-N0 range<=1 and identical tool sequence; positive-control P moves the primary metric above N1 mean on >=3/5) reasonable and applied without leakage?
 A3. Was the candidate pool selected BLINDLY (official-scorer availability + task type T1/T2 only), NOT by historical PASR or this phase's intermediate results?
 A4. Is the honest conclusion supported: expanding from 4->8 T1 tasks kept eligible cells at 5 (bottleneck is the positive-control gate, not reproducibility), so the fixed-budget expansion did NOT deliver >=8 eligible cells / >=6 tasks / any T2?""",
    "B": """You are Reviewer B, an independent T2-decomposition / scorer-component reviewer for R7-D Step 2.3.
The goal is to attribute T2 non-identifiability to one of 7 causes. Judge ONLY from the evidence. Be skeptical and concrete.
Answer each with verdict PASS/PARTIAL/FAIL and one sentence:
 B1. Is the T2 failure taxonomy grounded in the OFFICIAL tau2 evaluator's separate DB (ENV) and COMMUNICATE (NL-judge) reward components, not a mutation-count proxy?
 B2. Is the dominant class "agent_did_not_execute_mutation" (36/67) a REAL agent behavior (reached confirmation, executed no mutation, did NOT keep asking) rather than a measurement/parser artifact?
 B3. The classes "db_correct_but_communicate_fail", "db_wrong_and_communicate_fail" and "insufficient_user_decision_info" are all ZERO. Given COMMUNICATE checks were exercised in 15/67 runs, is treating these zeros as a REAL null (not measurement absence) justified?
 B4. Is the gemma context-window truncation (7681 > 7680 tokens on some T2 cells -> BATTERY_FAIL/PREFIX_FAIL) correctly excluded/flagged as a measurement caveat rather than counted as agent behavior?""",
}


def build_prompt(reviewer: str) -> str:
    ctx = f"""EVIDENCE (excerpts):

[FROZEN REGISTRY (T1=8, T2=12; openings/replies/metrics/selection_basis)]
{read('data/r7d_ipma/frozen/step2_3_registry.jsonl', 4000)}

[ANALYSIS SUMMARY (T1 eligibility per cell + T2 failure decomposition)]
{read('results/r7d_ipma/step2_3/analysis/summary.json', 5000)}

[T2 SCORER COMPONENTS + 7-class classifier]
{read('scripts/r7d_ipma/step2_3/scorer_components.py', 3000)}

[ANALYSIS + ELIGIBILITY LOGIC]
{read('scripts/r7d_ipma/step2_3/analyze_2_3.py', 2500)}

[RUN LOG TAIL (junction / diagnostic outcomes, context-window failures)]
{read('logs/step2_3.log', 2500)}
"""
    return (RUBRIC[reviewer] + "\n\n" + ctx +
            '\n\nReturn STRICT JSON only: {"verdicts":[{"id":"A1","verdict":"PASS|PARTIAL|FAIL","note":"..."},...],'
            '"overall":"one-sentence bottom line","biggest_concern":"..."}')


def call(endpoint, model, prompt, max_tokens=2000):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.0, "max_tokens": max_tokens,
               "response_format": {"type": "json_object"}}
    req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer EMPTY"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:  # noqa: S310
        body = json.loads(resp.read().decode())
    msg = body["choices"][0]["message"]
    content = (msg.get("content") or "") + (msg.get("reasoning_content") or "")
    m = re.search(r"\{.*\}", content, re.S)
    return json.loads(m.group(0)) if m else {"raw": content[:500]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviewer", required=True, choices=["A", "B"])
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--model", required=True)
    args = ap.parse_args()
    outd = ROOT / "reports/r7d_ipma/step2_3/reviews"
    outd.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt(args.reviewer)
    try:
        verdict = call(args.endpoint, args.model, prompt)
    except Exception as exc:  # noqa: BLE001
        verdict = {"error": repr(exc)[:200]}
    verdict["_meta"] = dict(reviewer=args.reviewer, model=args.model, endpoint=args.endpoint)

    (outd / f"REVIEW_{args.reviewer}_local.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False))
    md = [f"# Step 2.3 Reviewer {args.reviewer} (local, model={args.model})", ""]
    for v in verdict.get("verdicts", []):
        md.append(f"- **{v.get('id')}** {v.get('verdict')}: {v.get('note')}")
    md.append("")
    md.append(f"**Overall**: {verdict.get('overall', verdict.get('error', 'n/a'))}")
    md.append(f"**Biggest concern**: {verdict.get('biggest_concern', 'n/a')}")
    (outd / f"REVIEW_{args.reviewer}_local.md").write_text("\n".join(md))
    print(f"Reviewer {args.reviewer} ({args.model}): "
          f"{[v.get('verdict') for v in verdict.get('verdicts', [])]}")
    print(f"wrote {outd / f'REVIEW_{args.reviewer}_local.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
