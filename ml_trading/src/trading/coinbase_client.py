from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from coinbase.deribit import DeribitRetailClient

from .account import AccountSnapshot, build_snapshot, result_payload, as_dict
from .config import Settings
from .market_data import interval_to_ms, normalize_chart_data


class CoinbaseBroker:
    """Coinbase Global Derivatives adapter.

    Global Derivatives on Coinbase Advanced Trade use Coinbase's
    Deribit-powered gateway. This class keeps all exchange-specific
    details out of the strategy/model layers.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.key_file:
            key_path = Path(settings.key_file)
            if not key_path.exists():
                raise FileNotFoundError(f"Coinbase key file not found: {key_path}")
            self.client = DeribitRetailClient(key_file=str(key_path))
        else:
            self.client = DeribitRetailClient(
                api_key=settings.api_key,
                api_secret=settings.api_secret,
            )

    @staticmethod
    def _payload(value: Any) -> Any:
        return result_payload(value)

    def account_snapshot(self) -> AccountSnapshot:
        summary = self.client.private_get_account_summary(currency=self.settings.currency)
        positions = self.client.private_get_positions(currency=self.settings.currency)
        orders = self.client.private_get_open_orders(instrument_name=self.settings.instrument)
        return build_snapshot(
            account_id=self.settings.instrument,
            summary_raw=summary,
            positions_raw=positions,
            orders_raw=orders,
        )

    def candles(self, instrument: str, interval: str, limit: int):
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - int(limit * interval_to_ms(interval) * 1.2)
        response = self.client.call(
            "public/get_tradingview_chart_data",
            {
                "instrument_name": instrument,
                "start_timestamp": start_ms,
                "end_timestamp": end_ms,
                "resolution": _resolution(interval),
            },
        )
        raw = self._payload(response)
        if isinstance(raw, dict) and "result" in raw:
            raw = raw["result"]
        return normalize_chart_data(raw, now_ms=end_ms)


    def mark_price(self, instrument: str) -> float:
        ticker = self.client.public_ticker(instrument_name=instrument)
        result = self._payload(ticker)
        data = as_dict(result)
        if "mark_price" in data:
            return float(data["mark_price"])
        if "last_price" in data:
            return float(data["last_price"])
        if isinstance(result, dict):
            for key in ("mark_price", "last_price", "close"):
                if key in result:
                    return float(result[key])
        raise ValueError(f"Could not extract mark price for {instrument}")

    def instrument_meta(self, instrument: str) -> dict[str, Any]:
        response = self.client.call("public/get_instrument", {"instrument_name": instrument})
        data = self._payload(response)
        if isinstance(data, dict) and "result" in data:
            data = data["result"]
        return as_dict(data)

    def amount_precision(self, instrument: str) -> int:
        meta = self.instrument_meta(instrument)
        if "amount_precision" in meta:
            return int(meta["amount_precision"])
        return 6

    def min_trade_amount(self, instrument: str) -> float:
        meta = self.instrument_meta(instrument)
        for key in ("min_trade_amount", "min_amount", "min_trade_size"):
            if key in meta:
                return float(meta[key])
        return 0.0

    def fee_rate(self) -> float:
        # The global derivatives gateway does not expose a stable typed
        # account-fee helper in all SDK versions, so use the configured
        # fallback until Coinbase provides a dedicated typed field.
        return self.settings.taker_fee_rate_fallback

    def open_market(self, instrument: str, is_buy: bool, amount: float, label: str):
        method = self.client.private_buy if is_buy else self.client.private_sell
        return method(
            instrument_name=instrument,
            amount=amount,
            type="market",
            label=label,
        )

    def close_position(self, instrument: str, label: str):
        return self.client.private_close_position(instrument_name=instrument, label=label)

    def order_state_by_label(self, label: str):
        return self.client.private_get_order_state_by_label(label=label)

    def format_account(self, snapshot: AccountSnapshot) -> str:
        rows = [
            f"Coinbase instrument: {self.settings.instrument}",
            f"Account value (USDC): ${snapshot.account_value:,.4f}",
            f"Available funds: ${snapshot.available_funds:,.4f}",
            f"Margin used: ${snapshot.total_margin_used:,.4f}",
        ]
        position = snapshot.position_for(self.settings.instrument)
        if position.side:
            rows.append(
                f"Position: size={position.size} side={position.side} "
                f"entry={position.entry_price} mark={position.mark_price} "
                f"liq={position.liquidation_price} lev={position.leverage} "
                f"uPnL=${position.unrealized_pnl:,.4f}"
            )
        else:
            rows.append("Position: FLAT")
        rows.append(f"Open orders on instrument: {len(snapshot.open_orders)}")
        return "\n".join(rows)


def _resolution(interval: str) -> str:
    mapping = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "2h": "120", "4h": "240", "1d": "1D"}
    if interval not in mapping:
        raise ValueError(f"Unsupported interval {interval}")
    return mapping[interval]
