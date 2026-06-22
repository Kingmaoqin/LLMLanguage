"""Opening-event compatibility for current and legacy controlled-user traces."""

import unittest

from scripts.stage2_5b.final_integrity_audit import is_opening_event


class OpeningEventSchemaTest(unittest.TestCase):
    def test_current_event_index_is_canonical(self):
        self.assertTrue(
            is_opening_event({"user_event_idx": 0, "user_state": "request_open"})
        )
        self.assertFalse(
            is_opening_event({"user_event_idx": 1, "user_state": "turn_0"})
        )

    def test_legacy_state_name_is_supported(self):
        self.assertTrue(is_opening_event({"user_state": "turn_0"}))
        self.assertFalse(is_opening_event({"user_state": "request_open"}))
