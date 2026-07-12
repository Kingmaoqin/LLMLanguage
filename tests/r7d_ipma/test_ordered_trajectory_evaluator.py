import copy

import pytest

from scripts.r7d_ipma.reproducibility.ordered_trajectory_evaluator import (
    TrajectoryError, canonical_json, compare_trajectories,
)


MUT = {"modify_order", "cancel_reservation"}
BASE = {"actions": [
    {"name": "get_order", "arguments": {"order_id": "A1"}},
    {"name": "modify_order", "arguments": {"order_id": "A1", "color": "blue"}},
]}


def compare(value, endpoint=True, db=True):
    return compare_trajectories(BASE, value, mutation_tools=MUT,
                                endpoint_score_equal=endpoint, final_db_equal=db)


@pytest.mark.parametrize("kind,mutate,expected", [
    ("insert", lambda x: x["actions"].insert(1, {"name": "get_order", "arguments": {"order_id": "B2"}}), "insertion"),
    ("delete", lambda x: x["actions"].pop(0), "deletion"),
    ("duplicate", lambda x: x["actions"].append(copy.deepcopy(x["actions"][0])), "duplicate"),
    ("reorder", lambda x: x["actions"].reverse(), "reorder"),
    ("target", lambda x: x["actions"][0]["arguments"].update(order_id="B2"), "target_change"),
    ("argument", lambda x: x["actions"][1]["arguments"].update(color="red"), "argument_change"),
    ("mutating", lambda x: x["actions"][0].update(mutating=True), "mutation_class_change"),
])
def test_faults_are_detected(kind, mutate, expected):
    value = copy.deepcopy(BASE)
    mutate(value)
    result = compare(value)
    assert result["ordered_action_edit_distance"] > 0, kind
    assert expected in {k for edit in result["edits"] for k in edit["kinds"]}
    assert result["first_decisive_deviation"] is not None


def test_endpoint_same_process_different_is_corrupt_success_not_pasr():
    value = copy.deepcopy(BASE)
    value["actions"].reverse()
    result = compare(value)
    assert result["corrupt_success"] is True
    assert "not PASR" in result["claim_boundary"]


def test_order_multiplicity_and_nested_list_are_preserved():
    left = {"x": [1, 2, 2], "y": {"b": 1, "a": 2}}
    assert canonical_json(left) == canonical_json({"y": {"a": 2, "b": 1}, "x": [1, 2, 2]})
    assert canonical_json(left) != canonical_json({"x": [2, 1, 2], "y": {"a": 2, "b": 1}})


def test_malformed_call_fails_closed():
    with pytest.raises(TrajectoryError):
        compare({"actions": [{"name": "", "arguments": {}}]})

