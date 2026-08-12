"""spec 11.1: R9 must use BFCL's OWN native multi_turn_checker, not a copy.

Runs the official ground-truth trajectory through the adapter's scoring path and asserts
the native checker returns success=1; runs a corrupted trajectory and asserts success=0.
Also checks the measured mutation flags on the GT profile are non-trivial. Requires the
bfcl_eval package (skipped otherwise).
"""
import pytest

bfcl = pytest.importorskip("bfcl_eval")

from scripts.r9_attack.adapters.bfcl_adapter import BfclAdapter  # noqa: E402


@pytest.fixture(scope="module")
def adapter():
    return BfclAdapter(endpoints={})


def _decode_ground_truth(adapter, task_id):
    entries, gts = adapter._load_raw()
    return entries[task_id], gts[task_id]


def test_native_checker_passes_ground_truth(adapter):
    task_id = "multi_turn_base_0"
    entry, gt = _decode_ground_truth(adapter, task_id)
    # Feed the official GT calls as the model's decoded output -> must pass natively.
    decoded = [[turn] for turn in gt]  # one step per turn, each step a list of call strings
    endpoint = adapter._score(entry, gt, decoded, namespace=f"pytest_{task_id}")
    assert endpoint.success == 1
    assert endpoint.evaluator == "bfcl.multi_turn_checker"


def test_native_checker_fails_corrupted_trajectory(adapter):
    task_id = "multi_turn_base_0"
    entry, gt = _decode_ground_truth(adapter, task_id)
    # Drop every call from the last turn -> state must diverge -> fail.
    decoded = [[turn] for turn in gt]
    decoded[-1] = [["cd(folder='nonexistent_dir_zzz')"]]
    endpoint = adapter._score(entry, gt, decoded, namespace=f"pytest_bad_{task_id}")
    assert endpoint.success == 0


def test_reference_profile_detects_mutations(adapter):
    task = adapter.load_tasks(["multi_turn_base_0"])[0]
    # multi_turn_base_0 creates a dir and moves files -> must contain mutating funcs.
    assert task.meta["gt_mutating_functions"], "expected >=1 mutating GT function"
    assert task.meta["gt_read_functions"], "expected >=1 read GT function"
    assert task.min_prereq_verification_calls >= 1
    assert task.complexity_ok()
