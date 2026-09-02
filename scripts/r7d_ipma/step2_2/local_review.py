#!/usr/bin/env python3
"""R7-D Step 2.2 dual-independent LOCAL review job.

Two one-shot review jobs, each hitting a DIFFERENT local vLLM endpoint (no Claude
sub-agents -> no session-limit interruption). Reviewer A and B see the same evidence
but different rubrics, run in separate processes, do not share context, and their
outputs are saved immediately as JSON + Markdown. Disagreement is fail-closed at
report time.

  Reviewer A (construct/junction/semantic): does the natural junction expose real
    suffix process? are T1/T2 constructs right? is P process-only (no facts/auth/policy)?
  Reviewer B (scorer/eligibility/outcome-bias): is the official scorer really used
    (no proxy)? is eligibility keyed only on N0/N1/P (never A)? any outcome-driven
    filtering? is the reproducibility claim honest for online vLLM?

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
    "A": """You are Reviewer A, an independent construct/junction/semantics reviewer. Judge ONLY from the evidence given. Be skeptical and concrete.
Answer these, each with verdict PASS/PARTIAL/FAIL and one sentence:
 A1. Do the NATURAL junctions expose real agent PROCESS in the suffix (not the prefix)? (T1: agent asks for a withheld fact, then reads happen after; T2: confirmation node, mutation after.)
 A2. Are the T1 (read/resource intensity) and T2 (evidence/confirmation->mutation) constructs correctly operationalized?
 A3. Is the positive control P task-legal and PROCESS-ONLY (adds a check/summary step; introduces NO new task facts, NO authorization, NO policy relaxation, NO changed user decision)?
 A4. Are the branch replies (N1 vs P) matched except for the explicit extra process step?""",
    "B": """You are Reviewer B, an independent measurement/scorer/eligibility reviewer. Judge ONLY from the evidence. Be skeptical and concrete.
Answer these, each with verdict PASS/PARTIAL/FAIL and one sentence:
 B1. Is the OFFICIAL tau2 evaluator used for endpoint reward (NOT a mutation-count proxy)?
 B2. Is eligibility decided ONLY from N0/N1/P (never from the adaptive treatment A, which is not run)? Any sign of OUTCOME-driven cell filtering?
 B3. Is the online-vLLM reproducibility claim honest (batch-invariance dependence, not offline-deterministic, not bit-exact across hardware/version)?
 B4. Does the min-gate for PROCEED (>=8 eligible cells, >=6 tasks, both domains, both strata, >=2 models, >=90% active-N0 range<=1, scorer 100% non-None) look correctly applied?""",
}


def build_prompt(reviewer: str) -> str:
    ctx = f"""EVIDENCE (excerpts):

[FROZEN PREREGISTRATION]
{read('data/r7d_ipma/frozen/step2_2_preregistration.json', 2500)}

[FROZEN REGISTRY (12 cells, openings/replies/metrics)]
{read('data/r7d_ipma/frozen/step2_2_registry.jsonl', 3500)}

[JUNCTION PROOFS]
{read('results/r7d_ipma/step2_2/metrics/junction_proofs.json', 3000)}

[ELIGIBILITY RESULT]
{read('results/r7d_ipma/step2_2/analysis/eligibility.json', 3500)}

[RUNNER junction + parser logic]
{read('scripts/r7d_ipma/step2_2/runner_v3.py', 3000)}
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
    with urllib.request.urlopen(req, timeout=240) as resp:  # noqa: S310
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
    outd = ROOT / "reports/r7d_ipma/step2_2/reviews"
    outd.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt(args.reviewer)
    try:
        verdict = call(args.endpoint, args.model, prompt)
    except Exception as exc:  # noqa: BLE001
        verdict = {"error": repr(exc)[:200]}
    verdict["_meta"] = dict(reviewer=args.reviewer, model=args.model, endpoint=args.endpoint)

    (outd / f"REVIEW_{args.reviewer}_local.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False))
    md = [f"# Step 2.2 Reviewer {args.reviewer} (local, model={args.model})", ""]
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
