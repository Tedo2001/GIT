from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Position:
    instrument: str
    size: float
    entry_price: float | None
    mark_price: float | None
    liquidation_price: float | None
    leverage: float | None
    margin_used: float
    position_value: float
    unrealized_pnl: float

    @property
    def side(self) -> int:
        if self.size > 0:
            return 1
        if self.size < 0:
            return -1
        return 0

    @property
    def notional(self) -> float:
        return abs(self.position_value) if self.position_value else abs(self.size * (self.mark_price or 0.0))


@dataclass(frozen=True)
class AccountSnapshot:
    account_id: str
    account_value: float
    available_funds: float
    total_margin_used: float
    positions: tuple[Position, ...]
    open_orders: tuple[dict[str, Any], ...]

    def position_for(self, instrument: str) -> Position:
        for position in self.positions:
            if position.instrument == instrument:
                return position
        return Position(
            instrument=instrument,
            size=0.0,
            entry_price=None,
            mark_price=None,
            liquidation_price=None,
            leverage=None,
            margin_used=0.0,
            position_value=0.0,
            unrealized_pnl=0.0,
        )


def as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        try:
            result = value.to_dict()
            if isinstance(result, dict):
                return result
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


def result_payload(value: Any) -> Any:
    if hasattr(value, "result"):
        return value.result
    return value


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_position(raw: dict[str, Any]) -> Position:
    raw = as_dict(raw)
    size_raw = raw.get("size", raw.get("amount", raw.get("net_size", 0.0)))
    size = _float(size_raw)
    direction = str(raw.get("direction", "")).lower()
    if direction == "sell" and size > 0:
        size = -size
    if direction == "buy" and size < 0:
        size = abs(size)

    position_value = _float(
        raw.get("position_notional", raw.get("position_value", raw.get("size_usd", 0.0)))
    )
    mark = raw.get("mark_price", raw.get("markPrice"))
    entry = raw.get("average_price", raw.get("entry_price", raw.get("entry_vwap")))
    liq = raw.get("estimated_liquidation_price", raw.get("liquidation_price"))
    lev = raw.get("leverage")
    upl = raw.get("floating_profit_loss", raw.get("unrealized_pnl", 0.0))
    margin = raw.get("initial_margin", raw.get("margin_used", raw.get("im_notional", 0.0)))

    def unwrap(v: Any) -> Any:
        if isinstance(v, dict):
            for k in ("value", "amount"):
                if k in v:
                    return v[k]
        return v

    return Position(
        instrument=str(raw.get("instrument_name", raw.get("instrument", raw.get("symbol", "")))),
        size=size,
        entry_price=None if unwrap(entry) in (None, "") else _float(unwrap(entry)),
        mark_price=None if unwrap(mark) in (None, "") else _float(unwrap(mark)),
        liquidation_price=None if unwrap(liq) in (None, "") else _float(unwrap(liq)),
        leverage=None if unwrap(lev) in (None, "") else _float(unwrap(lev)),
        margin_used=_float(unwrap(margin)),
        position_value=position_value,
        unrealized_pnl=_float(unwrap(upl)),
    )


def build_snapshot(account_id: str, summary_raw: Any, positions_raw: Any, orders_raw: Any) -> AccountSnapshot:
    summary = as_dict(result_payload(summary_raw))
    positions_payload = result_payload(positions_raw)
    orders_payload = result_payload(orders_raw)

    if isinstance(positions_payload, dict):
        positions_payload = positions_payload.get("positions", positions_payload.get("data", []))
    if isinstance(orders_payload, dict):
        orders_payload = orders_payload.get("orders", orders_payload.get("data", []))
    if not isinstance(positions_payload, list):
        positions_payload = []
    if not isinstance(orders_payload, list):
        orders_payload = []

    equity = summary.get("equity", summary.get("balance", summary.get("margin_balance", 0.0)))
    available = summary.get(
        "available_funds",
        summary.get("available_withdrawal", summary.get("withdrawable", 0.0)),
    )
    margin = summary.get("initial_margin", summary.get("total_margin_used", 0.0))
    positions = tuple(parse_position(item) for item in positions_payload)

    return AccountSnapshot(
        account_id=account_id,
        account_value=_float(equity),
        available_funds=_float(available),
        total_margin_used=_float(margin),
        positions=positions,
        open_orders=tuple(item for item in orders_payload if isinstance(item, dict)),
    )
