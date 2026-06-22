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


if __name__ == "__main__":
    unittest.main()
