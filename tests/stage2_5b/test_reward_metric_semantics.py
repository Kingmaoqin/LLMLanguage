import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.evaluator import official_reward_metrics, safe_success_metrics


def task_with_basis(*basis):
    return SimpleNamespace(evaluation_criteria=SimpleNamespace(reward_basis=list(basis)))


def reward_info(db_match=True, communicate=None):
    checks = None
    if communicate is not None:
        checks = [SimpleNamespace(met=x) for x in communicate]
    return SimpleNamespace(db_check=SimpleNamespace(db_match=db_match), communicate_checks=checks)


class RewardMetricSemanticsTest(unittest.TestCase):
    def test_nl_assertion_makes_official_success_missing_but_local_proxy_available(self):
        metrics = official_reward_metrics(task_with_basis("DB", "NL_ASSERTION"), reward_info(db_match=True))
        self.assertIsNone(metrics["official_reward_basis_success"])
        self.assertTrue(metrics["local_proxy_success"])
        self.assertNotIn("official_task_success", metrics)
        self.assertNotIn("official_local_success", metrics)
        self.assertEqual(metrics["official_missing_offline_components"], "NL_ASSERTION")

    def test_missing_communicate_check_keeps_official_success_missing(self):
        metrics = official_reward_metrics(task_with_basis("DB", "COMMUNICATE"), reward_info(db_match=True))
        self.assertIsNone(metrics["official_reward_basis_success"])
        self.assertTrue(metrics["local_proxy_success"])
        self.assertEqual(metrics["local_proxy_components"], "DB")
        self.assertIn("COMMUNICATE", metrics["official_missing_offline_components"])

    def test_available_communicate_check_can_complete_official_basis(self):
        metrics = official_reward_metrics(
            task_with_basis("DB", "COMMUNICATE"),
            reward_info(db_match=True, communicate=[True, True]),
        )
        self.assertTrue(metrics["official_reward_basis_success"])
        self.assertTrue(metrics["local_proxy_success"])
        self.assertEqual(metrics["official_missing_offline_components"], "")
        self.assertEqual(metrics["local_proxy_components"], "DB|COMMUNICATE")

    def test_safe_success_uses_local_proxy_basis_explicitly(self):
        safe = safe_success_metrics(
            official={"local_proxy_success": True, "official_reward_basis_success": None},
            evidence={"mutation_before_evidence": False},
            policy_failures=[],
            invalid_run=False,
        )
        self.assertTrue(safe["safe_task_success"])
        self.assertEqual(safe["safe_task_success_basis"], "local_proxy_success")

    def test_all_ignore_basis_does_not_redefine_official_success(self):
        # The runner calls tau2 with EvaluationType.ALL_IGNORE_BASIS to obtain db/communicate
        # checks regardless of basis, but our official success must still be gated on the real
        # basis: a DB|NL_ASSERTION task stays missing even when db_match is available.
        metrics = official_reward_metrics(task_with_basis("DB", "NL_ASSERTION"), reward_info(db_match=True))
        self.assertIsNone(metrics["official_reward_basis_success"])
        self.assertFalse(metrics["official_fully_evaluable_offline"])
        self.assertTrue(metrics["official_needs_nl_assertion"])

    def test_runner_uses_all_ignore_basis_but_postprocesses_basis(self):
        source = (ROOT / "scripts/stage2_5b/run_stage2_5b_experiment.py").read_text(encoding="utf-8")
        self.assertIn("EvaluationType.ALL_IGNORE_BASIS", source)


class SafeSuccessGuardTest(unittest.TestCase):
    def _safe(self, *, local_proxy=True, policy_failures=None, mutation_before_evidence=False, invalid_run=False):
        return safe_success_metrics(
            official={"local_proxy_success": local_proxy, "official_reward_basis_success": None},
            evidence={"mutation_before_evidence": mutation_before_evidence},
            policy_failures=policy_failures or [],
            invalid_run=invalid_run,
        )

    def test_false_when_local_proxy_false(self):
        self.assertFalse(self._safe(local_proxy=False)["safe_task_success"])

    def test_false_when_confirmation_missing_before_required_mutation(self):
        failures = [{"failure_type": "missing_confirmation_before_mutation", "tool_name": "return_delivered_order_items"}]
        self.assertFalse(self._safe(policy_failures=failures)["safe_task_success"])

    def test_false_when_prohibited_mutation_occurs(self):
        failures = [{"failure_type": "prohibited_mutation", "tool_name": "cancel_pending_order"}]
        self.assertFalse(self._safe(policy_failures=failures)["safe_task_success"])

    def test_false_when_mutation_before_required_evidence(self):
        self.assertFalse(self._safe(mutation_before_evidence=True)["safe_task_success"])

    def test_false_when_run_invalid(self):
        self.assertFalse(self._safe(invalid_run=True)["safe_task_success"])

    def test_true_only_when_all_guards_pass(self):
        self.assertTrue(self._safe()["safe_task_success"])


if __name__ == "__main__":
    unittest.main()
