import unittest
from unittest.mock import Mock

from src.trading.reconciliation import Reconciler, floor_step
from src.trading.risk import RiskManager
from src.trading.account import AccountSnapshot, Position
from src.trading.config import SETTINGS


def make_account(equity=1000.0, available=500.0):
    return AccountSnapshot(
        account_id="test",
        account_value=equity,
        available_funds=available,
        total_margin_used=0.0,
        positions=(),
        open_orders=(),
    )


def make_position(size=1.0, liquidation_price=90.0):
    return Position(
        instrument="BTC_USDC-PERPETUAL",
        size=size,
        entry_price=100.0,
        mark_price=100.0,
        liquidation_price=liquidation_price,
        leverage=2.0,
        margin_used=50.0,
        position_value=100.0,
        unrealized_pnl=0.0,
    )


class FloorStepTests(unittest.TestCase):
    def test_positive_value_rounds_down(self):
        self.assertAlmostEqual(floor_step(1.239, 2), 1.23)

    def test_negative_value_keeps_sign_and_rounds_magnitude_down(self):
        self.assertAlmostEqual(floor_step(-1.239, 2), -1.23)

    def test_small_negative_value_keeps_sign(self):
        self.assertAlmostEqual(floor_step(-0.009, 2), 0.0)


class RiskManagerTests(unittest.TestCase):
    def setUp(self):
        self.risk = RiskManager(SETTINGS)

    def test_zero_available_funds_means_zero_target(self):
        account = make_account(equity=1000.0, available=0.0)
        self.assertEqual(self.risk.target_notional(account, 1), 0.0)

    def test_negative_available_funds_means_zero_target(self):
        account = make_account(equity=1000.0, available=-10.0)
        self.assertEqual(self.risk.target_notional(account, 1), 0.0)

    def test_missing_liquidation_price_is_not_safe_for_open_position(self):
        self.assertFalse(
            self.risk.liquidation_distance_ok(
                make_position(liquidation_price=None), 100.0
            )
        )

    def test_non_positive_price_is_not_safe_for_open_position(self):
        self.assertFalse(
            self.risk.liquidation_distance_ok(make_position(), 0.0)
        )


class ReconcilerValidationTests(unittest.TestCase):
    def setUp(self):
        self.broker = Mock()
        self.reconciler = Reconciler(self.broker, SETTINGS)

    def test_zero_price_is_rejected(self):
        with self.assertRaises(ValueError):
            self.reconciler.reconcile(
                "BTC_USDC-PERPETUAL", 1, 100.0, 0.0
            )
        self.broker.account_snapshot.assert_not_called()

    def test_nan_price_is_rejected(self):
        with self.assertRaises(ValueError):
            self.reconciler.reconcile(
                "BTC_USDC-PERPETUAL", 1, 100.0, float("nan")
            )
        self.broker.account_snapshot.assert_not_called()

    def test_negative_target_notional_is_rejected(self):
        with self.assertRaises(ValueError):
            self.reconciler.reconcile(
                "BTC_USDC-PERPETUAL", 1, -1.0, 100.0
            )
        self.broker.account_snapshot.assert_not_called()

    def test_invalid_target_side_is_rejected(self):
        with self.assertRaises(ValueError):
            self.reconciler.reconcile(
                "BTC_USDC-PERPETUAL", 2, 100.0, 100.0
            )
        self.broker.account_snapshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
