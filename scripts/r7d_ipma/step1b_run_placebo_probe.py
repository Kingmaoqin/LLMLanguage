#!/usr/bin/env python3
"""R7-D Step 1-B: run the P0 / P2 placebo probe against the local vLLM servers.

P0  identical neutral text, identical state, identical config, repeated 5x
    -> isolates serving / runtime nondeterminism.
P2  identical state and config, neutral text varied over 5 neutral templates
    -> isolates benign neutral surface-form variation.

P1 is not run: R7-C never seeds the sampler (see the pre-registration). Fabricating
it would be dishonest, so it is reported as STRUCTURALLY_ZERO instead.

R7-C could not separate these: its `seed` simultaneously selects the template
(seed % n_templates) and is stamped into the initial state, so "neutral seed_i vs
neutral seed_j" confounds wording with the state tag. This probe pins the template
and the state seed explicitly, which run_cell already supports.

All traffic goes to 127.0.0.1 vLLM. Nothing external is contacted.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.run_r7b_live import (  # noqa: E402
    R7BLiveExecutor,
    endpoint_ok,
    git_commit,
    load_models,
    load_tasks,
)
from src.r6.minimal_env import R6RunCell  # noqa: E402

PREREG = ROOT / "data/r7d_ipma/frozen/step1b_preregistration.json"
TEMPLATES = ROOT / "data/r7c_ipma/frozen/r7c_frozen_templates.jsonl"
REGISTRY = ROOT / "data/r7c_ipma/r7c_task_registry.csv"
OUT = ROOT / "results/r7d_ipma/step1/placebo_probe"

STATE_SEED = 300
TEMPERATURE = 0.0
MAX_STEPS = 60


def load_templates() -> dict[tuple[str, str], dict]:
    """(task_id, template_suffix) -> frozen neutral template row."""
    out = {}
    for line in TEMPLATES.open():
        r = json.loads(line)
        if r["condition"] != "neutral_control":
            continue
        out[(r["task_id"], r["template_id"].rsplit("__", 1)[-1])] = r
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--paraphrases", type=int, default=5)
    args = ap.parse_args()

    prereg = json.loads(PREREG.read_text())
    tasks_sel = prereg["selected_tasks"]
    models = load_models(prereg["models"])
    tasks = load_tasks()
    bank = load_templates()

    import csv

    registry_by_task = {r["task_id"]: r for r in csv.DictReader(REGISTRY.open())}

    for m in models:
        ok, msg = endpoint_ok(m)
        if not ok:
            raise SystemExit(f"local vLLM endpoint not ready for {m['alias']}: {msg}")
        print(f"  endpoint OK  {m['alias']:18s} {m['base_url']}")

    (OUT / "traces").mkdir(parents=True, exist_ok=True)
    commit = git_commit()

    # Build the full cell list: (arm, task, model, replicate, template_suffix)
    cells = []
    for t in tasks_sel:
        tid = t["task_id"]
        for m in models:
            for i in range(args.repeats):
                cells.append(dict(arm="P0", task=t, model=m, rep=i, tpl="01"))
            for j in range(args.paraphrases):
                sfx = f"{j+1:02d}"
                if (tid, sfx) not in bank:
                    continue
                cells.append(dict(arm="P2", task=t, model=m, rep=j, tpl=sfx))

    print(f"\ncells to run: {len(cells)}  "
          f"(P0={sum(1 for c in cells if c['arm']=='P0')}, P2={sum(1 for c in cells if c['arm']=='P2')})")

    executor = R7BLiveExecutor()
    results: list[dict] = []
    lock_print = time.time()

    def run_one(c: dict) -> dict:
        tid = c["task"]["task_id"]
        m = c["model"]
        tpl = bank[(tid, c["tpl"])]
        run_id = f"{m['alias']}__{tid}__{c['arm']}__tpl{c['tpl']}__rep{c['rep']}__r7d"
        t0 = time.time()
        trace = executor.run_cell(
            cell=R6RunCell(
                run_id=run_id,
                model_alias=m["alias"],
                task_id=tid,
                domain=tasks[tid]["domain"],
                layer=str(tasks[tid].get("layer") or ""),
                condition_id="neutral_control",
                seed=STATE_SEED,
                temperature=TEMPERATURE,
                executor="r7d_placebo_probe",
            ),
            model=m,
            task_reg=registry_by_task[tid],
            template=tpl,
            max_steps=int(m.get("max_steps_override", MAX_STEPS)),
            commit=commit,
        )
        (OUT / "traces" / f"{run_id}.trace.json").write_text(
            json.dumps(trace, ensure_ascii=False)
        )
        return dict(
            run_id=run_id,
            arm=c["arm"],
            band=c["task"]["band"],
            task_id=tid,
            domain=c["task"]["domain"],
            model=m["alias"],
            template_suffix=c["tpl"],
            replicate=c["rep"],
            n_tool_events=len(trace.get("tool_events") or []),
            tool_sequence="|".join(
                e.get("tool_name", "") for e in (trace.get("tool_events") or [])
            ),
            n_mutation_events=sum(
                1 for e in (trace.get("tool_events") or []) if e.get("mutated")
            ),
            n_confirmation_events=len(trace.get("confirmation_events") or []),
            any_tool_call=int(len(trace.get("tool_events") or []) > 0),
            final_response_len=len(str(trace.get("final_response") or "")),
            total_tokens=(trace.get("token_usage") or {}).get("total_tokens"),
            duration_s=round(time.time() - t0, 2),
        )

    # One worker per model: the three vLLM servers are independent processes on
    # separate GPUs, so this parallelises without adding contention inside a server.
    by_model: dict[str, list[dict]] = {}
    for c in cells:
        by_model.setdefault(c["model"]["alias"], []).append(c)

    def run_model(alias: str) -> list[dict]:
        out = []
        for k, c in enumerate(by_model[alias]):
            try:
                out.append(run_one(c))
            except Exception as exc:  # noqa: BLE001
                out.append(dict(run_id=f"FAILED__{alias}__{c['task']['task_id']}__{c['arm']}",
                                arm=c["arm"], band=c["task"]["band"],
                                task_id=c["task"]["task_id"], domain=c["task"]["domain"],
                                model=alias, template_suffix=c["tpl"], replicate=c["rep"],
                                error=repr(exc)))
            if (k + 1) % 10 == 0:
                print(f"    [{alias}] {k+1}/{len(by_model[alias])}", flush=True)
        return out

    t_start = time.time()
    with cf.ThreadPoolExecutor(max_workers=len(by_model)) as pool:
        futs = {pool.submit(run_model, a): a for a in by_model}
        for f in cf.as_completed(futs):
            results.extend(f.result())
    print(f"\nall cells done in {time.time()-t_start:.0f}s")

    ok = [r for r in results if "error" not in r]
    bad = [r for r in results if "error" in r]
    fields = list(ok[0].keys()) if ok else []
    with (OUT / "placebo_probe_runs.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(ok)
    (OUT / "failures.json").write_text(json.dumps(bad, indent=2, ensure_ascii=False))

    print(f"\nwrote {(OUT/'placebo_probe_runs.csv').relative_to(ROOT)}  ok={len(ok)} failed={len(bad)}")
    if bad:
        print("FAILURES:")
        for b in bad[:5]:
            print("  ", b.get("run_id"), b.get("error", "")[:120])
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
