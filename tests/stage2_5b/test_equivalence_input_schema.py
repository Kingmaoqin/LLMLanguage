from __future__ import annotations

import unittest

from scripts.stage2_5b.equivalence_analysis import REQUIRED_COLUMNS


class EquivalenceInputSchemaTest(unittest.TestCase):
    def test_requires_aggregated_contrast_columns(self) -> None:
        self.assertEqual(REQUIRED_COLUMNS, {"outcome", "ci_low", "ci_high"})


if __name__ == "__main__":
    unittest.main()
