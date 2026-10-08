
import time
import pandas as pd

from .config import SETTINGS
from .data import BinanceMarketData, BinanceFuturesMarketData
from .execution import BinanceREST
from .model import causal_predict
from .state import StateStore
from .strategy import make_signal

LR = 0.00325
MODEL_L2 = 0.425

PRODUCTION = {
    "FUTURES": {
        "DEMO": "https://demo-fapi.binance.com",
        "LIVE": "https://fapi.binance.com",
    },
    "SPOT": {
        "DEMO": "https://demo-api.binance.com",
        "LIVE": "https://api.binance.com",
    },
}

class TradingEngine:
    def __init__(self, settings=SETTINGS):
        settings.validate()
        self.s = settings
        self.base_url = PRODUCTION[settings.market_type][settings.environment]
        self.market = (
            BinanceFuturesMarketData(self.base_url, settings.symbol, settings.bar_size)
            if settings.market_type == "FUTURES"
            else BinanceMarketData(self.base_url, settings.symbol, settings.bar_size)
        )
        self.api = BinanceREST(
            settings.api_key,
            settings.api_secret,
            self.base_url,
            futures=settings.market_type == "FUTURES",
            dry_run=settings.dry_run,
        )
        self.state_store = StateStore(settings.state_file)
        self.state = self.state_store.load()

    def _actual_position(self):
        if self.s.market_type == "FUTURES":
            return self.api.futures_position(self.s.symbol)
        rules = self.api.symbol_rules(self.s.symbol)
        qty = self.api.spot_balance(rules["base_asset"])
        return {"qty": qty, "side": 1 if qty > 0 else 0}

    def run_once(self, force=False):
        df = self.market.klines(self.s.data_limit)
        bar = df.index[-1]

        if not force and self.state.get("last_processed_bar") == bar.isoformat():
            return {"status": "NO_NEW_BAR", "bar": str(bar)}

        pred, timestamp, price = causal_predict(
            df,
            horizon=self.s.horizon,
            lr=LR,
            model_l2=MODEL_L2,
        )

        previous_position = int(self.state.get("position", 0))
        previous_notional = float(self.state.get("position_notional", 0.0))

        signal = make_signal(
            pred=pred,
            timestamp=timestamp,
            price=price,
            previous_position=previous_position,
            previous_notional=previous_notional,
            equity=self.s.equity,
            risk_per_trade=self.s.risk_per_trade,
            leverage=self.s.leverage,
            threshold_multiplier=self.s.threshold_multiplier,
            taker_fee_rate=self.s.taker_fee_rate,
            slippage_rate=self.s.slippage_rate,
            allow_shorts=self.s.allow_shorts,
        )

        result = {
            "bar": str(bar),
            "prediction": signal.prediction,
            "price": signal.price,
            "action": signal.action,
            "desired_position": signal.position,
            "target_notional": signal.target_notional,
            "signed_delta_qty": signal.signed_delta_qty,
            "orders": [],
        }

        # Reconcile against the exchange, not our local assumption.
        actual = self._actual_position()
        actual_qty = float(actual["qty"])
        if self.s.market_type == "FUTURES":
            actual_position = 1 if actual_qty > 0 else (-1 if actual_qty < 0 else 0)
        else:
            actual_position = 1 if actual_qty > 0 else 0

        target_qty_abs = abs(signal.target_notional / signal.price) if signal.position != 0 else 0.0

        if signal.position != actual_position or (signal.position != 0 and abs(actual_qty) < target_qty_abs * 0.999):
            if self.s.market_type == "FUTURES":
                result["orders"] = self.api.execute_futures_target(
                    self.s.symbol, signal.position, target_qty_abs
                )
            else:
                result["orders"] = self.api.execute_spot_target(
                    self.s.symbol, signal.position, target_qty_abs
                )

        # Re-read actual position after execution.
        final = self._actual_position()
        final_qty = float(final["qty"])
        if self.s.market_type == "FUTURES":
            final_position = 1 if final_qty > 0 else (-1 if final_qty < 0 else 0)
        else:
            final_position = 1 if final_qty > 0 else 0

        self.state["position"] = final_position
        self.state["position_notional"] = abs(final_qty * signal.price)
        self.state["last_processed_bar"] = bar.isoformat()
        self.state_store.save(self.state)

        result["actual_position_after"] = final_position
        result["actual_qty_after"] = final_qty
        return result

    def loop(self):
        print(f"Starting {self.s.environment} {self.s.market_type} bot for {self.s.symbol} {self.s.bar_size}")
        print("LIVE execution is locked unless LIVE_TRADING_CONFIRM=YES_I_UNDERSTAND.")
        while True:
            try:
                result = self.run_once()
                print(pd.Series(result).to_string())
                self._sleep_to_next_bar()
            except KeyboardInterrupt:
                print("Stopped.")
                return
            except Exception as exc:
                print(f"ERROR: {exc}")
                time.sleep(30)

    def _sleep_to_next_bar(self):
        from .data import BAR_SECONDS
        sec = BAR_SECONDS[self.s.bar_size]
        now = time.time()
        next_boundary = (int(now) // sec + 1) * sec + self.s.close_grace_seconds
        wait = max(1.0, next_boundary - now)
        print(f"Sleeping ~{wait:.0f}s.")
        time.sleep(wait)
