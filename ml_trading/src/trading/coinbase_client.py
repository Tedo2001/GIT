
from __future__ import annotations

import math
import time
from typing import Any

from coinbase.deribit.rest_client import DeribitRetailClient
from coinbase.deribit.ws_client import DeribitRetailWSClient

from .account import AccountSnapshot, as_dict, build_snapshot, result_payload
from .config import Settings
from .market_data import _resolution, normalize_chart_data


class CoinbaseBroker:
    """Broker adapter for Coinbase Global Derivatives."""

    def __init__(self, settings: Settings):
        self.settings = settings

        kwargs: dict[str, Any] = {
            "environment": "production",
        }

        if settings.key_file is not None:
            kwargs["key_file"] = str(settings.key_file)
        elif settings.api_key and settings.api_secret:
            kwargs["api_key"] = settings.api_key
            kwargs["api_secret"] = settings.api_secret
        else:
            raise ValueError(
                "Missing credentials. Set COINBASE_KEY_FILE or "
                "COINBASE_API_KEY and COINBASE_API_SECRET."
            )

        self.client = DeribitRetailClient(**kwargs)
        self.market_data_client = DeribitRetailWSClient(**kwargs)

    @staticmethod
    def _payload(response: Any) -> Any:
        return result_payload(response)

    @staticmethod
    def _number(value: Any, field: str) -> float:
        if isinstance(value, dict):
            if "value" in value:
                value = value["value"]
            elif "amount" in value:
                value = value["amount"]

        if isinstance(value, bool) or value is None:
            raise ValueError(f"Missing or invalid numeric field: {field}")

        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Invalid numeric field: {field}") from exc

        if not math.isfinite(number):
            raise ValueError(f"Non-finite numeric field: {field}")

        return number

    def account_snapshot(self) -> AccountSnapshot:
        currency = self.settings.currency

        summary = self.client.private_get_account_summary(
            currency=currency,
            extended=True,
        )
        positions = self.client.private_get_positions(
            currency=currency,
            kind="future",
        )
        orders = self.client.private_get_open_orders(
            kind="future",
        )

        return build_snapshot(
            account_id=currency,
            summary_raw=summary,
            positions_raw=positions,
            orders_raw=orders,
        )

    def format_account(self, account: AccountSnapshot) -> str:
        position = account.position_for(self.settings.instrument)

        return (
            f"Account currency={self.settings.currency} "
            f"equity={account.account_value:.4f} "
            f"available={account.available_funds:.4f} "
            f"margin_used={account.total_margin_used:.4f} "
            f"instrument={position.instrument} "
            f"position_size={position.size:.8f} "
            f"position_side={position.side}"
        )

    def candles(
        self,
        instrument: str,
        interval: str,
        limit: int,
    ):
        if limit < 2:
            raise ValueError("Candle limit must be at least 2")

        resolution = _resolution(interval)
        now_ms = int(time.time() * 1000)

        # Request enough history for the desired candle count, plus a buffer.
        interval_ms = {
            "1m": 60_000,
            "5m": 300_000,
            "15m": 900_000,
            "30m": 1_800_000,
            "1h": 3_600_000,
            "2h": 7_200_000,
            "4h": 14_400_000,
            "1d": 86_400_000,
        }.get(interval)

        if interval_ms is None:
            raise ValueError(f"Unsupported candle interval: {interval}")

        end_ms = now_ms
        start_ms = end_ms - interval_ms * (limit + 2)

        # Open the WebSocket before requesting chart data.
        self.market_data_client.open()
        try:
            response = (
                self.market_data_client.public_get_tradingview_chart_data(
                    instrument_name=instrument,
                    start_timestamp=start_ms,
                    end_timestamp=end_ms,
                    resolution=resolution,
                )
            )
        finally:
            self.market_data_client.close()

        data = as_dict(self._payload(response))

        # Fail closed if the response differs from the expected schema.
        required = ("ticks", "open", "high", "low", "close")
        missing = [key for key in required if key not in data]

        if missing:
            raise ValueError(
                "TradingView chart response is missing fields: "
                + ", ".join(missing)
            )

        frame = normalize_chart_data(data, now_ms=now_ms)
        return frame.tail(limit).copy()

    def mark_price(self, instrument: str) -> float:
        response = self.client.public_ticker(
            instrument_name=instrument,
        )
        data = as_dict(self._payload(response))

        for key in ("mark_price", "last_price"):
            if key in data:
                value = self._number(data[key], key)
                if value > 0:
                    return value

        raise ValueError(
            f"Ticker for {instrument} has no valid mark or last price"
        )

    def instrument_meta(self, instrument: str) -> dict[str, Any]:
        response = self.client.public_get_instrument(
            instrument_name=instrument,
        )
        data = as_dict(self._payload(response))

        if not data:
            raise ValueError(
                f"Empty instrument metadata response for {instrument}"
            )

        return data

    def amount_precision(self, instrument: str) -> int:
        meta = self.instrument_meta(instrument)

        # Do not infer quantity increments from minimum trade size.
        if "amount_precision" not in meta:
            raise ValueError(
                f"Cannot safely determine amount precision for {instrument}; "
                "instrument metadata has no amount_precision. "
                "Verify the API's quantity increment before trading."
            )

        precision = int(meta["amount_precision"])
        if precision < 0:
            raise ValueError(
                f"Invalid amount_precision in metadata for {instrument}"
            )

        return precision

    def min_trade_amount(self, instrument: str) -> float:
        meta = self.instrument_meta(instrument)

        for key in ("min_trade_amount", "min_amount", "min_trade_size"):
            if key in meta:
                amount = self._number(meta[key], key)
                if amount <= 0:
                    raise ValueError(
                        f"Invalid {key} in instrument metadata for {instrument}"
                    )
                return amount

        raise ValueError(
            f"Missing minimum trade amount in instrument metadata for {instrument}"
        )

    def fee_rate(self) -> float:
        instrument = self.settings.instrument

        try:
            meta = self.instrument_meta(instrument)
            value = meta.get("taker_commission")
            if value is not None:
                fee = self._number(value, "taker_commission")
                if fee >= 0:
                    return fee
        except (ValueError, TypeError, KeyError):
            pass

        fallback = float(self.settings.taker_fee_rate_fallback)
        if not math.isfinite(fallback) or fallback < 0:
            raise ValueError("Invalid configured taker fee fallback")

        return fallback

    def open_market(
        self,
        instrument: str,
        is_buy: bool,
        amount: float,
        label: str | None = None,
    ) -> dict[str, Any]:
        if self.settings.dry_run:
            raise RuntimeError(
                "Order submission blocked: DRY_RUN=True. "
                "This method must not be called in dry-run mode."
            )

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Order amount must be finite and positive")

        # No live submission until amount-versus-contract units are verified.
        raise RuntimeError(
            "Live order submission is deliberately disabled in this "
            "recovery build. Verify the instrument's amount/contracts units "
            "and private API authentication before implementing execution."
        )

    def close_position(self, instrument: str) -> dict[str, Any]:
        if self.settings.dry_run:
            raise RuntimeError(
                "Position closing blocked: DRY_RUN=True."
            )

        raise RuntimeError(
            "Live position closing is deliberately disabled in this "
            "recovery build until authentication and execution semantics "
            "are verified."
        )
