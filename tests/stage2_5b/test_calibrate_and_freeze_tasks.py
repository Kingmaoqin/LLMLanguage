import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.calibrate_and_freeze_tasks import classify


def stats(success_rate: float = 0.5) -> dict[str, float]:
    return {"success_rate": success_rate, "invalid_rate": 0.0}


class CalibrateAndFreezeTasksTest(unittest.TestCase):
    def test_nl_assertion_is_exploratory_by_default(self):
        cand = {
            "is_multistage_reference": "true",
            "official_reward_basis_fully_local": "false",
            "branch_proxy_count": "4",
            "has_policy_sensitive_decision": "true",
        }
        classification, reason, mean_success = classify("retail_21", cand, stats(0.4), stats(0.6))
        self.assertEqual(classification, "exploratory_nl_assertion")
        self.assertIn("NL_ASSERTION", reason)
        self.assertEqual(mean_success, 0.5)

    def test_retail_local_db_flag_allows_retail_mid_band(self):
        cand = {
            "is_multistage_reference": "true",
            "official_reward_basis_fully_local": "false",
            "branch_proxy_count": "4",
            "has_policy_sensitive_decision": "true",
        }
        classification, reason, _mean_success = classify(
            "retail_21",
            cand,
            stats(0.4),
            stats(0.6),
            retail_local_db_confirmatory=True,
        )
        self.assertEqual(classification, "confirmatory")
        self.assertIn("official_reward_basis_success reported MISSING", reason)

    def test_retail_local_db_flag_does_not_allow_airline_nl_assertion(self):
        cand = {
            "is_multistage_reference": "true",
            "official_reward_basis_fully_local": "false",
            "branch_proxy_count": "4",
            "has_policy_sensitive_decision": "true",
        }
        classification, _reason, _mean_success = classify(
            "airline_7",
            cand,
            stats(0.4),
            stats(0.6),
            retail_local_db_confirmatory=True,
        )
        self.assertEqual(classification, "exploratory_nl_assertion")


if __name__ == "__main__":
    unittest.main()
