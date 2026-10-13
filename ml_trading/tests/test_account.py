import math
import unittest

from src.trading.account import build_snapshot


def valid_summary():
    return {
        "equity": 1000.0,
        "available_funds": 500.0,
        "initial_margin": 100.0,
    }


class AccountParserTests(unittest.TestCase):
    def test_valid_empty_account(self):
        snapshot = build_snapshot("test", valid_summary(), [], [])
        self.assertEqual(snapshot.account_value, 1000.0)
        self.assertEqual(snapshot.available_funds, 500.0)
        self.assertEqual(snapshot.positions, ())
        self.assertEqual(snapshot.open_orders, ())

    def test_missing_equity_is_rejected(self):
        summary = {"available_funds": 500.0}
        with self.assertRaises((ValueError, TypeError)):
            build_snapshot("test", summary, [], [])

    def test_missing_available_funds_is_rejected(self):
        summary = {"equity": 1000.0}
        with self.assertRaises((ValueError, TypeError)):
            build_snapshot("test", summary, [], [])

    def test_non_finite_equity_is_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                summary = valid_summary()
                summary["equity"] = value
                with self.assertRaises((ValueError, TypeError)):
                    build_snapshot("test", summary, [], [])

    def test_malformed_positions_collection_is_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            build_snapshot("test", valid_summary(), "not-a-list", [])

    def test_malformed_orders_collection_is_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            build_snapshot("test", valid_summary(), [], "not-a-list")


if __name__ == "__main__":
    unittest.main()
