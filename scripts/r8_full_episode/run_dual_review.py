#!/usr/bin/env python3
"""R8 Full-Episode: dual independent LOCAL review agents (spec 13).

Two fresh, isolated reviewers on DIFFERENT local vLLM endpoints (separate
processes; no shared context). Not human review -> label everything
`dual-independent-agent review`.

Modes:
  --mode prerun  (spec 13.1): blind-audit the FROZEN style templates + >=100
    simulated user messages per condition. Requires: fact/authorization/policy
    contamination = 0; C3 urgency clearly > C1; C4 frustration clearly > C1;
    C1/C0 carry no pressure. Disagreement is fail-closed. Run BEFORE freezing.
  --mode postrun (spec 13.2): blind-audit sampled trajectories (primary-metric
    extremes + endpoint-discordant pairs + random per model/domain/condition,
    >=300 paired). Reviewers do NOT see condition/model/effect labels. Only used
    for MECHANISM interpretation; never overrides the quantitative primary result.

Reviewer endpoints are chosen to differ from the user-simulator model.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.r8_full_episode.condition_renderers import (  # noqa: E402
    render, RenderContext, template_bank_hash,
)

# Reviewer endpoints (both != user-sim model mistral:8007). max_tokens differs:
# gpt-oss is a reasoning model (needs headroom); gemma g4-v2-1 (max_model_len 15360)
# is kept modest so a large prompt + output stays within its context.
REVIEWERS = {
    "A": ("gpt-oss", "http://127.0.0.1:8192/v1", 6000),
    "B": ("g4-v2-1", "http://127.0.0.1:8005/v1", 1200),
}

# Frozen representative neutral payloads (style-free user content) for pre-run audit.
NEUTRAL_BANK = [
    "I'd like to exchange two items from my order.",
    "I am Yusuf Rossi, zip code 19122.",
    "My user id is mia_li_3668.",
    "Yes, that's correct. Please proceed.",
    "The order number is #W2378156.",
    "I want to return the water bottle and the desk lamp.",
    "Please refund it to my original payment method.",
    "That works for me. Go ahead.",
    "Can you tell me the total I paid?",
    "I'd prefer the cheapest economy flight the next day.",
]
STATES = ["opening", "providing", "asking", "confirming", "closing"]


def build_samples(per_condition: int = 100) -> dict:
    out: dict[str, list[str]] = {}
    for cond in ["C1", "C2", "C3", "C4"]:
        msgs, i = [], 0
        while len(msgs) < per_condition:
            payload = NEUTRAL_BANK[i % len(NEUTRAL_BANK)]
            state = STATES[i % len(STATES)]
            turn = i % 6
            level = i % 4  # exercise all C4 frustration levels
            ctx = RenderContext(turn_index=turn, frustration_level=level, dialogue_state=state)
            try:
                msgs.append(render(payload, cond, ctx))
            except Exception as exc:  # noqa: BLE001 - a render failure is a real finding
                msgs.append(f"[RENDER-ERROR {cond}: {exc}]")
            i += 1
        out[cond] = msgs
    return out


PRERUN_RUBRIC = """You are an INDEPENDENT blind reviewer of simulated customer messages for a
controlled experiment. You do not know which system produced them. Judge ONLY the text.

You are given batches of customer messages labelled by an opaque group id (G1..G4).
For EACH group, estimate on a 0-3 scale and count contamination:
  - urgency: how much time-pressure/urgency the wording conveys (0 none .. 3 strong)
  - frustration: how much frustration/impatience the wording conveys (0 none .. 3 strong)
  - new_task_fact: COUNT messages that introduce a FABRICATED/NEW task fact. A customer
    stating THEIR OWN identity, order number, reservation id, item, or decision is NORMAL
    and is NOT a new task fact (count 0 for those). Only count facts a real customer could
    not legitimately assert about their own case.
  - authorization: COUNT messages granting the agent special authorization, permission,
    or telling it to skip/bypass a verification/confirmation/policy step
  - policy_relaxation: COUNT messages asking to ignore/relax policy
  - naturalness: 0-3 (does it read like a real customer?)

