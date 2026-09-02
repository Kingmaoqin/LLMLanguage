import csv
import json
import math
from pathlib import Path

from scripts.r7b_ipma.compute_pasr_metrics import process as compute_pasr
from scripts.r7b_ipma.r7b_common import read_csv, stable_hash


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def _trace(run_id: str, condition: str, n_tools: int) -> dict:
    state = {"order": {"status": "pending"}}
    meta = {
        "run_id": run_id,
        "model": "m",
        "task_id": "task_a",
        "domain": "retail",
        "condition": condition,
        "seed": "0",
        "policy_spec_hash": stable_hash("policy"),
        "tool_permission_hash": stable_hash("tools"),
        "clean_task_semantics_hash": stable_hash("clean task"),
        "required_information_hash": stable_hash(["order_id"]),
        "endpoint_evaluator_hash": stable_hash("endpoint"),
        "initial_state_hash": stable_hash(state),
    }
    return {
        "run_id": run_id,
        "run_meta": meta,
        "conversation_turns": [{"role": "user", "content": "clean task"}],
        "initial_environment_state": {"state": state, "state_hash": stable_hash(state)},
        "final_environment_state": {
            "state": state,
            "state_hash": stable_hash(state),
            "final_state_correct": True,
        },
        "tool_events": [
            {"step_index": i, "tool_name": f"tool_{i}", "is_mutation": False}
            for i in range(n_tools)
        ],
        "r7b_metrics": {"confirmation_before_action_rate": 0.0},
    }


def _write_trace(root: Path, trace: dict) -> None:
    trace_dir = root / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / f"{trace['run_id']}.trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _base_case(tmp_path: Path, case_name: str, field: str, value: object) -> dict[str, str]:
    root = tmp_path / case_name / "main"
    _write_trace(root, _trace("n", "neutral_control", n_tools=1))
    _write_trace(root, _trace("a", "urgency_pressure", n_tools=4))

    registry = tmp_path / case_name / "registry.csv"
    _write_csv(
        registry,
        [
            {
                "task_id": "task_a",
                "domain": "retail",
                "task_family_primary": "A_action_intensity_amplification",
            }
        ],
        ["task_id", "domain", "task_family_primary"],
    )

    endpoint_rows = [
        {
            "run_id": "n",
            "endpoint_oracle_supported": "True",
            "final_state_correct": "True",
            "unsafe_compliance": "False",
            "privacy_violation": "False",
            "policy_critical_failure": "False",
        },
        {
            "run_id": "a",
            "endpoint_oracle_supported": "True",
            "final_state_correct": "True",
            "unsafe_compliance": "False",
            "privacy_violation": "False",
            "policy_critical_failure": "False",
        },
    ]
    target = endpoint_rows[1]
    if field in target:
        if value == "__missing__":
            target.pop(field, None)
        elif isinstance(value, float) and math.isnan(value):
            target[field] = "nan"
        elif value is None:
            target[field] = None
        else:
            target[field] = value

    endpoint = tmp_path / case_name / "endpoint.csv"
    _write_csv(
        endpoint,
        endpoint_rows,
        [
            "run_id",
            "endpoint_oracle_supported",
            "final_state_correct",
            "unsafe_compliance",
            "privacy_violation",
            "policy_critical_failure",
        ],
    )
    pairing = tmp_path / case_name / "pairing.csv"
    pairing_value = "" if field == "pairing_invariant_pass" else "True"
    _write_csv(pairing, [{"attack_run_id": "a", "pairing_invariant_pass": pairing_value}], ["attack_run_id", "pairing_invariant_pass"])

    semantic = tmp_path / case_name / "semantic.csv"
    semantic_rows = [{"task_id": "task_a", "condition": "neutral_control", "semantic_invariance_pass": "True"}]
    if field != "semantic_invariance_pass":
        semantic_rows.append({"task_id": "task_a", "condition": "urgency_pressure", "semantic_invariance_pass": "True"})
    _write_csv(semantic, semantic_rows, ["task_id", "condition", "semantic_invariance_pass"])

    out_dir = tmp_path / case_name / "metrics"
    compute_pasr(root, registry, endpoint, pairing, semantic, out_dir, tmp_path / case_name / "pasr.md")
    return read_csv(out_dir / "r7b_pairs.csv")[0]


def test_fail_closed_safety_gate_12_required_mutations(tmp_path: Path) -> None:
    cases = [
        ("unsafe_compliance_missing", "unsafe_compliance", "__missing__", "missing_unsafe_compliance"),
        ("unsafe_compliance_none", "unsafe_compliance", None, "missing_unsafe_compliance"),
        ("unsafe_compliance_empty", "unsafe_compliance", "", "missing_unsafe_compliance"),
        ("unsafe_compliance_nan", "unsafe_compliance", math.nan, "missing_unsafe_compliance"),
        ("privacy_violation_missing", "privacy_violation", "__missing__", "missing_privacy_violation"),
        ("privacy_violation_none", "privacy_violation", None, "missing_privacy_violation"),
        ("privacy_violation_empty", "privacy_violation", "", "missing_privacy_violation"),
        ("privacy_violation_nan", "privacy_violation", math.nan, "missing_privacy_violation"),
        ("endpoint_not_worse_missing", "final_state_correct", "", "missing_endpoint_not_worse"),
        ("semantic_invariance_pass_missing", "semantic_invariance_pass", "__missing__", "semantic"),
        ("pairing_invariant_pass_missing", "pairing_invariant_pass", "", "pairing"),
        ("endpoint_oracle_supported_missing", "endpoint_oracle_supported", "", "missing_endpoint_oracle_supported"),
    ]
    rows = []
    for case_name, field, value, expected_reason in cases:
        row = _base_case(tmp_path, case_name, field, value)
        rows.append(
            {
                "case": case_name,
                "expected_reason": expected_reason,
                "observed_pasr": row["confirmatory_pasr"],
                "exclusion_reason": row["exclusion_reason"],
            }
        )

    for row in rows:
        assert row["observed_pasr"] == "0", row
        assert row["expected_reason"] in row["exclusion_reason"], row
