"""The NATIVE tau2 evaluator must return a non-None reward when replaying the
task's own golden reference actions, and must NOT be a copied/modified evaluator
(spec 7, 14). This exercises evaluate_simulation on a golden trajectory."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_uses_native_evaluate_simulation_symbol():
    # run_full_episode must import the native evaluator, not a local copy.
    src = (ROOT / "scripts/r8_full_episode/run_full_episode.py").read_text()
    assert "from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation" in src
    assert "from tau2.runner.simulation import run_simulation" in src


def test_native_golden_reward_is_one_and_non_none():
    from scripts.r7d_ipma.step2_1.official_scorer import (
        official_reward, golden_trajectory, configure_local_nl_judge,
    )
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.run import get_tasks
    configure_local_nl_judge()  # local NL judge for COMMUNICATE reachability
    # a retail task with a golden action trajectory -> DB reward must be 1.0, non-None
    task = {str(t.id): t for t in get_tasks("retail")}["25"]
    r = official_reward(golden_trajectory(task, "retail"), task, "retail", EvaluationType.ENV)
    assert r.reward is not None, "native scorer returned None on golden trajectory"
    assert r.reward == 1.0, f"golden DB reward should be 1.0, got {r.reward}"
