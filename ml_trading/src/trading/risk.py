from __future__ import annotations

from dataclasses import dataclass
import math

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
        if not math.isfinite(account.account_value) or account.account_value < 0:
            return RiskDecision(False, "Account value is invalid", 0.0)
        if not math.isfinite(account.available_funds) or account.available_funds < 0:
            return RiskDecision(False, "Available funds are invalid", 0.0)
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
        if requested_side not in (-1, 1):
            return 0.0
        if (
            not math.isfinite(account.account_value)
            or account.account_value <= 0
            or not math.isfinite(account.available_funds)
            or account.available_funds <= 0
            or not math.isfinite(self.settings.max_leverage_cap)
            or self.settings.max_leverage_cap <= 0
        ):
            return 0.0
        fraction = min(self.settings.position_fraction, self.settings.max_position_fraction)
        raw = max(0.0, account.account_value * fraction)
        margin_capacity = account.available_funds * self.settings.max_leverage_cap
        return max(0.0, min(raw, margin_capacity))

    def liquidation_distance_ok(self, position: Position, price: float) -> bool:
        if position.side == 0:
            return True
        liq = position.liquidation_price
        if (
            liq is None
            or not math.isfinite(price)
            or not math.isfinite(liq)
            or price <= 0
            or liq <= 0
        ):
            return False
        distance = abs(price - liq) / price
        return distance >= 0.10
