import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.normalize import IRREVERSIBLE_TOOLS


class MutationToolClassificationTest(unittest.TestCase):
    def test_retail_address_and_payment_writes_are_mutations(self):
        expected = {
            "modify_pending_order_address",
            "modify_pending_order_items",
            "modify_pending_order_payment",
            "modify_user_address",
        }
        self.assertTrue(expected.issubset(IRREVERSIBLE_TOOLS))

    def test_airline_passenger_write_is_a_mutation(self):
        self.assertIn(
            "update_reservation_passengers",
            IRREVERSIBLE_TOOLS,
        )

    def test_read_tools_are_not_mutations(self):
        for tool in [
            "find_user_id_by_name_zip",
            "get_user_details",
            "get_order_details",
            "get_product_details",
            "get_reservation_details",
            "search_direct_flight",
        ]:
            self.assertNotIn(tool, IRREVERSIBLE_TOOLS)


if __name__ == "__main__":
    unittest.main()
