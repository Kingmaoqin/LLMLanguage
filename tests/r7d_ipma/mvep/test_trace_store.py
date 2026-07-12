import copy
import json

import pytest

from scripts.r7d_ipma.mvep.trace_store import TraceStore, trace_complete


STAGES = ["PREFIX_CAPTURED", "JUNCTION_PROOF", "CALL_PREPARED", "CALL_RESPONSE",
          "TOOL_RESPONSE", "SCORER_RESULT"]


@pytest.mark.parametrize("crash_after", STAGES)
def test_crash_recovery_is_append_only_at_every_stage(tmp_path, crash_after):
    root = tmp_path / crash_after
    store = TraceStore.create(root, {"trajectory_id": crash_after}, "a" * 64)
    for stage in STAGES:
        store.append(stage, {"stage": stage})
        if stage == crash_after:
            break
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    recovered = TraceStore.recover(root, "synthetic_crash")
    for name, body in before.items():
        assert (root / name).read_bytes() == body
    assert recovered.events[-1]["event"] == "RECOVERY_DECLARED"
    recovered.terminal("ABORTED_SYNTHETIC")
    assert TraceStore.read_and_validate(root)[-1]["event"] == "TERMINAL"


def test_existing_root_and_terminal_resume_fail_closed(tmp_path):
    root = tmp_path / "run"
    store = TraceStore.create(root, {"trajectory_id": "x"}, "a" * 64)
    with pytest.raises(FileExistsError):
        TraceStore.create(root, {}, "b" * 64)
    store.terminal("PASS")
    with pytest.raises(RuntimeError, match="terminal"):
        TraceStore.recover(root, "not_allowed")
    with pytest.raises(RuntimeError, match="immutable"):
        store.append("CALL_EXCEPTION", {})


def test_nested_parent_then_exclusive_leaf_lifecycle(tmp_path):
    parent = tmp_path / "results" / "r7d_ipma" / "mvep"
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / "run_v1"
    store = TraceStore.create(root, {"trajectory_id": "x"}, "a" * 64)
    store.terminal("PASS")
    with pytest.raises(FileExistsError):
        TraceStore.create(root, {"trajectory_id": "replacement"}, "a" * 64)


def test_render_incident_recovery_preserves_partial_and_uses_attempt2(tmp_path):
    root = tmp_path / "cell"
    store = TraceStore.create(root, {"trajectory_id": "cell"}, "a" * 64)
    store.append("PREFIX_CAPTURED", {"content": None})
    store.append("JUNCTION_PROOF", {"passed": True})
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    recovered = TraceStore.recover(root, "render_incident")
    recovered.terminal("ABORTED-PRE-MODEL-CALL-RENDER")
    for name, body in before.items():
        assert (root / name).read_bytes() == body
    attempt2 = root.parent / "cell__attempt2"
    second = TraceStore.create(attempt2, {"trajectory_id": "cell"}, "b" * 64)
    second.terminal("CAPTURED")
    assert root.exists() and attempt2.exists()


def test_tamper_and_missing_sequence_are_detected(tmp_path):
    root = tmp_path / "run"
    store = TraceStore.create(root, {"trajectory_id": "x"}, "a" * 64)
    store.append("PREFIX_CAPTURED", {"x": 1})
    path = root / "0001_PREFIX_CAPTURED.json"
    value = json.loads(path.read_text()); value["payload"]["x"] = 2
    path.chmod(0o644); path.write_text(json.dumps(value)); path.chmod(0o444)
    with pytest.raises(RuntimeError, match="hash"):
        TraceStore.read_and_validate(root)


def test_full_trace_completeness_and_token_fail_closed():
    trace = {key: {} for key in (
        "identity", "rendered_messages", "assistant_messages", "tool_calls",
        "tool_responses", "db", "scorer", "timing", "retry",
        "code_environment_model_hashes", "junction_proof",
    )}
    trace.update(schema_version="r7d-mvep-raw-trace-v1", manifest_hash="a" * 64,
                 environment_lock_hash="b" * 64, input_hash="c" * 64,
                 tokens={"input": 1, "output": 2, "tool": 3, "total": 6})
    assert trace_complete(trace) == (True, [])
    broken = copy.deepcopy(trace); broken["tokens"]["tool"] = None
    assert trace_complete(broken)[0] is False
