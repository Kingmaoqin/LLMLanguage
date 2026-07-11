#!/usr/bin/env python3
"""R7-D Step 1-B (pre-registration): choose the 6 tasks for the P0/P2 placebo probe.

Selection uses ONLY the neutral_control arm (mean tool calls per task) and domain
distinctness. It never reads any attack condition, r7b_pairs.csv, or PASR. The
placebo decomposition asks how much neutral-arm variance is runtime noise, so the
probe must span the tool-activity range that drives that variance -- hence a
high-activity / low-activity stratification.

Writes data/r7d_ipma/frozen/step1b_preregistration.json, which is committed to git
BEFORE any probe run executes.
"""
from __future__ import annotations

import collections
import glob
import hashlib
import json
import pathlib
import statistics
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
TRACES = REPO / "results/r7c_ipma/full/live_20260710_000752/traces"
OUT = REPO / "data/r7d_ipma/frozen/step1b_preregistration.json"

N_PER_BAND = 2
REPEATS = 5
MODELS = ["gemma4_31b", "gpt_oss_120b", "mistral_small_3p2"]


def main() -> int:
    # ---- neutral-arm activity only ----
    activity: dict[str, list[int]] = collections.defaultdict(list)
    domain: dict[str, str] = {}
    for path in glob.glob(str(TRACES / "*.json")):
        d = json.loads(pathlib.Path(path).read_text())
        if d["condition"] != "neutral_control":
            continue  # attack arms are never opened here
        activity[d["task_id"]].append(len(d.get("tool_events") or []))
        domain[d["task_id"]] = d["run_meta"].get("domain")

    stats = [
        dict(
            task_id=t,
            domain=domain[t],
            neutral_mean_tools=statistics.mean(v),
            neutral_zero_rate=sum(1 for x in v if x == 0) / len(v),
            n_neutral_runs=len(v),
        )
        for t, v in activity.items()
    ]
    # Three activity bands, 2 tasks each. A "3 highest + 3 lowest" rule (v1) was
    # written first and discarded WITHOUT running it: its low stratum selected three
    # tasks whose neutral mean tool calls are exactly 0.00 (100% zero-tool runs), so
    # P0 variance there is identically zero and the probe would measure nothing. The
    # informative regime is the MARGINAL band, where a run sometimes calls a tool and
    # sometimes does not -- that is where run-to-run instability can masquerade as a
    # process effect. v2 therefore spans all three bands. The revision is driven purely
    # by neutral-arm variance structure; no attack condition or PASR was consulted.
    def band(r: dict) -> str:
        m = r["neutral_mean_tools"]
        if m >= 2.0:
            return "HIGH"
        if m > 0.0:
            return "MARGINAL"
        return "ZERO"

    chosen: list[dict] = []
    used_domains: set[str] = set()
    for b in ["HIGH", "MARGINAL", "ZERO"]:
        pool = sorted(
            [r for r in stats if band(r) == b],
            key=lambda r: (-r["neutral_mean_tools"], r["task_id"]),
        )
        n = 0
        for r in pool:
            if n == N_PER_BAND:
                break
            if r["domain"] in used_domains:
                continue
            used_domains.add(r["domain"])
            r = dict(r, band=b)
            chosen.append(r)
            n += 1
    high = [r for r in chosen if r["band"] == "HIGH"]
    low = [r for r in chosen if r["band"] != "HIGH"]

    prereg = {
        "preregistration_id": "r7d_step1b_placebo_probe_v2",
        "frozen_at": "2026-07-10",
        "purpose": "Decompose the R7-C placebo into P0 (runtime nondeterminism) and P2 (neutral surface form).",
        "selection_rule": (
            "From the neutral_control arm ONLY, bin the 48 tasks by mean tool calls into "
            "HIGH (>=2), MARGINAL (0<m<2) and ZERO (=0). Take 2 tasks per band, all 6 domains "
            "distinct, ties broken by lexicographic task_id. No attack condition, no pair "
            "file, and no PASR is read."
        ),
        "superseded_rule_v1": (
            "'3 highest + 3 lowest' was authored first and DISCARDED WITHOUT BEING RUN: its low "
            "stratum picked three tasks with neutral mean tool calls of exactly 0.00 (100% "
            "zero-tool runs), where P0 variance is identically zero and the probe would measure "
            "nothing. The MARGINAL band -- tasks that sometimes call a tool and sometimes do not "
            "-- is the regime where run-to-run instability can be mistaken for a process effect, "
            "so it must be covered. Revision motivated solely by neutral-arm variance structure."
        ),
        "forbidden_inputs": ["any attack condition trace", "r7b_pairs.csv", "PASR", "pasr_success_explanations.csv"],
        "selected_tasks": chosen,
        "arms": {
            "P0_exact_repeat": {
                "description": "Identical neutral text, identical initial state, identical config, run REPEATS times.",
                "template_suffix": "01",
                "state_seed": 300,
                "repeats": REPEATS,
                "measures": "serving / runtime nondeterminism only",
            },
            "P1_seed_only": {
                "description": (
                    "NOT RUNNABLE and NOT FABRICATED. R7-C never passes a sampling seed to the "
                    "model: the chat payload in src/r6/minimal_live_agent.py contains only "
                    "{model, messages, tools, tool_choice, temperature, max_tokens}, and "
                    "temperature=0.0 (greedy). The integer called 'seed' in R7-C selects the "
                    "template (seed % n_templates) and is stamped into the state dict; it is not "
                    "an RNG seed. Sampling/seed effect is therefore STRUCTURALLY_ZERO by construction."
                ),
                "status": "STRUCTURALLY_ZERO",
            },
            "P2_neutral_paraphrase": {
                "description": "Same initial state and config; neutral text varied across 5 distinct neutral templates.",
                "template_suffixes": ["01", "02", "03", "04", "05"],
                "state_seed": 300,
                "repeats": 1,
                "measures": "benign neutral surface-form variation",
            },
            "P3_r7c_protocol": {
                "description": "Offline audit of the placebo R7-C actually ran (neutral seed_i vs neutral seed_j).",
                "status": "OFFLINE_AUDIT_ONLY",
            },
        },
        "models": MODELS,
        "budget": {
            "P0_runs": len(chosen) * len(MODELS) * REPEATS,
            "P2_runs": len(chosen) * len(MODELS) * 5,
            "total_new_model_runs": len(chosen) * len(MODELS) * (REPEATS + 5),
        },
        "execution_boundary": "All model calls go to local vLLM on 127.0.0.1 (ports 8005/8007/8192). No external service is contacted; no real database is mutated.",
        "primary_readout": (
            "P0 flip rate of 'did the agent call any tool at all' across identical repeats, "
            "and the per-(model,task) SD of n_tool_events under P0 vs P2 vs the R7-C neutral noise floor."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(prereg, indent=2, ensure_ascii=False))
    h = hashlib.sha256(OUT.read_bytes()).hexdigest()

    print("=== Step 1-B probe task selection (neutral arm only) ===")
    print(f"{'band':>9s}  {'task_id':42s} {'domain':16s} {'mean_tools':>10s} {'zero_rate':>10s}")
    for r in chosen:
        print(f"{r['band']:>9s}  {r['task_id']:42s} {r['domain']:16s} {r['neutral_mean_tools']:10.2f} {r['neutral_zero_rate']:10.1%}")
    print(f"\nbudget: P0={prereg['budget']['P0_runs']} + P2={prereg['budget']['P2_runs']} "
          f"= {prereg['budget']['total_new_model_runs']} new local runs")
    print(f"\nwrote {OUT.relative_to(REPO)}\nsha256={h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
