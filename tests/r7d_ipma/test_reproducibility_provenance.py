import json

import pytest

from scripts.r7d_ipma.reproducibility.provenance import (
    AppendOnlyJournal, replay_recorded_trace, verify_two_replays,
)


TRACE = {
    "rendered_input": "system\nuser request",
    "token_texts": {"prompt": "system user request", "completion": "done"},
    "messages": [{"tool_calls": [
        {"id": "1", "name": "get_order", "arguments": {"order_id": "A1"}},
        {"id": "2", "name": "modify_order", "arguments": {"order_id": "A1"}},
    ]}],
    "expected_score": 1.0,
    "expected_db_hash": "db-final",
}


def test_two_independent_replays_are_identical_and_no_write():
    original = json.dumps(TRACE, sort_keys=True)
    kwargs = dict(
        mutation_tools={"modify_order"},
        scorer=lambda trace: trace["expected_score"],
        db_replayer=lambda trace: trace["expected_db_hash"],
        token_counter=lambda text: len(text.split()),
    )
    result = verify_two_replays(TRACE, **kwargs)
    assert result["identical"]
    assert result["first"]["ordered_tool_names"] == ["get_order", "modify_order"]
    assert result["first"]["mutating_flags"] == [False, True]
    assert json.dumps(TRACE, sort_keys=True) == original


def test_token_accounting_fails_closed_when_text_missing():
    trace = dict(TRACE)
    trace.pop("token_texts")
    with pytest.raises(ValueError, match="incomplete_token_texts"):
        replay_recorded_trace(trace, mutation_tools=set(), scorer=lambda _: 1,
                              db_replayer=lambda _: "db", token_counter=lambda _: 0)


def test_append_only_state_machine_refuses_overwrite_and_bad_order(tmp_path):
    journal = AppendOnlyJournal(tmp_path / "journal")
    journal.append("PREPARED", {"input_hash": "x"})
    with pytest.raises(FileExistsError):
        journal.append("PREPARED", {"input_hash": "changed"})
    with pytest.raises(RuntimeError, match="out_of_order"):
        journal.append("CAPTURED", {})
    journal.append("COMMITTED", {"request_hash": "r"})
    journal.append("CAPTURED", {"response_hash": "s"})
    journal.append("TERMINAL", {"status": "ok"})
    assert len(list((tmp_path / "journal").glob("*.json"))) == 4


def test_existing_run_root_fails_closed(tmp_path):
    (tmp_path / "run").mkdir()
    with pytest.raises(FileExistsError):
        AppendOnlyJournal(tmp_path / "run")
