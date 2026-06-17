import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.scan_candidate_tasks import scan


class CandidateTaskScanTest(unittest.TestCase):
    def test_scan_selects_10_to_15_real_tasks(self):
        _all_rows, selected, counts = scan()
        self.assertGreaterEqual(counts["retail"], 10)
        self.assertGreaterEqual(counts["airline"], 10)
        self.assertGreaterEqual(len(selected), 10)
        self.assertLessEqual(len(selected), 15)
        self.assertTrue(all(r["status"] == "candidate_structural" for r in selected))
        self.assertTrue(all(int(r["write_action_count"]) > 0 for r in selected))


if __name__ == "__main__":
    unittest.main()
