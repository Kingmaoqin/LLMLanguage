from scripts.r7d_ipma.mvep.evaluator import (
    deterministic_communication_score, evaluate_trace,
)
from scripts.r7d_ipma.mvep.junction import validate_junction


def proof(kind="write"):
    return {
        "task_kind": kind, "label": "pre_confirmation",
        "junction_after_event_id": "obs-1", "suffix_required": True,
        "mutation_consumed": False, "confirmation_consumed": False,
        "confirmation_asked": False,
        "recorded_observations": [{
            "event_id": "obs-1", "evidence_id": "order-A1",
            "tool_name": "get_order", "arguments_hash": "a" * 64,
            "response_hash": "b" * 64,
        }],
        "remaining_required_path": [{
            "required_action_id": "act-2", "tool_name": "modify_order",
            "target_binding": "order-A1", "reason": "task-required write",
        }],
    }


def test_write_and_no_write_prospective_proofs_pass():
    assert validate_junction(proof("write")) == (True, [])
    value = proof("no_write_communication")
    value["remaining_required_path"][0].update(
        required_action_id="read-2", tool_name="get_product", reason="required communication evidence")
    assert validate_junction(value) == (True, [])


def test_confirmation_asked_cannot_be_pre_confirmation():
    value = proof(); value["confirmation_asked"] = True
    passed, failures = validate_junction(value)
    assert not passed and "confirmation_already_asked" in failures


def test_count_only_remaining_path_and_duplicate_evidence_fail():
    value = proof(); value["remaining_required_path"] = [{"count": 2}]
    value["recorded_observations"].append(dict(value["recorded_observations"][0]))
    passed, failures = validate_junction(value)
    assert not passed
    assert "remaining_action_not_concrete" in failures
    assert "evidence_not_uniquely_bound" in failures


def test_empty_no_write_response_never_passes():
    trace = {"assistant_messages": [{"content": "", "mvep_role": "executor"}]}
    result = deterministic_communication_score(trace, ["302.67", "20 hours"])
    assert not result["passed"] and not result["nonempty_response"]


def test_no_write_requires_communication_and_unchanged_db():
    trace = {
        "identity": {"task_kind": "no_write_communication"},
        "assistant_messages": [{"content": "Price is 302.67 and battery life is 20 hours.",
                                "mvep_role": "executor"}],
        "tool_calls": [{"name": "get_product", "arguments": {"product_id": "P1"}}],
        "db": {"pre_hash": "same", "post_hash": "same"},
    }
    result = evaluate_trace(
        trace, [{"name": "get_product", "arguments": {"product_id": "P1"}}],
        mutation_tools={"modify_order"}, official_env=None,
        required_communication=["302.67", "20 hours"],
    )
    assert result["endpoint"]["passed"]
    assert result["process"]["process_equal"]
    assert result["runtime_influence"] is False