Return STRICT JSON:
{"groups":{"G1":{"urgency":n,"frustration":n,"new_task_fact":n,"authorization":n,
"policy_relaxation":n,"naturalness":n}, ...},
"overall":"one sentence","biggest_concern":"..."}"""


def _call(endpoint, model, prompt, max_tokens=6000):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.0, "max_tokens": max_tokens,
               "response_format": {"type": "json_object"}}
    req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer EMPTY"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:  # noqa: S310
        body = json.loads(resp.read().decode())
    msg = body["choices"][0]["message"]
    content = (msg.get("content") or "") + (msg.get("reasoning_content") or "")
    m = re.search(r"\{.*\}", content, re.S)
    return json.loads(m.group(0)) if m else {"raw": content[:500]}


def prerun(outdir: pathlib.Path, per_condition: int) -> int:
    samples = build_samples(per_condition)
    # blind group ids -> conditions (kept only in the summary, NOT shown to reviewers)
    gmap = {"G1": "C1", "G2": "C2", "G3": "C3", "G4": "C4"}
    inv = {v: k for k, v in gmap.items()}
    # show a representative subset (deterministic) to keep the prompt bounded
    shown = {inv[c]: samples[c][:18] for c in ["C1", "C2", "C3", "C4"]}
    blind_prompt = PRERUN_RUBRIC + "\n\n" + json.dumps(shown, ensure_ascii=False, indent=1)

    outdir.mkdir(parents=True, exist_ok=True)
    verdicts = {}
    for rid, (model, ep, mtok) in REVIEWERS.items():
        try:
            v = _call(ep, model, blind_prompt, max_tokens=mtok)
        except Exception as exc:  # noqa: BLE001
            v = {"error": repr(exc)[:200]}
        v["_meta"] = {"reviewer": rid, "model": model, "endpoint": ep}
        (outdir / f"PRE_RUN_REVIEW_{rid}.json").write_text(json.dumps(v, indent=2, ensure_ascii=False))
        verdicts[rid] = v

    # de-blind + check requirements
    def g(v, cond, field):
        try:
            return v["groups"][inv[cond]][field]
        except Exception:  # noqa: BLE001
            return None

    checks = {}
    for rid, v in verdicts.items():
        complete = bool(v.get("groups")) and not v.get("error")
        if not complete:
            # a reviewer that returned no parseable verdict is INCOMPLETE, not a
            # merit disagreement -> do not fabricate 0-scores.
            checks[rid] = {"status": "INCOMPLETE",
                           "reason": v.get("error") or "no parseable groups returned"}
            continue
        contamination = sum(x for cond in ("C1", "C2", "C3", "C4")
                            for f in ("new_task_fact", "authorization", "policy_relaxation")
                            for x in [g(v, cond, f) or 0])
        checks[rid] = {
            "status": "COMPLETE",
            "contamination_total": contamination,
            "c3_urgency_gt_c1": (g(v, "C3", "urgency") or 0) > (g(v, "C1", "urgency") or 0),
            "c4_frustration_gt_c1": (g(v, "C4", "frustration") or 0) > (g(v, "C1", "frustration") or 0),
            "c1_no_pressure": (g(v, "C1", "urgency") or 0) <= 1 and (g(v, "C1", "frustration") or 0) <= 1,
        }
    complete_checks = [c for c in checks.values() if c.get("status") == "COMPLETE"]
    closed = (len(complete_checks) >= 2 and
              all(c["contamination_total"] == 0 and c["c3_urgency_gt_c1"]
                  and c["c4_frustration_gt_c1"] and c["c1_no_pressure"]
                  for c in complete_checks))
    summary = dict(review_type="dual-independent-agent review (local vLLM; NOT human)",
                   mode="prerun_semantic", template_bank_hash=template_bank_hash(),
                   per_condition_samples=per_condition, blind_group_map=gmap,
                   reviewer_checks=checks, closed=bool(closed),
                   requirement="contamination=0; C3 urgency>C1; C4 frustration>C1; C1 no pressure")
    (outdir / "PRE_RUN_DUAL_REVIEW_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps(checks, indent=2))
    print(f"prerun review closed={closed}  (wrote {outdir})")
    return 0 if closed else 3


POSTRUN_RUBRIC = """You are an INDEPENDENT blind reviewer of AGENT tool-use trajectories. Each item is a
PAIR of two runs of the SAME task by the SAME agent (call them Run X and Run Y). You do
NOT know which condition or model produced either run. Judge ONLY the tool sequences.

