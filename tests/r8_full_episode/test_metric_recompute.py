"""Independent metric recompute must be correct on a hand-built trace (spec 14).
Exercises tool-call counting, mutation detection, duplicate reads, error-driven
retry, and confirmation-before-mutation ordering."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r8_full_episode.extract_episode_metrics import compute_metrics


def _trace():
    # retail episode: 2 reads (one duplicated), a user confirmation, then 1 mutation.
    return dict(
        run_id="t", domain="retail", task_id="25", task_type="single",
        model="m", condition="C3", replicate=0, official_reward=1.0,
        reward_components={"db_component": 1.0, "communicate_met": 1, "n_communicate_checks": 1,
                           "overall_reward": 1.0},
        tokens_total=100, duration_seconds=1.0,
        agent_tool_calls=[], tool_results=[{"id": "e1", "error": "boom"}],
        user_state_records=[],
        native_messages=[
            {"role": "assistant", "content": None, "turn_idx": 0,
             "tool_calls": [{"name": "get_user_details", "arguments": {"u": 1}, "id": "a"}]},
            {"role": "assistant", "content": None, "turn_idx": 1,
             "tool_calls": [{"name": "get_user_details", "arguments": {"u": 1}, "id": "e1"}]},  # errored
            {"role": "assistant", "content": None, "turn_idx": 2,
             "tool_calls": [{"name": "get_user_details", "arguments": {"u": 1}, "id": "b"}]},  # retry
            {"role": "assistant", "content": "Please confirm the exchange.", "turn_idx": 3},
            {"role": "user", "content": "Yes, that's correct. Please proceed.", "turn_idx": 4},
            {"role": "assistant", "content": None, "turn_idx": 5,
             "tool_calls": [{"name": "exchange_delivered_order_items", "arguments": {}, "id": "c"}]},
        ],
    )


def test_tool_and_mutation_counts():
    m = compute_metrics(_trace(), "retail")
    assert m["total_agent_tool_calls"] == 4
    assert m["unique_tool_calls"] == 2  # get_user_details(u=1) and the exchange
    assert m["mutation_count"] == 1
    assert m["duplicate_read_calls"] == 2  # 2nd & 3rd get_user_details repeat the read


def test_error_driven_retry_counted():
    m = compute_metrics(_trace(), "retail")
    # the call after the errored 'e1' repeats (name,args) -> exactly one error-driven retry
    assert m["retry_count"] == 1
    assert m["invalid_tool_calls"] == 1


def test_confirmation_before_mutation_ordering():
    m = compute_metrics(_trace(), "retail")
    assert m["confirmation_requested"] is True
    assert m["confirmation_obtained"] is True
    assert m["confirmation_before_mutation"] is True  # user affirmed (turn 4) before mutation (turn 5)


def test_primary_reward_passthrough():
    m = compute_metrics(_trace(), "retail")
    assert m["official_reward"] == 1.0 and m["db_component"] == 1.0
