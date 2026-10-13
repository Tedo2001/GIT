from __future__ import annotations

import math
import uuid
from typing import Any

from .coinbase_client import CoinbaseBroker
from .config import Settings


def floor_step(value: float, decimals: int) -> float:
    factor = 10**decimals
    return math.floor(abs(value) * factor + 1e-12) / factor


class Reconciler:
    def __init__(self, broker: CoinbaseBroker, settings: Settings):
        self.broker = broker
        self.settings = settings

    def _ensure_no_open_orders(self, symbol: str):
        account = self.broker.account_snapshot()
        if account.open_orders:
            raise RuntimeError(
                f"Refusing to trade {symbol}: {len(account.open_orders)} open order(s) exist. "
                "Review/cancel them before the bot trades again."
            )
        return account

    def reconcile(self, symbol: str, target_side: int, target_notional: float, mark_price: float) -> list[dict[str, Any]]:
        account = self._ensure_no_open_orders(symbol)
        current = account.position_for(symbol)

        if target_side == 0:
            if current.side == 0:
                return []
            label = f"ml-close-{uuid.uuid4().hex[:20]}"
            response = self.broker.close_position(symbol, label)
            return [{"action": "CLOSE", "label": label, "response": str(response)}]

        target_abs_size = target_notional / mark_price
        decimals = self.broker.amount_precision(symbol)
        min_amount = self.broker.min_trade_amount(symbol)
        target_abs_size = floor_step(target_abs_size, decimals)
        if target_abs_size < min_amount:
            target_abs_size = 0.0

        current_size = current.size

        # If direction is wrong, close first; a fresh order is used only after
        # the exchange has accepted the close request. The next cycle verifies
        # the actual position before opening the new direction.
        if current.side != 0 and current.side != target_side:
            label = f"ml-reverse-close-{uuid.uuid4().hex[:16]}"
            response = self.broker.close_position(symbol, label)
            return [{"action": "REVERSE_CLOSE", "label": label, "response": str(response)}]

        desired_size = target_abs_size * target_side
        delta = desired_size - current_size
        delta = floor_step(delta, decimals)

        if abs(delta) < min_amount:
            return []

        is_buy = delta > 0
        label = f"ml-open-{uuid.uuid4().hex[:20]}"
        response = self.broker.open_market(symbol, is_buy=is_buy, amount=abs(delta), label=label)
        return [
            {
                "action": "BUY" if is_buy else "SELL",
                "delta_size": float(delta),
                "amount": abs(float(delta)),
                "label": label,
                "response": str(response),
            }
        ]