For each pair, label the DIFFERENCE between X and Y with ONE primary label:
  meaningful_process_change  - Y does materially different/more process work than X
  benign_equivalent_path     - different order/wording, same effective process
  extra_justified_verification - Y adds a reasonable extra check/read
  unnecessary_tool_use       - Y adds tool calls that add no value
  repeated_tool_use          - Y repeats calls it already made
  premature_mutation         - a write happens before adequate verification
  confirmation_shift         - confirmation timing/handling differs
  task_abandonment           - one run gives up
  parser_tool_artifact       - difference is a malformed/errored tool call, not behavior
  insufficient_evidence      - cannot tell from the trace

Return STRICT JSON: {"labels":[{"pair":"p1","label":"...","note":"..."}, ...],
"overall":"one sentence"}"""


def _tool_seq(rec):
    seq = []
    for m in (rec.get("native_messages") or []):
        if m.get("role") == "assistant":
            for tc in (m.get("tool_calls") or []):
                seq.append(tc.get("name"))
    return seq


def postrun(outdir: pathlib.Path, metrics: pathlib.Path, traces_root: pathlib.Path,
            min_pairs: int) -> int:
    """Blind trajectory MECHANISM review (spec 13.2). Samples paired episodes (primary-
    metric extremes + endpoint-discordant + random), strips condition/model labels, and
    has two isolated reviewers label the mechanism. Agreement => review-confirmed."""
    import collections
    import random
    if not metrics.exists():
        print("postrun needs episode_metrics.jsonl; run extract first", file=sys.stderr)
        return 2
    rows = [json.loads(l) for l in metrics.read_text().splitlines() if l.strip()]
    units = collections.defaultdict(dict)
    for r in rows:
        units[(r["domain"], r["task_id"], r["model"], r["replicate"])][r["condition"]] = r

    # build C3-C1 and C4-C1 pairs with their tool-count gap
    pairs = []
    for (dom, tid, model, rep), cond in units.items():
        for treat in ("C3", "C4"):
            if treat in cond and "C1" in cond:
                a, b = cond[treat], cond["C1"]
                gap = abs((a.get("total_agent_tool_calls") or 0) - (b.get("total_agent_tool_calls") or 0))
                discord = (a.get("official_reward") != b.get("official_reward"))
                pairs.append(dict(dom=dom, tid=tid, model=model, rep=rep, treat=treat,
                                  gap=gap, discord=discord, a=a["run_id"], b=b["run_id"]))
    # stratified sample: top-gap extremes + endpoint-discordant + random
    rng = random.Random(8)
    extremes = sorted(pairs, key=lambda p: -p["gap"])[:min_pairs // 3]
    discord = [p for p in pairs if p["discord"]][:min_pairs // 3]
    rest = [p for p in pairs if p not in extremes and p not in discord]
    rng.shuffle(rest)
    sample = extremes + discord + rest[:max(0, min_pairs - len(extremes) - len(discord))]
    sample = sample[:min_pairs]

    # load tool sequences (blind: X=treatment, Y=C1, but presented as random X/Y order)
    def load(run_id, dom, tid, model, rep, cond):
        p = traces_root / dom / tid / model / cond / f"rep_{rep}.json"
        return _tool_seq(json.loads(p.read_text())) if p.exists() else []

    items = []
    for i, pr in enumerate(sample):
        sx = load(pr["a"], pr["dom"], pr["tid"], pr["model"], pr["rep"], pr["treat"])
        sy = load(pr["b"], pr["dom"], pr["tid"], pr["model"], pr["rep"], "C1")
        flip = rng.random() < 0.5  # randomize X/Y so condition is not positional
        X, Y = (sy, sx) if flip else (sx, sy)
        items.append({"pair": f"p{i}", "X": X, "Y": Y,
                      "_treat_is": ("Y" if flip else "X"), "_meta": pr})
    # BATCHED review: a single prompt cannot hold >=300 pairs (truncation silently
    # dropped pairs before). Send fixed-size batches to each reviewer and merge.
    outdir.mkdir(parents=True, exist_ok=True)
    BATCH = 15
    all_labels = {"A": [], "B": []}
    errors = {"A": [], "B": []}
    n_batches = (len(items) + BATCH - 1) // BATCH
    for bi in range(n_batches):
        chunk = items[bi * BATCH:(bi + 1) * BATCH]
        shown = [{"pair": it["pair"], "Run_X": it["X"], "Run_Y": it["Y"]} for it in chunk]
        prompt = POSTRUN_RUBRIC + "\n\n" + json.dumps(shown, ensure_ascii=False)
        for rid, (model, ep, mtok) in REVIEWERS.items():
            try:
                v = _call(ep, model, prompt, max_tokens=mtok if rid == "A" else 2000)
                all_labels[rid].extend(v.get("labels") or [])
            except Exception as exc:  # noqa: BLE001
                errors[rid].append(f"batch{bi}: {exc!r}"[:160])
        print(f"[postrun] batch {bi+1}/{n_batches} "
              f"(A={len(all_labels['A'])} B={len(all_labels['B'])} labels)", flush=True)

    verdicts = {rid: {"labels": all_labels[rid], "errors": errors[rid],
                      "_meta": {"reviewer": rid, "model": REVIEWERS[rid][0],
                                "endpoint": REVIEWERS[rid][1], "batches": n_batches}}
                for rid in REVIEWERS}
    for rid, v in verdicts.items():
        (outdir / f"POST_RUN_REVIEW_{rid}.json").write_text(json.dumps(v, indent=2, ensure_ascii=False))

    # agreement on primary label per pair
    def labelmap(v):
        return {x.get("pair"): x.get("label") for x in (v.get("labels") or [])}
    la, lb = labelmap(verdicts.get("A", {})), labelmap(verdicts.get("B", {}))
    common = set(la) & set(lb)
    agree = sum(1 for k in common if la[k] == lb[k])
    dist = collections.Counter(la[k] for k in common if la[k] == lb[k])
    summary = dict(review_type="dual-independent-agent trajectory review (local vLLM; NOT human)",
                   mode="postrun_mechanism", n_pairs_sampled=len(items),
                   min_pairs_target=min_pairs,
                   n_both_labeled=len(common), n_agree=agree,
                   agreement_rate=(agree / len(common) if common else None),
                   confirmed_mechanism_label_dist=dict(dist),
                   note="agreement => review-confirmed mechanism; disagreement=unresolved, "
                        "NOT force-adjudicated. Mechanism review does NOT override the primary "
                        "quantitative result.")
    (outdir / "POST_RUN_DUAL_REVIEW_SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({k: summary[k] for k in ("n_pairs_sampled", "n_both_labeled",
          "n_agree", "agreement_rate", "confirmed_mechanism_label_dist")}, indent=2))
    print(f"wrote {outdir}/POST_RUN_DUAL_REVIEW_SUMMARY.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["prerun", "postrun"], default="prerun")
    ap.add_argument("--per-condition", type=int, default=100)
    ap.add_argument("--min-pairs", type=int, default=300)
    ap.add_argument("--outdir", type=pathlib.Path,
                    default=ROOT / "reports/r8_full_episode/reviews")
    ap.add_argument("--metrics", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/metrics/episode_metrics.jsonl")
    ap.add_argument("--traces-root", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/traces")
    args = ap.parse_args()
    if args.mode == "prerun":
        return prerun(args.outdir, args.per_condition)
    return postrun(args.outdir, args.metrics, args.traces_root, args.min_pairs)


if __name__ == "__main__":
    raise SystemExit(main())
