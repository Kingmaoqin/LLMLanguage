"""spec 11.4 / 14: paired contrasts cluster on the SAME task/model/repeat cell, and
statistics cluster on TASK, not episode.

Also checks Holm correction ordering and that ITT keeps every frozen task (no per-cell
filter, spec 9.3) by ensuring pairing does not silently drop unmatched cells beyond the
required both-conditions-present rule.
"""
from scripts.r9_attack.analyze_confirmatory import (
    holm,
    paired_primary,
    permutation_test,
    task_cluster_bootstrap,
)


def _rec(task, model, repeat, condition, reads, prereq=1):
    calls = [{"turn": 0, "step": i, "name": "ls", "arguments": {}, "ok": True, "mutating": False}
             for i in range(reads)]
    calls.append({"turn": 0, "step": reads, "name": "mkdir", "arguments": {}, "ok": True, "mutating": True})
    return {
        "benchmark": "bfcl", "task_id": task, "model": model, "repeat": repeat,
        "condition": condition, "family": "compression", "infra_failure": False,
        "tool_calls": calls, "endpoint": {"success": 1},
        "min_prereq_verification_calls": prereq, "min_viable_total_verification_calls": prereq,
    }


def test_pairing_matches_same_cell_only():
    recs = [
        _rec("t1", "m", 0, "C4", 1), _rec("t1", "m", 0, "C1", 3),   # matched -> diff -2
        _rec("t1", "m", 1, "C4", 0),                                 # unmatched (no C1 in r1)
        _rec("t2", "m", 0, "C1", 2),                                 # unmatched (no C4)
    ]
    pairs = paired_primary(recs, "compression", "C4", "C1")
    assert len(pairs) == 1
    task, delta = pairs[0]
    assert task == "t1"
    assert delta == (1 - 3)  # verification_depth diff with prereq=1


def test_bootstrap_clusters_on_task_not_episode():
    # Two tasks, each with several repeats; a task with many repeats must not dominate by count.
    recs = []
    for r in range(10):
        recs += [_rec("tbig", "m", r, "C4", 0), _rec("tbig", "m", r, "C1", 4)]  # delta -4 x10
    recs += [_rec("tsmall", "m", 0, "C4", 3), _rec("tsmall", "m", 0, "C1", 3)]   # delta 0 x1
    pairs = paired_primary(recs, "compression", "C4", "C1")
    boot = task_cluster_bootstrap(pairs, n=500)
    # cluster means: tbig=-4, tsmall=0 -> point estimate is the mean of the TWO clusters = -2
    assert boot["n_tasks"] == 2
    assert abs(boot["mean"] - (-2.0)) < 1e-9


def test_permutation_p_in_unit_interval():
    recs = []
    for r in range(6):
        recs += [_rec("t1", "m", r, "C4", 0), _rec("t1", "m", r, "C1", 4)]
        recs += [_rec("t2", "m", r, "C4", 1), _rec("t2", "m", r, "C1", 4)]
    pairs = paired_primary(recs, "compression", "C4", "C1")
    p = permutation_test(pairs, n=500)
    assert 0.0 <= p <= 1.0


def test_holm_is_monotone_and_bounded():
    adj = holm({"a": 0.001, "b": 0.02, "c": 0.5, "d": 0.9})
    assert all(0 <= v <= 1 for v in adj.values())
    # smallest raw p gets multiplied by m=4
    assert abs(adj["a"] - 0.004) < 1e-9
    # monotone non-decreasing in raw-p order
    assert adj["a"] <= adj["b"] <= adj["c"] <= adj["d"]
