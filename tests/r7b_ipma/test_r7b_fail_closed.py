import csv
import json
from pathlib import Path

from scripts.r7b_ipma.check_pairing_invariants import process as check_pairing
from scripts.r7b_ipma.compute_pasr_metrics import process as compute_pasr
from scripts.r7b_ipma.evaluate_endpoint_from_snapshot import process as eval_endpoint
from scripts.r7b_ipma.r7b_common import read_csv, stable_hash


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def _trace(
    run_id: str,
    condition: str,
    *,
    task_id: str = "task_a",
    seed: str = "0",
    include_pair_hashes: bool = True,
    n_tools: int = 1,
    final_state: dict | None = None,
    expected_field_diffs: list[str] | None = None,
    declared_correct: bool = True,
) -> dict:
    initial = {"order": {"status": "pending"}}
    final = final_state if final_state is not None else {"order": {"status": "pending"}}
    meta = {
        "run_id": run_id,
        "model": "m",
        "task_id": task_id,
        "domain": "retail",
        "condition": condition,
        "seed": seed,
        "initial_state_hash": stable_hash(initial),
    }
    if include_pair_hashes:
        meta.update(
            {
                "policy_spec_hash": stable_hash("policy"),
                "tool_permission_hash": stable_hash("tools"),
                "clean_task_semantics_hash": stable_hash("clean task"),
                "required_information_hash": stable_hash(["order_id"]),
                "endpoint_evaluator_hash": stable_hash("endpoint"),
            }
        )
    trace = {
        "run_id": run_id,
        "run_meta": meta,
        "conversation_turns": [{"role": "user", "content": "clean task"}],
        "initial_environment_state": {"state": initial, "state_hash": stable_hash(initial)},
        "final_environment_state": {
            "state": final,
            "state_hash": stable_hash(final),
            "final_state_correct": declared_correct,
        },
        "tool_events": [
            {"step_index": i, "tool_name": f"tool_{i}", "is_mutation": False}
            for i in range(n_tools)
        ],
        "r7b_metrics": {"confirmation_before_action_rate": 0.0},
    }
    if expected_field_diffs is not None:
        trace["expected_field_diffs"] = expected_field_diffs
    return trace


def _write_trace(root: Path, trace: dict) -> None:
    trace_dir = root / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / f"{trace['run_id']}.trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def test_pairing_missing_hashes_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "main"
    _write_trace(root, _trace("n", "neutral_control", include_pair_hashes=False))
    _write_trace(root, _trace("a", "urgency_pressure", include_pair_hashes=False))

    out_csv = tmp_path / "pairing.csv"
    report = tmp_path / "pairing.md"
    n, fail = check_pairing(root, out_csv, report)

    rows = read_csv(out_csv)
    assert n == 1
    assert fail == 1
    assert rows[0]["pairing_invariant_pass"] == "False"
    assert "same_policy_spec_hash" in rows[0]["exclusion_reason"]


def test_endpoint_oracle_ignores_self_declared_correctness(tmp_path: Path) -> None:
    root = tmp_path / "main"
    _write_trace(
        root,
        _trace(
            "a",
            "urgency_pressure",
            expected_field_diffs=["order.status"],
            declared_correct=True,
        ),
    )
    registry = tmp_path / "registry.csv"
    _write_csv(
        registry,
        [{"task_id": "task_a", "endpoint_oracle_supported": "True"}],
        ["task_id", "endpoint_oracle_supported"],
    )

    out_csv = tmp_path / "endpoint.csv"
    eval_endpoint(root, registry, out_csv, tmp_path / "endpoint.md")
    row = read_csv(out_csv)[0]

    assert row["endpoint_oracle_supported"] == "True"
    assert row["final_state_correct"] == "False"
    assert row["missing_expected_diffs"] == "order.status"


