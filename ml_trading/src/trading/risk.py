from __future__ import annotations

from dataclasses import dataclass

from .account import AccountSnapshot, Position
from .config import Settings


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str
    target_notional: float


class RiskManager:
    def __init__(self, settings: Settings):
        self.settings = settings

    def check_account(self, account: AccountSnapshot) -> RiskDecision:
        if account.account_value < self.settings.min_account_value_usdc:
            return RiskDecision(
                False,
                f"Account value ${account.account_value:.2f} is below safety minimum",
                0.0,
            )
        return RiskDecision(True, "OK", 0.0)

    def target_notional(self, account: AccountSnapshot, requested_side: int) -> float:
        if requested_side == 0:
            return 0.0
        fraction = min(self.settings.position_fraction, self.settings.max_position_fraction)
        raw = max(0.0, account.account_value * fraction)
        margin_capacity = max(0.0, account.available_funds) * self.settings.max_leverage_cap
        if margin_capacity > 0:
            raw = min(raw, margin_capacity)
        return max(0.0, raw)

    def liquidation_distance_ok(self, position: Position, price: float) -> bool:
        if position.side == 0 or position.liquidation_price is None or price <= 0:
            return True
        distance = abs(price - position.liquidation_price) / price
        return distance >= 0.10
