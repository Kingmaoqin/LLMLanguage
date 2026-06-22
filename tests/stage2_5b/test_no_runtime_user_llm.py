import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.stage2_5b.controlled_user import ControlledUser


class NoRuntimeUserLlmTest(unittest.TestCase):
    def test_controlled_user_rejects_llm(self):
        with self.assertRaises(ValueError):
            ControlledUser(
                "2",
                domain="retail",
                llm="openai/any-model",
            )

    def test_runner_uses_no_llm_user_identifier(self):
        runner = (
            ROOT
            / "scripts"
            / "stage2_5b"
            / "run_stage2_5b_experiment.py"
        ).read_text(encoding="utf-8")
        self.assertIn('llm_user="controlled_user_no_llm"', runner)
        self.assertNotIn("generic_" + "policy_from_task", runner)


if __name__ == "__main__":
    unittest.main()
