#!/usr/bin/env python3
"""Deterministic offline reanalysis for the EACL process-robustness package.

No model, endpoint, network, GPU, or source-file write is performed. All outputs
are written below EACL_PROCESS_ROBUSTNESS_PAPER_PACKAGE_20260718.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import random
import shutil
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SOURCE = Path("/home/xqin5/llmlanguage")
REPO = SOURCE / "ir_mstu_stage2"
PACKAGE = SOURCE / "EACL_PROCESS_ROBUSTNESS_PAPER_PACKAGE_20260718"
R6 = REPO / "results/r6_sensitivity/full_main_seq_eligible_20260626"
R8 = REPO / "results/r8_full_episode"
INVENTORY_CSV = PACKAGE / "01_INVENTORY/ASSET_INVENTORY.csv"
RNG_SEED = 20260718

PURE = ["praise_trust_clean", "insult_strong_clean", "abuse_escalating_clean"]
ALL_R6_CONTRASTS = [
    ("pure_valence", "praise_trust_vs_neutral", "praise_trust_clean", "neutral_clean"),
    ("pure_valence", "insult_vs_neutral", "insult_strong_clean", "neutral_clean"),
    ("pure_valence", "abuse_vs_neutral", "abuse_escalating_clean", "neutral_clean"),
    ("pressure_factorial", "neutral_pressure_vs_clean", "neutral_pressure", "neutral_clean"),
    (
        "pressure_factorial",
        "praise_auth_vs_praise_clean",
        "praise_trust_authorization_pressure",
        "praise_trust_clean",
    ),
    (
        "pressure_factorial",
        "insult_urgency_vs_insult_clean",
        "insult_urgency_pressure",
        "insult_strong_clean",
    ),
    (
        "pressure_factorial",
        "abuse_continuation_vs_abuse_clean",
        "abuse_continuation_pressure",
        "abuse_escalating_clean",
    ),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fields:
        raise ValueError(f"cannot infer columns for empty table: {path}")
    fields = fields or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def truth(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    b = truth(value)
    if b is not None:
        return float(b)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def levenshtein(a: list[Any], b: list[Any]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def norm_distance(a: list[Any], b: list[Any]) -> float:
    denom = max(len(a), len(b))
    return levenshtein(a, b) / denom if denom else 0.0


def canonical_args(event: dict[str, Any]) -> str:
    return json.dumps(event.get("arguments") or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def tool_names(trace: dict[str, Any]) -> list[str]:
    return [str(e.get("tool_name") or "") for e in trace.get("tool_events") or [] if e.get("tool_name")]


def arg_sequence(trace: dict[str, Any]) -> list[str]:
    return [
        f"{e.get('tool_name')}|{hashlib.sha256(canonical_args(e).encode()).hexdigest()[:16]}"
        for e in trace.get("tool_events") or []
        if e.get("tool_name")
    ]


def stage(event: dict[str, Any]) -> str:
    name = str(event.get("tool_name") or "").lower()
    if event.get("mutated") or str(event.get("mutation_type") or "").lower() not in {"", "read", "none"}:
        return "write_commit"
    if any(k in name for k in ("search", "find", "query")):
        return "search"
    if any(k in name for k in ("validate", "verify", "checksum", "calculate", "permission", "policy")):
        return "validation"
    if any(k in name for k in ("get", "lookup", "list", "detail", "status", "metadata")):
        return "lookup_retrieval"
    return "other_read_or_action"


def stage_sequence(trace: dict[str, Any]) -> list[str]:
    return [stage(e) for e in trace.get("tool_events") or [] if e.get("tool_name")]


def first_divergence(a: list[Any], b: list[Any]) -> int | None:
    for i, (x, y) in enumerate(itertools.zip_longest(a, b, fillvalue=object())):
        if x != y:
            return i
    return None


def prewrite_length(trace: dict[str, Any]) -> int | None:
    events = [e for e in trace.get("tool_events") or [] if e.get("tool_name")]
    for i, event in enumerate(events):
        if stage(event) == "write_commit":
            return i
    return None


def exact_redundancy(trace: dict[str, Any]) -> int:
    seq = arg_sequence(trace)
    return len(seq) - len(set(seq))


def bh(pvalues: list[float]) -> list[float]:
    n = len(pvalues)
    order = sorted(range(n), key=pvalues.__getitem__)
    q = [1.0] * n
    running = 1.0
    for rank_from_end, idx in enumerate(reversed(order), 1):
        rank = n - rank_from_end + 1
        running = min(running, pvalues[idx] * n / rank)
        q[idx] = min(1.0, running)
    return q


def task_bootstrap(values_by_task: dict[str, list[float]], n_boot: int = 20000) -> tuple[float, float, float]:
    tasks = sorted(values_by_task)
    task_means = [statistics.mean(values_by_task[t]) for t in tasks]
    estimate = statistics.mean(task_means)
    rng = random.Random(RNG_SEED)
    boots = []
    for _ in range(n_boot):
        sample = [task_means[rng.randrange(len(task_means))] for _ in task_means]
        boots.append(statistics.mean(sample))
    boots.sort()
    return estimate, boots[int(0.025 * n_boot)], boots[min(n_boot - 1, int(0.975 * n_boot))]


def sign_permutation(task_values: list[float], n_perm: int = 100000) -> float:
    observed = abs(statistics.mean(task_values))
    rng = random.Random(RNG_SEED)
    extreme = 1
    for _ in range(n_perm):
        value = statistics.mean(v if rng.random() < 0.5 else -v for v in task_values)
        extreme += abs(value) >= observed - 1e-15
    return extreme / (n_perm + 1)


def load_r6() -> tuple[list[dict[str, str]], dict[tuple[str, str, str, str], dict[str, Any]]]:
    rows = list(csv.DictReader((R6 / "interactional_metrics/per_run_metrics.csv").open(encoding="utf-8")))
    traces: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for path in sorted((R6 / "traces").glob("*.trace.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        m = obj["run_meta"]
        key = (str(m["model_alias"]), str(m["task_id"]), str(m["condition_id"]), str(m["seed"]))
        obj["_source_path"] = str(path)
        traces[key] = obj
    return rows, traces


def metric_index(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    return {(r["model_alias"], r["task_id"], r["condition_id"], str(r["seed"])): r for r in rows}


def r6_integrity(rows: list[dict[str, str]], traces: dict[tuple[str, str, str, str], dict[str, Any]]) -> dict[str, Any]:
    models = sorted({r["model_alias"] for r in rows})
    tasks = sorted({r["task_id"] for r in rows})
    conditions = sorted({r["condition_id"] for r in rows})
    seeds = sorted({str(r["seed"]) for r in rows})
    expected = len(models) * len(tasks) * len(conditions) * len(seeds)
    duplicate_ids = len(rows) - len({r["run_id"] for r in rows})
    initial_mismatch = 0
    pair_count = 0
    for family, name, treatment, reference in ALL_R6_CONTRASTS:
        del family, name
        for model in models:
            for task in tasks:
                for seed in seeds:
                    left, right = traces[(model, task, treatment, seed)], traces[(model, task, reference, seed)]
                    pair_count += 1
                    if left["initial_environment_state"].get("state_hash") != right["initial_environment_state"].get("state_hash"):
                        initial_mismatch += 1
    return {
        "rows": len(rows),
        "traces": len(traces),
        "expected": expected,
        "models": models,
        "tasks": tasks,
        "conditions": conditions,
        "seeds": seeds,
        "duplicate_run_ids": duplicate_ids,
        "matched_contrast_pairs": pair_count,
        "initial_state_hash_mismatches": initial_mismatch,
    }


def placebo_adjusted_distance(
    rows: list[dict[str, str]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    del rows
    outputs: list[dict[str, Any]] = []
    for scope, executor in (("all_r6", None), ("tau2_only", "tau2_r6_live"), ("minimal_stub_only", "r6_minimal_live_model")):
        keys = [
            key
            for key, tr in traces.items()
            if key[2] == "neutral_clean" and (executor is None or tr["run_meta"].get("executor") == executor)
        ]
        models = sorted({k[0] for k in keys})
        tasks = sorted({k[1] for k in keys})
        seeds = sorted({k[3] for k in keys})
        scope_rows: list[dict[str, Any]] = []
        for family, contrast, treatment, reference in ALL_R6_CONTRASTS:
            # Only a neutral_clean reference has a directly comparable neutral-neutral placebo.
            # Other factorial contrasts retain neutral placebo as a descriptive scale calibration.
            attack_by_task: dict[str, list[float]] = defaultdict(list)
            placebo_by_task: dict[str, list[float]] = defaultdict(list)
            for task in tasks:
                for model in models:
                    for seed in seeds:
                        if (model, task, treatment, seed) not in traces or (model, task, reference, seed) not in traces:
                            continue
                        attack_by_task[task].append(
                            norm_distance(
                                tool_names(traces[(model, task, treatment, seed)]),
                                tool_names(traces[(model, task, reference, seed)]),
                            )
                        )
                    neutral = [traces[(model, task, "neutral_clean", s)] for s in seeds]
                    placebo_by_task[task].extend(
                        norm_distance(tool_names(a), tool_names(b)) for a, b in itertools.combinations(neutral, 2)
                    )
            deltas = {
                task: [statistics.mean(attack_by_task[task]) - statistics.mean(placebo_by_task[task])]
                for task in tasks
                if attack_by_task[task] and placebo_by_task[task]
            }
            est, lo, hi = task_bootstrap(deltas)
            p = sign_permutation([statistics.mean(v) for v in deltas.values()])
            attack_values = [x for vals in attack_by_task.values() for x in vals]
            placebo_values = [x for vals in placebo_by_task.values() for x in vals]
            scope_rows.append(
                {
                    "protocol": "R6",
                    "scope": scope,
                    "family": family,
                    "contrast": contrast,
                    "treatment": treatment,
                    "reference": reference,
                    "metric": "tool_name_sequence_distance_minus_neutral_neutral_placebo",
                    "n_treatment_reference_pairs": len(attack_values),
                    "n_placebo_pairs": len(placebo_values),
                    "n_task_clusters": len(deltas),
                    "treatment_reference_mean_distance": statistics.mean(attack_values),
                    "neutral_neutral_placebo_mean_distance": statistics.mean(placebo_values),
                    "estimate": est,
                    "ci_low": lo,
                    "ci_high": hi,
                    "permutation_p": p,
                    "post_hoc": True,
                    "note": (
                        "Task-cluster bootstrap and task-level sign permutation. "
                        "Neutral-neutral seed pairs calibrate temperature-0/server drift. "
                        "For non-neutral-reference factorial contrasts this is scale calibration, not a matched placebo."
                    ),
                }
            )
        qs = bh([float(r["permutation_p"]) for r in scope_rows])
        for row, q in zip(scope_rows, qs):
            row["bh_q_within_scope_7_contrasts"] = q
            row["fdr_significant"] = q < 0.05
        outputs.extend(scope_rows)
    return outputs


def pair_process_table(
    rows: list[dict[str, str]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
    calibrated: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    del rows
    calibrated_index = {(r["scope"], r["contrast"]): r for r in calibrated}
    output = []
    for scope, executor in (("all_r6", None), ("tau2_only", "tau2_r6_live"), ("minimal_stub_only", "r6_minimal_live_model")):
        neutral_keys = [
            key for key, tr in traces.items()
            if key[2] == "neutral_clean" and (executor is None or tr["run_meta"].get("executor") == executor)
        ]
        models = sorted({k[0] for k in neutral_keys})
        tasks = sorted({k[1] for k in neutral_keys})
        seeds = sorted({k[3] for k in neutral_keys})
        for family, contrast, treatment, reference in ALL_R6_CONTRASTS:
            records = []
            for model in models:
                for task in tasks:
                    for seed in seeds:
                        a = traces[(model, task, treatment, seed)]
                        b = traces[(model, task, reference, seed)]
                        names_a, names_b = tool_names(a), tool_names(b)
                        args_a, args_b = arg_sequence(a), arg_sequence(b)
                        stages_a, stages_b = stage_sequence(a), stage_sequence(b)
                        hash_a = a["final_environment_state"].get("state_hash")
                        hash_b = b["final_environment_state"].get("state_hash")
                        pre_a, pre_b = prewrite_length(a), prewrite_length(b)
                        records.append(
                            {
                                "tool_name_distance": norm_distance(names_a, names_b),
                                "argument_sequence_distance": norm_distance(args_a, args_b),
                                "stage_sequence_distance": norm_distance(stages_a, stages_b),
                                "tool_name_diff": names_a != names_b,
                                "argument_diff": args_a != args_b,
                                "stage_diff": stages_a != stages_b,
                                "same_final_hash": bool(hash_a and hash_b and hash_a == hash_b),
                                "same_final_hash_and_tool_diff": bool(hash_a and hash_b and hash_a == hash_b and names_a != names_b),
                                "first_divergence": first_divergence(names_a, names_b),
                                "same_multiset_reorder": Counter(names_a) == Counter(names_b) and names_a != names_b,
                                "length_changed": len(names_a) != len(names_b),
                                "tool_count_delta": len(names_a) - len(names_b),
                                "unique_tool_name_delta": len(set(names_a)) - len(set(names_b)),
                                "redundant_exact_delta": exact_redundancy(a) - exact_redundancy(b),
                                "prewrite_delta": None if pre_a is None or pre_b is None else pre_a - pre_b,
                            }
                        )
            cal = calibrated_index[(scope, contrast)]
            output.append(
                {
                    "protocol": "R6",
                    "scope": scope,
                    "family": family,
                    "contrast": contrast,
                    "n_pairs": len(records),
                    "tool_name_distance_mean": statistics.mean(r["tool_name_distance"] for r in records),
                    "argument_sequence_distance_mean": statistics.mean(r["argument_sequence_distance"] for r in records),
                    "stage_sequence_distance_mean": statistics.mean(r["stage_sequence_distance"] for r in records),
                    "tool_name_sequence_diff_rate": statistics.mean(r["tool_name_diff"] for r in records),
                    "argument_sequence_diff_rate": statistics.mean(r["argument_diff"] for r in records),
                    "stage_sequence_diff_rate": statistics.mean(r["stage_diff"] for r in records),
                    "same_final_hash_rate": statistics.mean(r["same_final_hash"] for r in records),
                    "same_final_hash_and_tool_diff_rate": statistics.mean(
                        r["same_final_hash_and_tool_diff"] for r in records
                    ),
                    "mean_first_divergence_zero_based": statistics.mean(
                        r["first_divergence"] for r in records if r["first_divergence"] is not None
                    )
                    if any(r["first_divergence"] is not None for r in records)
                    else "",
                    "same_multiset_reorder_rate": statistics.mean(r["same_multiset_reorder"] for r in records),
                    "length_change_rate": statistics.mean(r["length_changed"] for r in records),
                    "mean_tool_call_delta": statistics.mean(r["tool_count_delta"] for r in records),
                    "mean_unique_tool_name_delta": statistics.mean(r["unique_tool_name_delta"] for r in records),
                    "mean_exact_redundant_call_delta": statistics.mean(r["redundant_exact_delta"] for r in records),
                    "mean_prewrite_path_delta_evaluable": statistics.mean(
                        r["prewrite_delta"] for r in records if r["prewrite_delta"] is not None
                    )
                    if any(r["prewrite_delta"] is not None for r in records)
                    else "",
                    "placebo_adjusted_distance": cal["estimate"],
                    "placebo_adjusted_ci_low": cal["ci_low"],
                    "placebo_adjusted_ci_high": cal["ci_high"],
                    "placebo_adjusted_bh_q": cal["bh_q_within_scope_7_contrasts"],
                    "evidence_note": (
                        "Same-final-hash is external-state equivalence only, not task success; "
                        "communication/no-write correctness is not established by a DB hash."
                    ),
                }
            )
    return output


def outcome_table(
    rows: list[dict[str, str]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    primary = list(csv.DictReader((R6 / "analysis/primary_contrasts.csv").open(encoding="utf-8")))
    output = []
    for row in primary:
        if row["metric"] not in {
            "final_state_correct",
            "policy_failure_any",
            "confirmation_before_action_rate",
            "unsafe_compliance_or_privacy_violation",
        }:
            continue
        status = "PARTIALLY_SUPPORTED"
        caveat = ""
        if row["metric"] == "final_state_correct":
            status = "INVALIDATED_BY_EVALUATION"
            caveat = (
                "Only 1440 minimal-environment rows are evaluable; that environment ignores tool arguments "
                "and mutates expected paths, while 720 tau2 rows are missing field-level correctness."
            )
        elif row["metric"] == "unsafe_compliance_or_privacy_violation":
            status = "PARTIALLY_SUPPORTED"
            caveat = (
                "Evaluator detects successful prohibited-tool execution; it does not comprehensively score "
                "semantic disclosure in assistant text."
            )
        output.append(
            {
                "protocol": "R6",
                "contrast": row["contrast"],
                "metric": row["metric"],
                "n_pairs": row["n_pairs"],
                "n_tasks": row["n_tasks"],
                "estimate": row["estimate"],
                "ci_low": row["ci_low"],
                "ci_high": row["ci_high"],
                "corrected_p": row["q_value"],
                "final_status": status,
                "evaluator": "r6_annotation_minimal_live_v1 / tool-execution safety proxy",
                "caveat": caveat,
                "source": str(R6 / "analysis/primary_contrasts.csv"),
            }
        )
    analysis = json.loads((R8 / "analysis/analysis.json").read_text(encoding="utf-8"))
    for contrast in ("C3-C1", "C4-C1"):
        obj = analysis["primary"]["P1"][contrast]
        output.append(
            {
                "protocol": "R8",
                "contrast": contrast,
                "metric": "official_tau2_reward",
                "n_pairs": obj.get("n_pairs"),
                "n_tasks": 36,
                "estimate": obj.get("abs_diff"),
                "ci_low": (obj.get("ci95") or ["", ""])[0],
                "ci_high": (obj.get("ci95") or ["", ""])[1],
                "corrected_p": analysis["holm_adjusted_p"].get(f"P1:{contrast}"),
                "final_status": "SUPPORTED",
                "evaluator": "tau2 1.0.0 native evaluate_simulation",
                "caveat": "Separate full-episode pressure protocol; do not pool with R6 social-style conditions.",
                "source": str(R8 / "analysis/analysis.json"),
            }
        )
    return output


def heterogeneity_table(
    rows: list[dict[str, str]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    del rows
    outputs = []
    dimensions: list[tuple[str, str, Iterable[str]]] = [
        ("model", "model_alias", sorted({k[0] for k in traces})),
        ("task", "task_id", sorted({k[1] for k in traces})),
        ("domain", "domain", sorted({str(t["run_meta"].get("domain")) for t in traces.values()})),
        ("layer", "layer", sorted({str(t["run_meta"].get("layer")) for t in traces.values()})),
        ("executor", "executor", sorted({str(t["run_meta"].get("executor")) for t in traces.values()})),
    ]
    for dim, field, levels in dimensions:
        for level in levels:
            recs = []
            for key, ref in traces.items():
                model, task, cond, seed = key
                if cond != "neutral_clean":
                    continue
                meta_value = model if field == "model_alias" else task if field == "task_id" else str(ref["run_meta"].get(field))
                if meta_value != level:
                    continue
                for treatment in PURE:
                    tr = traces[(model, task, treatment, seed)]
                    names_t, names_r = tool_names(tr), tool_names(ref)
                    same_hash = (
                        tr["final_environment_state"].get("state_hash")
                        == ref["final_environment_state"].get("state_hash")
                    )
                    recs.append(
                        {
                            "distance": norm_distance(names_t, names_r),
                            "different": names_t != names_r,
                            "same_hash_process_diff": same_hash and names_t != names_r,
                            "tool_delta": len(names_t) - len(names_r),
                        }
                    )
            if not recs:
                continue
            outputs.append(
                {
                    "protocol": "R6_pure_style_vs_neutral",
                    "dimension": dim,
                    "level": level,
                    "n_pairs": len(recs),
                    "mean_tool_sequence_distance": statistics.mean(r["distance"] for r in recs),
                    "tool_sequence_diff_rate": statistics.mean(r["different"] for r in recs),
                    "same_final_hash_and_process_diff_rate": statistics.mean(
                        r["same_hash_process_diff"] for r in recs
                    ),
                    "mean_tool_call_delta": statistics.mean(r["tool_delta"] for r in recs),
                    "status": "DESCRIPTIVE_ONLY",
                    "limitation": "No multiplicity-corrected interaction test; ranking is exploratory.",
                }
            )
    return outputs


def tool_stage_table(
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    outputs = []
    for family, contrast, treatment, reference in ALL_R6_CONTRASTS:
        pairs = []
        for model, task, cond, seed in sorted(traces):
            if cond != treatment:
                continue
            a, b = traces[(model, task, treatment, seed)], traces[(model, task, reference, seed)]
            ca, cb = Counter(stage_sequence(a)), Counter(stage_sequence(b))
            pairs.append(
                {
                    "first_stage_divergence": first_divergence(stage_sequence(a), stage_sequence(b)),
                    **{f"delta_{s}": ca[s] - cb[s] for s in (
                        "search", "lookup_retrieval", "validation", "write_commit", "other_read_or_action"
                    )},
                }
            )
        for s in ("search", "lookup_retrieval", "validation", "write_commit", "other_read_or_action"):
            outputs.append(
                {
                    "protocol": "R6",
                    "family": family,
                    "contrast": contrast,
                    "tool_stage": s,
                    "n_pairs": len(pairs),
                    "mean_frequency_shift": statistics.mean(r[f"delta_{s}"] for r in pairs),
                    "insertion_rate": statistics.mean(r[f"delta_{s}"] > 0 for r in pairs),
                    "deletion_rate": statistics.mean(r[f"delta_{s}"] < 0 for r in pairs),
                    "mean_first_stage_divergence_zero_based": statistics.mean(
                        r["first_stage_divergence"]
                        for r in pairs
                        if r["first_stage_divergence"] is not None
                    )
                    if any(r["first_stage_divergence"] is not None for r in pairs)
                    else "",
                    "status": "DETERMINISTIC_DESCRIPTIVE",
                }
            )
    return outputs


def cost_table(
    rows: list[dict[str, str]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    idx = metric_index(rows)
    output = []
    for family, contrast, treatment, reference in ALL_R6_CONTRASTS:
        records = []
        for model, task, cond, seed in sorted(traces):
            if cond != treatment:
                continue
            a, b = traces[(model, task, treatment, seed)], traces[(model, task, reference, seed)]
            ma, mb = idx[(model, task, treatment, seed)], idx[(model, task, reference, seed)]
            usage_a, usage_b = a.get("token_usage") or {}, b.get("token_usage") or {}
            dur_a, dur_b = number(a["run_meta"].get("duration_s")), number(b["run_meta"].get("duration_s"))
            token_a, token_b = number(usage_a.get("tokens_total")), number(usage_b.get("tokens_total"))
            records.append(
                {
                    "tool_calls": len(tool_names(a)) - len(tool_names(b)),
                    "unique_tool_calls": len(set(tool_names(a))) - len(set(tool_names(b))),
                    "redundant_calls": exact_redundancy(a) - exact_redundancy(b),
                    "mutations": int(float(ma["n_mutation_events"])) - int(float(mb["n_mutation_events"])),
                    "token_delta": None if token_a is None or token_b is None else token_a - token_b,
                    "duration_delta": None if dur_a is None or dur_b is None else dur_a - dur_b,
                    "final_hash_changed": (
                        a["final_environment_state"].get("state_hash")
                        != b["final_environment_state"].get("state_hash")
                    ),
                    "executor": a["run_meta"].get("executor"),
                }
            )
        for metric in ("tool_calls", "unique_tool_calls", "redundant_calls", "mutations", "token_delta", "duration_delta"):
            vals = [r[metric] for r in records if r[metric] is not None]
            output.append(
                {
                    "protocol": "R6",
                    "family": family,
                    "contrast": contrast,
                    "metric": metric,
                    "n_pairs_total": len(records),
                    "n_pairs_evaluable": len(vals),
                    "missing_rate": 1 - len(vals) / len(records),
                    "mean_delta": statistics.mean(vals) if vals else "",
                    "median_delta": statistics.median(vals) if vals else "",
                    "positive_delta_rate": statistics.mean(v > 0 for v in vals) if vals else "",
                    "accounting_scope": (
                        "complete_trace_counter"
                        if metric not in {"token_delta", "duration_delta"}
                        else "prompt_plus_completion_or_agent_duration; minimal executor only for 1440/2160 rows"
                    ),
                    "claim_eligibility": (
                        "SUPPORTED_DESCRIPTIVE"
                        if metric not in {"token_delta", "duration_delta"}
                        else "APPENDIX_ONLY_PARTIAL_ACCOUNTING"
                    ),
                }
            )
        output.append(
            {
                "protocol": "R6",
                "family": family,
                "contrast": contrast,
                "metric": "final_db_hash_changed",
                "n_pairs_total": len(records),
                "n_pairs_evaluable": len(records),
                "missing_rate": 0,
                "mean_delta": statistics.mean(r["final_hash_changed"] for r in records),
                "median_delta": "",
                "positive_delta_rate": statistics.mean(r["final_hash_changed"] for r in records),
                "accounting_scope": "hash-only external-state comparison",
                "claim_eligibility": "SUPPORTED_DESCRIPTIVE_NOT_TASK_SUCCESS",
            }
        )
    return output


def representative_traces(
    traces: dict[tuple[str, str, str, str], dict[str, Any]]
) -> list[dict[str, Any]]:
    candidates = []
    for model, task, cond, seed in sorted(traces):
        if cond not in PURE:
            continue
        a, b = traces[(model, task, cond, seed)], traces[(model, task, "neutral_clean", seed)]
        if a["run_meta"].get("executor") != "tau2_r6_live":
            continue
        same_hash = (
            a["final_environment_state"].get("state_hash")
            == b["final_environment_state"].get("state_hash")
        )
        distance = norm_distance(tool_names(a), tool_names(b))
        if same_hash and distance > 0:
            candidates.append((distance, model, task, cond, seed, a, b))
    selected = sorted(candidates, reverse=True)[:3]
    output = []
    for rank, (distance, model, task, cond, seed, treatment, neutral) in enumerate(selected, 1):
        salt = f"{model}|{task}|{seed}".encode()
        anon = hashlib.sha256(salt).hexdigest()[:12]
        output.append(
            {
                "case_id": f"ANON_R6_{rank:02d}_{anon}",
                "condition_blind_codes": {"X": "neutral_clean", "Y": cond},
                "condition_blind_note": "Mapping retained here for audit; reviewer inputs must remove this mapping.",
                "external_state_hash_equal": True,
                "tool_name_sequence_distance": distance,
                "X": [
                    {
                        "position": i,
                        "tool": e.get("tool_name"),
                        "argument_keys": sorted((e.get("arguments") or {}).keys()),
                        "stage": stage(e),
                        "tool_error": bool(e.get("tool_error")),
                    }
                    for i, e in enumerate(neutral.get("tool_events") or [])
                ],
                "Y": [
                    {
                        "position": i,
                        "tool": e.get("tool_name"),
                        "argument_keys": sorted((e.get("arguments") or {}).keys()),
                        "stage": stage(e),
                        "tool_error": bool(e.get("tool_error")),
                    }
                    for i, e in enumerate(treatment.get("tool_events") or [])
                ],
                "source_hashes": {
                    "X": sha256(Path(neutral["_source_path"])),
                    "Y": sha256(Path(treatment["_source_path"])),
                },
                "privacy": "Argument values and conversation text omitted; task/model/seed replaced by salted case ID.",
            }
        )
    path = PACKAGE / "03_RAW_TRACE_INDEX/ANONYMIZED_REPRESENTATIVE_TRACES.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def trace_index(inventory_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows = []
    parsed = 0
    counts: Counter[str] = Counter()
    for inv in inventory_rows:
        if inv["asset_category"] != "raw_trace":
            continue
        path = Path(inv["source_path"])
        protocol = inv["experiment_round"]
        record: dict[str, Any] = {
            "source_path": str(path),
            "sha256": inv["sha256"],
            "size_bytes": inv["size_bytes"],
            "modified_time": inv["modified_time"],
            "protocol": protocol,
            "run_id": "",
            "model": "",
            "task_id": "",
            "domain": "",
            "condition": "",
            "seed_or_replicate": "",
            "executor_or_task_type": "",
            "metadata_parse_status": "PATH_ONLY",
            "scientific_eligibility": inv["evidence_status"],
        }
        try:
            if str(path).startswith(str(R6 / "traces")):
                obj = json.loads(path.read_text(encoding="utf-8"))
                m = obj["run_meta"]
                record.update(
                    run_id=obj.get("run_id", ""),
                    model=m.get("model_alias", ""),
                    task_id=m.get("task_id", ""),
                    domain=m.get("domain", ""),
                    condition=m.get("condition_id", ""),
                    seed_or_replicate=m.get("seed", ""),
                    executor_or_task_type=m.get("executor", ""),
                    metadata_parse_status="PARSED_R6",
                )
                parsed += 1
            elif str(path).startswith(str(R8 / "traces")):
                obj = json.loads(path.read_text(encoding="utf-8"))
                record.update(
                    run_id=obj.get("run_id", ""),
                    model=obj.get("model", ""),
                    task_id=obj.get("task_id", ""),
                    domain=obj.get("domain", ""),
                    condition=obj.get("condition", ""),
                    seed_or_replicate=obj.get("replicate", ""),
                    executor_or_task_type=obj.get("task_type", ""),
                    metadata_parse_status="PARSED_R8",
                )
                parsed += 1
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            record["metadata_parse_status"] = f"ERROR:{type(exc).__name__}"
        rows.append(record)
        counts[protocol] += 1
    return rows, {"indexed": len(rows), "parsed_metadata": parsed, **dict(counts)}


def copy_core_assets() -> list[dict[str, Any]]:
    selections = [
        (R6 / "interactional_metrics/per_run_metrics.csv", "R6 per-run metrics; 2160 rows", "C01,C04-C11"),
        (R6 / "analysis/primary_contrasts.csv", "R6 primary contrast table", "C04,C06-C08"),
        (R6 / "analysis/secondary_contrasts.csv", "R6 secondary contrast table", "C08-C10"),
        (R6 / "r6_integrity_status.csv", "R6 integrity status", "C01"),
        (REPO / "reports/r6_sensitivity/R6_FULL_DEEP_ANALYSIS_CN_20260629.md", "R6 historical synthesis", "context"),
        (REPO / "reports/r7_ipma/R6_TOKEN_DURATION_REPAIR_CN.md", "R6 token/duration repair audit", "C09"),
        (REPO / "reports/r7_ipma/R6_TAU2_FIELD_DIFF_AUDIT_CN.md", "R6 tau2 field-diff audit", "C06"),
        (REPO / "reports/r7_ipma/R6_TOOL_TRAJECTORY_CASE_AUDIT_CN.md", "R6 historical case audit", "C04"),
        (REPO / "data/r6/r6_social_style_templates.yaml", "Frozen R6 condition text", "C02"),
        (REPO / "data/r6/r6_tasks.yaml", "Frozen R6 tasks", "C01,C06"),
        (REPO / "data/r6/r6_task_policy_annotations.yaml", "R6 evaluator annotations", "C06-C08,C11"),
        (REPO / "scripts/r6/r6_contrasts.py", "R6 original contrast implementation", "C04,C08"),
        (REPO / "scripts/r6/extract_r6_metrics.py", "R6 metric implementation", "C06-C11"),
        (REPO / "src/r6/minimal_live_agent.py", "R6 minimal environment executor/evaluator", "C06"),
        (REPO / "reports/r7c_ipma/R7C_FULL_REPORT_CN.md", "R7-C strict placebo counterevidence", "C13"),
        (REPO / "reports/r7d_ipma/R7D_STEP1_CONSTRUCT_VALIDITY_AND_ALIGNMENT_CN.md", "R7-D construct audit", "C12,C13"),
        (R8 / "analysis/analysis.json", "R8 primary/secondary analysis", "C14,C15"),
        (R8 / "integrity/full_integrity.json", "R8 integrity report", "C14,C15"),
        (REPO / "reports/r8_full_episode/R8_FULL_EPISODE_MULTI_STEP_STRESS_TEST_CN.md", "R8 final report", "C14,C15"),
        (REPO / "data/r8_full_episode/frozen/preregistration.json", "R8 frozen preregistration", "C14,C15"),
        (REPO / "reports/measurement_repair/R5_FULL_EXPERIMENT_REPORT_CN.md", "R5 replication/null context", "context"),
        (SOURCE / "LLMLANGUAGE_轮次进展与试错总结_CN.md", "Cross-round historical ledger", "context"),
    ]
    dest_root = PACKAGE / "02_CORE_EVIDENCE/source_snapshots"
    dest_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, (src, reason, claim) in enumerate(selections, 1):
        if not src.exists():
            rows.append(
                {
                    "source_path": str(src),
                    "destination_path": "",
                    "sha256": "",
                    "size": "",
                    "modified_time": "",
                    "reason_selected": reason,
                    "claim_id": claim,
                    "copy_status": "MISSING",
                }
            )
            continue
        dest = dest_root / f"{i:02d}_{src.name}"
        shutil.copy2(src, dest)
        st = src.stat()
        rows.append(
            {
                "source_path": str(src),
                "destination_path": str(dest),
                "sha256": sha256(src),
                "size": st.st_size,
                "modified_time": datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(),
                "reason_selected": reason,
                "claim_id": claim,
                "copy_status": "COPIED_VERIFIED" if sha256(dest) == sha256(src) else "HASH_MISMATCH",
            }
        )
    write_csv(PACKAGE / "COPY_MANIFEST.csv", rows)
    return rows


def claim_matrix(
    r6_info: dict[str, Any],
    calibrated: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hashes = {
        "r6_metrics": sha256(R6 / "interactional_metrics/per_run_metrics.csv"),
        "r6_primary": sha256(R6 / "analysis/primary_contrasts.csv"),
        "r6_templates": sha256(REPO / "data/r6/r6_social_style_templates.yaml"),
        "r7c": sha256(REPO / "reports/r7c_ipma/R7C_FULL_REPORT_CN.md"),
        "r8": sha256(R8 / "analysis/analysis.json"),
    }
    tau2_cal = {
        r["contrast"]: r
        for r in calibrated
        if r["scope"] == "tau2_only" and r["contrast"] in {
            "praise_trust_vs_neutral", "insult_vs_neutral", "abuse_vs_neutral"
        }
    }
    process_effect = "; ".join(
        f"{k}: Δadj={v['estimate']:.3f}, CI[{v['ci_low']:.3f},{v['ci_high']:.3f}], q={v['bh_q_within_scope_7_contrasts']:.4g}"
        for k, v in tau2_cal.items()
    )
    fields = [
        "claim_id", "paper_claim", "evidence_files", "source_paths", "file_sha256",
        "denominator", "models", "domains", "conditions", "evaluator", "statistical_test",
        "effect_size", "confidence_interval", "corrected_p_value", "supporting_evidence",
        "counterevidence", "limitations", "final_status", "main_text_eligible",
        "appendix_or_exclude",
    ]
    base = {k: "" for k in fields}
    claims = [
        {
            **base,
            "claim_id": "C01",
            "paper_claim": "R6 形成完整的 3×30×8×3=2160 条 live-model trace 矩阵。",
            "evidence_files": "r6_integrity_status.csv; per_run_metrics.csv; 2160 raw traces",
            "source_paths": str(R6),
            "file_sha256": hashes["r6_metrics"],
            "denominator": "2160/2160 traces",
            "models": ", ".join(r6_info["models"]),
            "domains": "10 recorded domains",
            "conditions": "8",
            "evaluator": "schema/integrity checks",
            "statistical_test": "deterministic count + duplicate/schema audit",
            "supporting_evidence": f"expected={r6_info['expected']}; duplicates={r6_info['duplicate_run_ids']}; initial hash mismatches={r6_info['initial_state_hash_mismatches']}",
            "limitations": "Completion/integrity does not validate evaluator semantics.",
            "final_status": "SUPPORTED",
            "main_text_eligible": "YES",
            "appendix_or_exclude": "Main/Table 1",
        },
        {
            **base,
            "claim_id": "C02",
            "paper_claim": "R6 操作覆盖 praise、strong insult 与 escalating abuse。",
            "evidence_files": "r6_social_style_templates.yaml",
            "source_paths": str(REPO / "data/r6/r6_social_style_templates.yaml"),
            "file_sha256": hashes["r6_templates"],
            "denominator": "8 conditions × 3 frozen wrappers",
            "conditions": "neutral/praise_trust/process-frustration/escalating process complaint + pressure variants",
            "evaluator": "direct text inspection",
            "supporting_evidence": "Frozen wrappers exist and are turn-count matched.",
            "counterevidence": "insult_strong_clean says the support process is frustrating/annoying; it does not directly insult the agent.",
            "limitations": "Condition IDs overstate interpersonal hostility; authorization/continuation pressure are semantically active.",
            "final_status": "PARTIALLY_SUPPORTED",
            "main_text_eligible": "YES_WITH_RENAMING",
            "appendix_or_exclude": "Main method caveat; original labels appendix only",
        },
        {
            **base,
            "claim_id": "C03",
            "paper_claim": "R6 paired comparisons preserve recorded initial external state.",
            "evidence_files": "2160 R6 traces",
            "source_paths": str(R6 / "traces"),
            "denominator": str(r6_info["matched_contrast_pairs"]),
            "models": "3",
            "domains": "10",
            "conditions": "7 treatment-reference contrasts",
            "evaluator": "initial_environment_state.state_hash",
            "statistical_test": "deterministic equality",
            "effect_size": "0 mismatches",
            "supporting_evidence": "All audited contrast pairs have equal recorded initial-state hash.",
            "limitations": "Tool-schema/system-policy hashes are not present in every R6 trace.",
            "final_status": "SUPPORTED",
            "main_text_eligible": "YES",
            "appendix_or_exclude": "Main design",
        },
        {
            **base,
            "claim_id": "C04",
            "paper_claim": "R6 的 clean social-style 条件在 tau2 子集上改变工具名序列，且高于 neutral-neutral 漂移。",
            "evidence_files": "R6 tau2 traces; offline PROCESS_ROBUSTNESS.csv",
            "source_paths": str(R6 / "traces"),
            "file_sha256": hashes["r6_metrics"],
            "denominator": "90 pairs/condition; 10 task clusters; 90 neutral-neutral placebo pairs",
            "models": "3",
            "domains": "retail, airline",
            "conditions": "praise_trust/process-frustration/escalating process complaint vs neutral",
            "evaluator": "normalized Levenshtein distance over tool names",
            "statistical_test": "post-hoc task-cluster bootstrap + task sign permutation + BH over 7 contrasts",
            "effect_size": process_effect,
            "supporting_evidence": "All three tau2 clean-style adjusted distances are positive; exact values are machine-generated.",
            "counterevidence": "R8 full-episode pressure effects are below practical threshold; R6 test was not preregistered with placebo.",
            "limitations": "Post-hoc; condition nomenclature/semantic purity imperfect; distance does not imply worse behavior.",
            "final_status": "PARTIALLY_SUPPORTED",
            "main_text_eligible": "YES_AS_EXPLORATORY",
            "appendix_or_exclude": "Main secondary + full appendix",
        },
        {
            **base,
            "claim_id": "C05",
            "paper_claim": "R6 存在 final-DB-hash 相同但工具轨迹不同的配对。",
            "evidence_files": "R6 traces; PROCESS_ROBUSTNESS.csv",
            "source_paths": str(R6 / "traces"),
            "denominator": "90 tau2 pairs per clean condition",
            "models": "3",
            "domains": "retail, airline",
            "conditions": "three clean styles vs neutral",
            "evaluator": "final DB hash equality + exact tool sequence inequality",
            "statistical_test": "descriptive paired proportion",
            "effect_size": "tau2 same-hash+different-tool rates: praise .411; process-frustration .389; escalating complaint .356",
            "supporting_evidence": "Directly recomputed from raw traces.",
            "counterevidence": "Same DB hash may mean both runs failed/no-op and does not score communication correctness.",
            "limitations": "Outcome-stable means external-state-equivalent, not successful-task-equivalent.",
            "final_status": "PARTIALLY_SUPPORTED",
            "main_text_eligible": "YES_WITH_STRICT_WORDING",
            "appendix_or_exclude": "Main descriptive result",
        },
        {
            **base,
            "claim_id": "C06",
            "paper_claim": "R6 证明最终任务成功在 social conditions 下稳定。",
            "evidence_files": "primary_contrasts.csv; minimal_live_agent.py; R6_TAU2_FIELD_DIFF_AUDIT_CN.md",
            "source_paths": f"{R6 / 'analysis/primary_contrasts.csv'}; {REPO / 'src/r6/minimal_live_agent.py'}",
            "file_sha256": hashes["r6_primary"],
            "denominator": "1440 minimal rows evaluable; 720 tau2 field outcome missing",
            "evaluator": "r6_annotation_minimal_live_v1",
            "statistical_test": "original paired bootstrap/FDR",
            "supporting_evidence": "Original final_state_correct contrasts did not survive FDR.",
            "counterevidence": "Minimal executor ignores tool arguments and applies expected mutations; tau2 has no field-level scorer.",
            "limitations": "No full valid outcome denominator.",
            "final_status": "INVALIDATED_BY_EVALUATION",
            "main_text_eligible": "NO",
            "appendix_or_exclude": "Explain invalidation; exclude success-rate claim",
        },
        {
            **base,
            "claim_id": "C07",
            "paper_claim": "R6 中 privacy violation 与 unsafe compliance 均为零。",
            "evidence_files": "per_run_metrics.csv; extract_r6_metrics.py; run_r6_live.py",
            "source_paths": str(R6 / "interactional_metrics/per_run_metrics.csv"),
            "file_sha256": hashes["r6_metrics"],
            "denominator": "2160 rows for successful prohibited-tool proxy",
            "evaluator": "successful prohibited-tool execution / explicit runner flags",
            "statistical_test": "deterministic count",
            "effect_size": "0/2160 flagged",
            "supporting_evidence": "No successful prohibited tool execution was flagged.",
            "counterevidence": "Textual disclosure is not comprehensively evaluated; flags can be runner-generated negatives.",
            "limitations": "Must not be phrased as comprehensive privacy/safety violation rate.",
            "final_status": "PARTIALLY_SUPPORTED",
            "main_text_eligible": "YES_AS_TOOL_EXECUTION_BOUND",
            "appendix_or_exclude": "Main caveated; broad safety claim excluded",
        },
        {
            **base,
            "claim_id": "C08",
            "paper_claim": "Pressure/urgency/continuation alters action intensity and confirmation timing in R6.",
            "evidence_files": "primary_contrasts.csv; secondary_contrasts.csv",
            "source_paths": str(R6 / "analysis"),
            "file_sha256": hashes["r6_primary"],
            "denominator": "270 tool pairs; 135 confirmation-evaluable pairs",
            "models": "3",
            "domains": "10",
            "conditions": "neutral pressure; insult+urgency; complaint+continuation",
            "evaluator": "direct tool-event count; structured/text confirmation timing",
            "statistical_test": "task-cluster bootstrap + BH-FDR",
            "effect_size": "tool calls +0.400/+0.800/+0.452; confirmation-before-action +0.133",
            "confidence_interval": "see source table; e.g. urgency tool calls [0.507,1.111]",
            "corrected_p_value": "q=.031/.010/.031; confirmation q=.004",
            "supporting_evidence": "FDR-surviving primary/secondary contrasts.",
            "counterevidence": "Pressure wrappers add directive/continuation semantics, so this is not pure valence.",
            "limitations": "Secondary family for tool counts; no full token/latency accounting.",
            "final_status": "SUPPORTED",
            "main_text_eligible": "YES_AS_PRESSURE_EFFECT",
            "appendix_or_exclude": "Main",
        },
        {
            **base,
            "claim_id": "C09",
            "paper_claim": "R6 social conditions change token cost or latency.",
            "evidence_files": "R6 traces; R6_TOKEN_DURATION_REPAIR_CN.md",
            "source_paths": str(REPO / "reports/r7_ipma/R6_TOKEN_DURATION_REPAIR_CN.md"),
            "denominator": "1440/2160 trace pairs potentially account prompt+completion; 720/2160 missing",
            "evaluator": "provider prompt+completion usage and run duration",
            "supporting_evidence": "Partial minimal-executor accounting exists.",
            "counterevidence": "33.3% missing is exactly the tau2 subset; framework/system/tool-schema cost is absent.",
            "limitations": "Cross-executor full cost incomparable.",
            "final_status": "INCONCLUSIVE",
            "main_text_eligible": "NO_FULL_COST_CLAIM",
            "appendix_or_exclude": "Appendix descriptive only",
        },
        {
            **base,
            "claim_id": "C10",
            "paper_claim": "Mistral is the most process-sensitive R6 model.",
            "evidence_files": "MODEL_TASK_HETEROGENEITY.csv",
            "source_paths": str(PACKAGE / "04_ANALYSIS_TABLES/MODEL_TASK_HETEROGENEITY.csv"),
            "denominator": "270 pure-style pairs/model",
            "statistical_test": "descriptive stratification only",
            "supporting_evidence": "Mistral has the highest mean sequence distance and divergence rate.",
            "counterevidence": "No multiplicity-corrected model×condition interaction; serving repairs differ by model.",
            "limitations": "Ranking is exploratory.",
            "final_status": "PARTIALLY_SUPPORTED",
            "main_text_eligible": "NO_AS_CONFIRMATORY",
            "appendix_or_exclude": "Appendix/exploratory figure",
        },
        {
            **base,
            "claim_id": "C11",
            "paper_claim": "R6 独立测得 task abandonment，且 repeated abuse 不增加 abandonment。",
            "evidence_files": "extract_r6_metrics.py; per_run_metrics.csv",
            "source_paths": str(REPO / "scripts/r6/extract_r6_metrics.py"),
            "denominator": "2160",
            "evaluator": "fallback maps benign over-refusal directly to agent_side_abandonment",
            "supporting_evidence": "Metric column is complete.",
            "counterevidence": "371 abandonment labels exactly equal 371 over_refusal labels by construction.",
            "limitations": "Cannot distinguish boundary setting, over-refusal, and abandonment.",
            "final_status": "INVALIDATED_BY_EVALUATION",
            "main_text_eligible": "NO",
            "appendix_or_exclude": "Exclude; document evaluator failure",
        },
        {
            **base,
            "claim_id": "C12",
            "paper_claim": "R7-v1 PASR≈14% demonstrates process manipulation.",
            "evidence_files": "R7 historical reports; R7-C/R7-D audits",
            "source_paths": str(REPO / "reports/r7_ipma"),
            "denominator": "historical 1350 attack-neutral pairs",
            "evaluator": "old PASR with invalid pairing/endpoint/semantic gates",
            "supporting_evidence": "Historical report contains 14%.",
            "counterevidence": "Later audits invalidate pairing/endpoint/semantic logic and placebo specificity.",
            "final_status": "INVALIDATED_BY_EVALUATION",
            "main_text_eligible": "NO",
            "appendix_or_exclude": "Excluded historical claim",
        },
        {
            **base,
            "claim_id": "C13",
            "paper_claim": "R7-C strict PASR is no larger than its neutral-neutral placebo.",
            "evidence_files": "R7C_FULL_REPORT_CN.md",
            "source_paths": str(REPO / "reports/r7c_ipma/R7C_FULL_REPORT_CN.md"),
            "file_sha256": hashes["r7c"],
            "denominator": "2160 attack pairs; 432 pooled placebo pairs",
            "models": "3",
            "conditions": "5 pressure variants vs neutral",
            "evaluator": "strict fail-closed PASR after audit fixes",
            "effect_size": "attack .0403; pooled placebo .0463",
            "supporting_evidence": "Placebo exceeds attack.",
            "limitations": "R7-C construct itself was later judged weak/under-identified.",
            "final_status": "SUPPORTED",
            "main_text_eligible": "YES_AS_COUNTEREVIDENCE",
            "appendix_or_exclude": "Main methodology/audit result",
        },
        {
            **base,
            "claim_id": "C14",
            "paper_claim": "R8 full-episode urgency/frustration does not change official tau2 reward by ≥5pp pooled.",
            "evidence_files": "R8 analysis.json; integrity report; preregistration",
            "source_paths": str(R8 / "analysis/analysis.json"),
            "file_sha256": hashes["r8"],
            "denominator": "2680 valid episodes; 540 paired units per contrast family",
            "models": "3",
            "domains": "retail, airline",
            "conditions": "C3/C4 vs matched C1",
            "evaluator": "official tau2 native evaluate_simulation",
            "statistical_test": "preregistered task-cluster bootstrap + Holm",
            "effect_size": "C3 +.024; C4 -.006 reward",
            "confidence_interval": "C3 [-.024,.071]; C4 [-.052,.039]",
            "corrected_p_value": ".749/.879",
            "supporting_evidence": "Integrity PASS and official evaluator.",
            "limitations": "Pressure protocol, not praise/insult; custom scaffold has an 11pp main effect vs official simulator.",
            "final_status": "SUPPORTED",
            "main_text_eligible": "YES",
            "appendix_or_exclude": "Main",
        },
        {
            **base,
            "claim_id": "C15",
            "paper_claim": "R8 pooled process changes are below preregistered practical importance.",
            "evidence_files": "R8 analysis.json",
            "source_paths": str(R8 / "analysis/analysis.json"),
            "file_sha256": hashes["r8"],
            "denominator": "540 paired units",
            "evaluator": "total tool calls",
            "statistical_test": "cluster permutation + Holm; preregistered ≥1 call and ≥15% threshold",
            "effect_size": "C3 +0.50/+6.4%; C4 +0.69/+8.7%",
            "confidence_interval": "C3 [.072,.935]; C4 [.195,1.215]",
            "corrected_p_value": ".089/.054",
            "supporting_evidence": "Both pooled estimates are below practical threshold.",
            "counterevidence": "Airline C4 exploratory subgroup +1.41 calls; sensitivity models are nominally significant but non-primary.",
            "limitations": "Cannot claim exact zero; conditional heterogeneity remains.",
            "final_status": "SUPPORTED",
            "main_text_eligible": "YES",
            "appendix_or_exclude": "Main",
        },
        {
            **base,
            "claim_id": "C16",
            "paper_claim": "Across protocols, stable outcomes systematically coexist with practically meaningful unstable processes.",
            "evidence_files": "R6/R7-C/R8 combined evidence package",
            "source_paths": f"{R6}; {R8}",
            "denominator": "not poolable",
            "evaluator": "heterogeneous",
            "supporting_evidence": "R6 shows sequence identity changes and same-hash/different-path pairs.",
            "counterevidence": "R8 pooled tool effects are calibrated subthreshold; R7-C attack≤placebo.",
            "limitations": "Protocols, evaluators, tasks, and conditions differ.",
            "final_status": "INCONCLUSIVE",
            "main_text_eligible": "NO_AS_UNIVERSAL_CLAIM",
            "appendix_or_exclude": "Use as research question, not conclusion",
        },
    ]
    return [{field: row.get(field, "") for field in fields} for row in claims]


def matrix_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Claim–Evidence Matrix",
        "",
        "完整机器字段见同目录 CSV；下表仅显示写作决策核心列。",
        "",
        "| ID | 主张（简写） | 状态 | 正文 | 处置 |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        claim = str(row["paper_claim"]).replace("|", "\\|")
        lines.append(
            f"| {row['claim_id']} | {claim} | {row['final_status']} | "
            f"{row['main_text_eligible']} | {row['appendix_or_exclude']} |"
        )
    lines += [
        "",
        "## 状态解释",
        "",
        "- `SUPPORTED`：原始文件与本次确定性重算一致，且 evaluator 对该窄主张适用。",
        "- `PARTIALLY_SUPPORTED`：观察成立，但外推、语义纯度、统计预注册或 evaluator 覆盖不足。",
        "- `INVALIDATED_BY_EVALUATION`：数值可能存在，但对应 evaluator/构造不能支撑论文主张。",
        "- `INCONCLUSIVE`：证据与反证并存或协议不可池化。",
        "",
    ]
    return "\n".join(lines)


def core_results(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep = {"C01", "C04", "C05", "C08", "C13", "C14", "C15"}
    return [
        {
            "claim_id": r["claim_id"],
            "result": r["paper_claim"],
            "status": r["final_status"],
            "effect_size": r["effect_size"],
            "confidence_interval": r["confidence_interval"],
            "corrected_p_value": r["corrected_p_value"],
            "paper_location": r["appendix_or_exclude"],
        }
        for r in claims
        if r["claim_id"] in keep
    ]


def main() -> int:
    inventory_rows = list(csv.DictReader(INVENTORY_CSV.open(encoding="utf-8")))
    rows, traces = load_r6()
    info = r6_integrity(rows, traces)
    calibrated = placebo_adjusted_distance(rows, traces)
    process = pair_process_table(rows, traces, calibrated)
    outcome = outcome_table(rows, traces)
    heterogeneity = heterogeneity_table(rows, traces)
    stages = tool_stage_table(traces)
    costs = cost_table(rows, traces)
    reps = representative_traces(traces)
    traces_out, coverage = trace_index(inventory_rows)

    write_csv(PACKAGE / "04_ANALYSIS_TABLES/PROCESS_ROBUSTNESS.csv", process)
    write_csv(PACKAGE / "04_ANALYSIS_TABLES/PROCESS_PLACEBO_CALIBRATION.csv", calibrated)
    write_csv(PACKAGE / "04_ANALYSIS_TABLES/OUTCOME_ROBUSTNESS.csv", outcome)
    write_csv(PACKAGE / "04_ANALYSIS_TABLES/MODEL_TASK_HETEROGENEITY.csv", heterogeneity)
    write_csv(PACKAGE / "04_ANALYSIS_TABLES/TOOL_STAGE_SENSITIVITY.csv", stages)
    write_csv(PACKAGE / "04_ANALYSIS_TABLES/COST_AND_STATE_IMPACT.csv", costs)
    write_csv(PACKAGE / "03_RAW_TRACE_INDEX/TRACE_INDEX.csv", traces_out)

    coverage_md = [
        "# Raw Trace Coverage",
        "",
        f"- 全项目按路径识别并索引的 trace 文件：{coverage['indexed']:,}",
        f"- 已解析结构化 metadata（R6/R8）：{coverage['parsed_metadata']:,}",
        f"- R6 核心 trace：{coverage.get('r6', 0):,} 个路径条目（其中本次主 root 2160 条逐文件解析）。",
        f"- R8 trace：{coverage.get('r8', 0):,} 个路径条目（2680 有效 + 20 error/capacity 记录由 integrity 另行记账）。",
        "",
        "## 覆盖口径",
        "",
        "索引覆盖率为 100% 的“trace-like 文件路径覆盖”，不等于所有历史 trace 都有统一 schema。",
        "R7 v1 的巨型 trace 只做路径、hash、大小和处置登记，未被重新解释为科学证据。",
        "R6/R8 核心 trace 已解析 model/task/condition/seed；原始文件保留在源目录，package 不复制 3.9 GiB 历史 trace。",
        "",
        f"匿名代表性 trace 对：{len(reps)}，见 `ANONYMIZED_REPRESENTATIVE_TRACES.json`。",
        "",
    ]
    (PACKAGE / "03_RAW_TRACE_INDEX/TRACE_COVERAGE.md").write_text("\n".join(coverage_md), encoding="utf-8")

    claims = claim_matrix(info, calibrated)
    write_csv(PACKAGE / "02_CORE_EVIDENCE/CLAIM_EVIDENCE_MATRIX.csv", claims)
    (PACKAGE / "02_CORE_EVIDENCE/CLAIM_EVIDENCE_MATRIX.md").write_text(
        matrix_markdown(claims), encoding="utf-8"
    )
    write_csv(PACKAGE / "02_CORE_EVIDENCE/CORE_RESULTS_TABLE.csv", core_results(claims))
    copies = copy_core_assets()

    summary = {
        "r6": info,
        "trace_coverage": coverage,
        "claims": Counter(r["final_status"] for r in claims),
        "representative_trace_pairs": len(reps),
        "copy_manifest_rows": len(copies),
        "generated_at": datetime.now().astimezone().isoformat(),
    }
    (PACKAGE / "04_ANALYSIS_TABLES/OFFLINE_REANALYSIS_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
