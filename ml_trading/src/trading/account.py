from __future__ import annotations

import math
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
        return 1 if self.size > 0 else (-1 if self.size < 0 else 0)

    @property
    def notional(self) -> float:
        return abs(self.position_value) if self.position_value else abs(
            self.size * (self.mark_price or 0.0)
        )


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
        return Position(instrument, 0.0, None, None, None, None, 0.0, 0.0, 0.0)


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        result = value.to_dict()
        if isinstance(result, dict):
            return result
    if hasattr(value, "__dict__"):
        result = dict(value.__dict__)
        if result:
            return result
    raise ValueError(f"Expected an object/dict, got {type(value).__name__}")


def result_payload(value: Any) -> Any:
    if isinstance(value, dict) and "error" in value:
        raise ValueError("API response contains an error")
    if isinstance(value, dict) and "result" in value:
        return value["result"]
    if hasattr(value, "result"):
        return value.result
    return value


def _float(value: Any, default: float | None = None) -> float:
    if value is None or isinstance(value, bool):
        if default is not None:
            return default
        raise ValueError("Missing numeric value")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        if default is not None:
            return default
        raise ValueError(f"Invalid numeric value: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError("Numeric value must be finite")
    return number


def _required_number(data: dict[str, Any], keys: tuple[str, ...], field: str) -> float:
    for key in keys:
        if key in data:
            value = data[key]
            if isinstance(value, dict):
                if "value" in value:
                    value = value["value"]
                elif "amount" in value:
                    value = value["amount"]
                else:
                    raise ValueError(f"Invalid {field} object")
            return _float(value)
    raise ValueError(f"Missing required account field: {field}")


def _optional_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        if "value" in value:
            value = value["value"]
        elif "amount" in value:
            value = value["amount"]
        else:
            raise ValueError("Invalid optional numeric object")
    return _float(value)


def parse_position(raw: dict[str, Any]) -> Position:
    raw = as_dict(raw)

    instrument = raw.get("instrument_name", raw.get("instrument", raw.get("symbol")))
    if not isinstance(instrument, str) or not instrument.strip():
        raise ValueError("Position is missing instrument name")

    size_value = raw.get("size", raw.get("amount", raw.get("net_size")))
    if size_value is None:
        raise ValueError(f"Position {instrument} is missing size")
    size = _float(size_value)
    direction = str(raw.get("direction", "")).lower()
    if direction == "sell" and size > 0:
        size = -size
    elif direction == "buy" and size < 0:
        size = abs(size)

    position_value = _required_number(
        raw, ("position_notional", "position_value", "size_usd"), "position value"
    ) if any(k in raw for k in ("position_notional", "position_value", "size_usd")) else 0.0

    mark = raw.get("mark_price", raw.get("markPrice"))
    entry = raw.get("average_price", raw.get("entry_price", raw.get("entry_vwap")))
    liq = raw.get("estimated_liquidation_price", raw.get("liquidation_price"))
    lev = raw.get("leverage")
    upl = raw.get("floating_profit_loss", raw.get("unrealized_pnl", 0.0))
    margin = raw.get("initial_margin", raw.get("margin_used", raw.get("im_notional", 0.0)))

    return Position(
        instrument=instrument,
        size=size,
        entry_price=_optional_number(entry),
        mark_price=_optional_number(mark),
        liquidation_price=_optional_number(liq),
        leverage=_optional_number(lev),
        margin_used=_float(margin),
        position_value=position_value,
        unrealized_pnl=_float(upl),
    )


def _collection(value: Any, keys: tuple[str, ...], field: str) -> list[Any]:
    value = result_payload(value)
    if isinstance(value, dict):
        found = False
        for key in keys:
            if key in value:
                value = value[key]
                found = True
                break
        if not found:
            raise ValueError(f"Response is missing {field} collection")
    if not isinstance(value, list):
        raise ValueError(f"Expected {field} to be a list")
    return value


def build_snapshot(
    account_id: str, summary_raw: Any, positions_raw: Any, orders_raw: Any
) -> AccountSnapshot:
    summary = as_dict(result_payload(summary_raw))

    equity = _required_number(
        summary, ("equity", "balance", "margin_balance"), "equity"
    )
    available = _required_number(
        summary,
        ("available_funds", "available_withdrawal", "withdrawable"),
        "available funds",
    )
    margin = _required_number(
        summary, ("initial_margin", "total_margin_used"), "total margin"
    )

    positions_payload = _collection(
        positions_raw, ("positions", "data"), "positions"
    )
    orders_payload = _collection(orders_raw, ("orders", "data"), "orders")

    positions = tuple(parse_position(item) for item in positions_payload)
    if any(not isinstance(item, dict) for item in orders_payload):
        raise ValueError("Open orders collection contains a malformed entry")

    return AccountSnapshot(
        account_id=account_id,
        account_value=equity,
        available_funds=available,
        total_margin_used=margin,
        positions=positions,
        open_orders=tuple(orders_payload),
    )
