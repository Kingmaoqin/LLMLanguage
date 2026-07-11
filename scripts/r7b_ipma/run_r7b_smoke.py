#!/usr/bin/env python3
"""Run R7-B code smoke on strict synthetic traces.

This is not a model experiment.  It validates that the R7-B data structures,
template audits, pairing invariants, endpoint oracle, PASR and statistics
pipeline work under a controlled strict-pairing trace set.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r7b_ipma.r7b_common import CONDITIONS, read_csv, stable_hash, write_md


MODELS = ["gemma4_31b", "gpt_oss_120b", "mistral_small_3p2"]
SEEDS = [300, 301]


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return {"cmd": " ".join(cmd), "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def tool_events_for(family: str, condition: str) -> list[dict]:
    base = ["read_identity", "read_record"]
    if family == "A_action_intensity_amplification" and condition != "neutral_control":
        seq = base + ["read_policy", "read_record", "read_record"]
    elif family == "E_evidence_path_steering" and condition != "neutral_control":
        seq = ["read_identity", "read_alt_source", "read_record"]
    elif family in {"B_premature_mutation_pressure", "C_confirmation_shift"}:
        seq = base + ["mutate_record"]
    else:
        seq = base
    events = []
    for i, name in enumerate(seq):
        is_mut = name.startswith("mutate")
        events.append(
            {
                "step_index": i,
                "turn_index": 0,
                "tool_name": name,
                "tool_arguments": {"entity_id": "entity_1"},
                "tool_arguments_hash": stable_hash({"entity_id": "entity_1"}),
                "tool_observation_hash": stable_hash({"ok": True, "tool": name}),
                "success": True,
                "is_read": not is_mut,
                "is_write": is_mut,
                "is_mutation": is_mut,
                "requires_confirmation": is_mut,
                "confirmation_available_before_call": True,
                "evidence_fields_available_before_call": ["identity", "record"],
                "state_diff_after_call": ["records.status"] if is_mut else [],
                "latency_seconds": 0.01,
            }
        )
    return events


def write_synthetic_traces() -> int:
    registry = [r for r in read_csv(ROOT / "data/r7b_ipma/r7b_task_registry.csv") if r["endpoint_oracle_supported"] == "True"][:8]
    trace_dir = ROOT / "results/r7b_ipma/main/traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    for old in trace_dir.glob("*.trace.json"):
        old.unlink()
    count = 0
    for task in registry:
        expected_diff = ["records.status"] if task["requires_mutation"] == "True" else []
        for model in MODELS:
            for seed in SEEDS:
                initial_state = {"records": {"status": "initial", "task_id": task["task_id"]}}
                for condition in CONDITIONS:
                    final_state = {"records": {"status": "updated" if expected_diff else "initial", "task_id": task["task_id"]}}
                    events = tool_events_for(task["task_family_primary"], condition)
                    if not any(e["is_mutation"] for e in events):
                        final_state = initial_state
                    run_id = f"{model}__{task['task_id']}__{condition}__seed{seed}__r7b_smoke"
                    pressure = "neutral" if condition == "neutral_control" else condition
                    trace = {
                        "run_id": run_id,
                        "r7b_version": "r7b_smoke_v1",
                        "git_commit": "SMOKE_UNCOMMITTED",
                        "run_meta": {
                            "run_id": run_id,
                            "model": model,
                            "model_alias": model,
                            "model_config": {"temperature": 0.0},
                            "task_id": task["task_id"],
                            "condition": condition,
                            "condition_id": condition,
                            "template_id": f"{task['task_id']}__{condition}__01",
                            "seed": seed,
                            "temperature": 0.0,
                            "system_prompt_hash": stable_hash("r7b_smoke_system"),
                            "clean_task_semantics_hash": task["canonical_clean_task_semantics_hash"],
                            "pressure_prefix_hash": stable_hash(pressure),
                            "policy_spec_hash": task["policy_spec_hash"],
                            "tool_permission_hash": task["tool_permission_hash"],
                            "initial_state_hash": task["initial_state_hash"],
                            "endpoint_evaluator_hash": task["endpoint_evaluator_hash"],
                            "required_information_hash": task["required_information_hash"],
                        },
                        "conversation_turns": [
                            {
                                "turn_index": 0,
                                "speaker": "user",
                                "surface_content": task["canonical_clean_task_semantics"],
                                "clean_task_semantics_hash_if_user": task["canonical_clean_task_semantics_hash"],
                                "pressure_label_if_user": pressure,
                                "pressure_prefix_hash_if_user": stable_hash(pressure),
                                "timestamp": "2026-07-06T00:00:00Z",
                            }
                        ],
                        "tool_events": events,
                        "state_diffs": [],
                        "initial_environment_state": {"state": initial_state, "state_hash": task["initial_state_hash"]},
                        "final_environment_state": {"state": final_state, "state_hash": stable_hash(final_state), "final_state_correct": True},
                        "expected_field_diffs": expected_diff if any(e["is_mutation"] for e in events) else [],
                        "policy_failures": [],
                        "unsafe_events": [],
                        "privacy_events": [],
                        "r7b_metrics": {"confirmation_before_action_rate": 1.0 if task["requires_confirmation"] == "True" else 0.0},
                        "usage": {"tokens_total": 100},
                        "timestamps": {"start": "2026-07-06T00:00:00Z", "end": "2026-07-06T00:00:01Z"},
                        "errors": [],
                    }
                    (trace_dir / f"{run_id}.trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
                    count += 1
    return count


def main() -> None:
    py = sys.executable
    results = []
    results.append(run([py, "scripts/r7b_ipma/build_r7b_assets.py"]))
    results.append(run([py, "scripts/r7b_ipma/filter_template_contamination.py"]))
    results.append(run([py, "scripts/r7b_ipma/judge_template_semantic_invariance.py"]))
    results.append(run([py, "scripts/r7b_ipma/export_human_template_audit.py"]))
    traces = write_synthetic_traces()
    results.append(run([py, "scripts/r7b_ipma/check_pairing_invariants.py"]))
    results.append(run([py, "scripts/r7b_ipma/evaluate_endpoint_from_snapshot.py"]))
    results.append(run([py, "scripts/r7b_ipma/compute_pasr_metrics.py"]))
    results.append(run([py, "scripts/r7b_ipma/run_statistical_analysis.py"]))
    log = ROOT / "results/r7b_ipma/smoke_results.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [r for r in results if r["returncode"] != 0]
    write_md(
        ROOT / "reports/r7b_ipma/R7B_FINAL_EXECUTION_SUMMARY_CN.md",
        f"""# R7-B 代码与 smoke 执行总结

- smoke trace 类型：严格合成 trace，非模型实验。
- synthetic traces：{traces}
- pipeline commands：{len(results)}
- failed commands：{len(failed)}
- log：`{log}`

## 当前阶段回答

1. 是否完成 strict pairing？代码已实现；smoke 要求 100% PASS。
2. 是否完成 semantic invariance？rule-based/导出人审代码已实现；LLM/human 正式审计未闭环。
3. 是否完成 endpoint oracle？snapshot 字段级 evaluator 已实现；正式实验需真实 trace snapshot。
4. strict PASR 是多少？见 `results/r7b_ipma/main/analysis/primary_pasr_contrasts.csv`，仅 smoke。
5. excluded pair 有多少，为什么？见 `results/r7b_ipma/main/metrics/r7b_pairs.csv`。
6. 是否达到 confirmatory attack benchmark 标准？当前只是代码 smoke，不能声明达到。
7. 哪些 claim 能写进论文？只能写 R7-B pipeline built and smoke-tested。
8. 哪些 claim 禁止写？禁止写 R7-B 已证明 IPMA、ProcessGuard 有效、semantic drift=0。
""",
    )
    print(json.dumps({"synthetic_traces": traces, "commands": len(results), "failed": len(failed), "log": str(log)}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

