from __future__ import annotations

import math
import uuid
from typing import Any

from .coinbase_client import CoinbaseBroker
from .config import Settings


def floor_step(value: float, decimals: int) -> float:
    if decimals < 0:
        raise ValueError("decimals must be non-negative")

    factor = 10**decimals
    magnitude = math.floor(abs(value) * factor + 1e-12) / factor
    return math.copysign(magnitude, value)


class Reconciler:
    def __init__(self, broker: CoinbaseBroker, settings: Settings):
        self.broker = broker
        self.settings = settings

    def _ensure_no_open_orders(self, symbol: str):
        account = self.broker.account_snapshot()

        if account.open_orders:
            raise RuntimeError(
                f"Refusing to trade {symbol}: "
                f"{len(account.open_orders)} open order(s) exist. "
                "Review/cancel them before the bot trades again."
            )

        return account

    def reconcile(
        self,
        symbol: str,
        target_side: int,
        target_notional: float,
        mark_price: float,
    ) -> list[dict[str, Any]]:
        # Validate inputs before account access or order sizing.
        if target_side not in (-1, 0, 1):
            raise ValueError("target_side must be -1, 0, or 1")

        if not math.isfinite(mark_price) or mark_price <= 0:
            raise ValueError(
                "mark_price must be finite and greater than zero"
            )

        if (
            not math.isfinite(target_notional)
            or target_notional < 0
        ):
            raise ValueError(
                "target_notional must be finite and non-negative"
            )

        account = self._ensure_no_open_orders(symbol)
        current = account.position_for(symbol)

        # A zero target means close any existing position.
        if target_side == 0:
            if current.side == 0:
                return []

            label = f"ml-close-{uuid.uuid4().hex[:20]}"
            response = self.broker.close_position(symbol, label)

            return [
                {
                    "action": "CLOSE",
                    "label": label,
                    "response": str(response),
                }
            ]

        # Calculate the target base-asset size.
        # IMPORTANT: Confirm the exchange's amount/contract units
        # before enabling live orders.
        target_abs_size = target_notional / mark_price

        decimals = self.broker.amount_precision(symbol)
        min_amount = self.broker.min_trade_amount(symbol)

        if decimals < 0:
            raise ValueError("amount precision must be non-negative")

        if not math.isfinite(min_amount) or min_amount < 0:
            raise ValueError("minimum trade amount is invalid")

        target_abs_size = floor_step(target_abs_size, decimals)

        if target_abs_size < min_amount:
            target_abs_size = 0.0

        current_size = current.size

        # Close a position in the opposite direction first.
        # Opening the new direction is deferred to a later cycle,
        # after the actual position can be checked again.
        if current.side != 0 and current.side != target_side:
            label = f"ml-reverse-close-{uuid.uuid4().hex[:16]}"
            response = self.broker.close_position(symbol, label)

            return [
                {
                    "action": "REVERSE_CLOSE",
                    "label": label,
                    "response": str(response),
                }
            ]

        desired_size = target_abs_size * target_side
        delta = desired_size - current_size
        delta = floor_step(delta, decimals)

        if abs(delta) < min_amount:
            return []

        is_buy = delta > 0
        label = f"ml-open-{uuid.uuid4().hex[:20]}"

        response = self.broker.open_market(
            symbol,
            is_buy=is_buy,
            amount=abs(delta),
            label=label,
        )

        return [
            {
                "action": "BUY" if is_buy else "SELL",
                "delta_size": float(delta),
                "amount": abs(float(delta)),
                "label": label,
                "response": str(response),
            }
        ]