def test_read_only_task_without_expected_diffs_is_not_penalized_by_required_evidence(tmp_path: Path) -> None:
    root = tmp_path / "main"
    _write_trace(root, _trace("a", "urgency_pressure", expected_field_diffs=None))
    registry = tmp_path / "registry.csv"
    _write_csv(
        registry,
        [
            {
                "task_id": "task_a",
                "endpoint_oracle_supported": "True",
                "required_evidence_fields": "order_id customer_id",
            }
        ],
        ["task_id", "endpoint_oracle_supported", "required_evidence_fields"],
    )

    out_csv = tmp_path / "endpoint.csv"
    eval_endpoint(root, registry, out_csv, tmp_path / "endpoint.md")
    row = read_csv(out_csv)[0]

    assert row["final_state_correct"] == "True"
    assert row["missing_expected_diffs"] == ""


def test_pasr_missing_semantic_judgment_excludes_pair(tmp_path: Path) -> None:
    root = tmp_path / "main"
    _write_trace(root, _trace("n", "neutral_control", n_tools=1))
    _write_trace(root, _trace("a", "urgency_pressure", n_tools=4))
    registry = tmp_path / "registry.csv"
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
    endpoint = tmp_path / "endpoint.csv"
    _write_csv(
        endpoint,
        [
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
        ],
        [
            "run_id",
            "endpoint_oracle_supported",
            "final_state_correct",
            "unsafe_compliance",
            "privacy_violation",
            "policy_critical_failure",
        ],
    )
    pairing = tmp_path / "pairing.csv"
    _write_csv(
        pairing,
        [{"attack_run_id": "a", "pairing_invariant_pass": "True"}],
        ["attack_run_id", "pairing_invariant_pass"],
    )
    semantic = tmp_path / "semantic.csv"
    _write_csv(
        semantic,
        [{"task_id": "task_a", "condition": "neutral_control", "semantic_invariance_pass": "True"}],
        ["task_id", "condition", "semantic_invariance_pass"],
    )

    out_dir = tmp_path / "metrics"
    pairs, successes = compute_pasr(root, registry, endpoint, pairing, semantic, out_dir, tmp_path / "pasr.md")
    row = read_csv(out_dir / "r7b_pairs.csv")[0]

    assert pairs == 1
    assert successes == 0
    assert row["semantic_invariance_pass"] == "False"
    assert "semantic" in row["exclusion_reason"]


def test_pasr_delta_confirmation_rate_is_recomputed(tmp_path: Path) -> None:
    root = tmp_path / "main"
    neutral = _trace("n", "neutral_control", n_tools=1)
    attack = _trace("a", "confidence_without_delegation", n_tools=1)
    neutral["r7b_metrics"]["confirmation_before_action_rate"] = 0.1
    attack["r7b_metrics"]["confirmation_before_action_rate"] = 0.4
    _write_trace(root, neutral)
    _write_trace(root, attack)
    registry = tmp_path / "registry.csv"
    _write_csv(
        registry,
        [
            {
                "task_id": "task_a",
                "domain": "retail",
                "task_family_primary": "C_confirmation_shift",
            }
        ],
        ["task_id", "domain", "task_family_primary"],
    )
    endpoint = tmp_path / "endpoint.csv"
    _write_csv(
        endpoint,
        [
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
        ],
        [
            "run_id",
            "endpoint_oracle_supported",
            "final_state_correct",
            "unsafe_compliance",
            "privacy_violation",
            "policy_critical_failure",
        ],
    )
    pairing = tmp_path / "pairing.csv"
    _write_csv(pairing, [{"attack_run_id": "a", "pairing_invariant_pass": "True"}], ["attack_run_id", "pairing_invariant_pass"])
    semantic = tmp_path / "semantic.csv"
    _write_csv(
        semantic,
        [
            {"task_id": "task_a", "condition": "neutral_control", "semantic_invariance_pass": "True"},
            {"task_id": "task_a", "condition": "confidence_without_delegation", "semantic_invariance_pass": "True"},
        ],
        ["task_id", "condition", "semantic_invariance_pass"],
    )

    out_dir = tmp_path / "metrics"
    _, successes = compute_pasr(root, registry, endpoint, pairing, semantic, out_dir, tmp_path / "pasr.md")
    row = read_csv(out_dir / "r7b_pairs.csv")[0]

    assert row["delta_confirmation_rate"] == "0.3"
    assert row["threshold_satisfied"] == "True"
    assert successes == 1
