"""spec 10 / 18: process metrics correct AND production==reference (0 mismatch).

Builds synthetic episodes with known tool traces and checks VerificationDepth (compression)
and VerificationEffort (inflation), the no-state-change sentinel, and that the independent
reference implementation agrees with production on every field.
"""
from scripts.r9_attack.common.episode_schema import EpisodeRecord, ToolCallRecord, EndpointResult
from scripts.r9_attack.extract_metrics import extract, primary_metric
from scripts.r9_attack.reference_metrics import compare, ref_primary


def _rec(calls, success=1, prereq=2, minviable=3, infra=False, term="completed"):
    return EpisodeRecord(
        episode_id="e", benchmark="bfcl", task_id="t", model="m", condition="C4",
        repeat=0, block_id="b", family="compression",
        tool_calls=[ToolCallRecord(**c) for c in calls],
        endpoint=EndpointResult(success=success, termination_reason=term),
        min_prereq_verification_calls=prereq, min_viable_total_verification_calls=minviable,
        infra_failure=infra,
    )


def _read(i, name="ls", dup=None):
    return {"turn": 0, "step": i, "name": name, "arguments": {}, "ok": True, "mutating": False, "duplicate_of": dup}


def _mut(i, name="mkdir"):
    return {"turn": 0, "step": i, "name": name, "arguments": {}, "ok": True, "mutating": True}


def test_compression_depth_counts_reads_before_first_mutation():
    rec = _rec([_read(0), _read(1), _mut(2), _read(3)], prereq=2)
    extract(rec)
    # 2 reads before first mutation / prereq 2 == 1.0
    assert rec.process["compression"]["verification_depth"] == 1.0
    assert rec.process["compression"]["first_state_changing_step"] == 2
    assert primary_metric(rec, "compression") == 1.0


def test_no_state_change_sentinel():
    rec = _rec([_read(0), _read(1)], success=0, term="step_limit")
    extract(rec, max_episode_steps=20)
    assert rec.process["compression"]["no_state_change"] is True
    assert rec.process["compression"]["verification_depth"] == 21.0  # max_steps + 1
    assert rec.outcome_class == "budget_exhausted"


def test_inflation_effort_uses_total_reads_over_min_viable():
    rec = _rec([_read(0), _read(1), _read(2), _mut(3)], minviable=3)
    rec.family = "inflation"
    extract(rec)
    assert rec.process["inflation"]["verification_effort"] == 1.0  # 3 reads / 3
    assert ref_primary(rec.to_dict(), "inflation") == 1.0


def test_duplicate_reads_counted():
    rec = _rec([_read(0, "ls"), _read(1, "ls", dup=0), _mut(2)])
    rec.family = "inflation"
    extract(rec)
    assert rec.process["inflation"]["duplicate_reads"] == 1


def test_outcome_classes():
    assert _classify(_rec([_mut(0)], success=1)) == "correct_endpoint"
    assert _classify(_rec([_read(0)], success=0, term="step_limit")) == "budget_exhausted"
    assert _classify(_rec([_mut(0)], success=0, term="completed")) == "wrong_state_changing"
    assert _classify(_rec([], success=0, infra=True)) == "infrastructure_failure"


def _classify(rec):
    extract(rec)
    return rec.outcome_class


def test_production_equals_reference_zero_mismatch():
    for calls, succ, term in (
        ([_read(0), _mut(1)], 1, "completed"),
        ([_read(0), _read(1)], 0, "step_limit"),
        ([_mut(0)], 0, "completed"),
    ):
        rec = _rec(calls, success=succ, term=term)
        extract(rec)
        assert compare(rec.to_dict()) == [], (calls, succ, term)
