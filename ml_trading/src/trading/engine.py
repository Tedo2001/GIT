from __future__ import annotations

import time
from dataclasses import asdict

from .coinbase_client import CoinbaseBroker
from .config import SETTINGS
from .logging_utils import append_jsonl
from .model import causal_predict
from .reconciliation import Reconciler
from .risk import RiskManager
from .state import StateStore
from .strategy import make_signal


class TradingEngine:
    def __init__(self):
        SETTINGS.validate()
        self.settings = SETTINGS
        self.broker = CoinbaseBroker(SETTINGS)
        self.risk = RiskManager(SETTINGS)
        self.reconciler = Reconciler(self.broker, SETTINGS)
        self.state_store = StateStore(SETTINGS.state_file)
        self.state = self.state_store.load()

    def _daily_safety(self, account_value: float) -> None:
        today = self.state_store.utc_date()
        if self.state.daily_date != today or self.state.daily_start_equity is None:
            self.state.daily_date = today
            self.state.daily_start_equity = account_value
            self.state.halted = False
            self.state.halt_reason = None
            self.state_store.save(self.state)

        start = self.state.daily_start_equity or account_value
        if self.settings.max_daily_loss_pct > 0 and account_value < start * (1 - self.settings.max_daily_loss_pct):
            self.state.halted = True
            self.state.halt_reason = (
                f"Daily loss limit hit: start={start:.4f}, current={account_value:.4f}, "
                f"limit={self.settings.max_daily_loss_pct:.2%}"
            )
            self.state_store.save(self.state)
            raise RuntimeError(self.state.halt_reason)

        if self.state.halted:
            raise RuntimeError(self.state.halt_reason or "Bot is halted")

    def run_once(self, force: bool = False) -> dict:
        account = self.broker.account_snapshot()
        print(self.broker.format_account(account))
        self._daily_safety(account.account_value)

        candles = self.broker.candles(self.settings.instrument, self.settings.interval, self.settings.data_limit)
        prediction, bar_timestamp, price = causal_predict(candles, horizon=self.settings.horizon)
        bar_key = str(bar_timestamp)

        if not force and self.state.last_processed_bar == bar_key:
            print(f"Skipping already processed bar: {bar_key}")
            return {"status": "skipped", "bar": bar_key}

        current_position = account.position_for(self.settings.instrument)
        fee_rate = self.broker.fee_rate()

        preview_side = (
            1
            if prediction > self.settings.threshold_multiplier * (fee_rate + self.settings.slippage_rate)
            else (
                -1
                if self.settings.allow_shorts
                and prediction < -self.settings.threshold_multiplier * (fee_rate + self.settings.slippage_rate)
                else 0
            )
        )
        target_notional = self.risk.target_notional(account, preview_side)

        signal = make_signal(
            pred=prediction,
            timestamp=bar_timestamp,
            price=price,
            previous_position=current_position.side,
            target_notional=target_notional,
            threshold_multiplier=self.settings.threshold_multiplier,
            fee_rate=fee_rate,
            slippage_rate=self.settings.slippage_rate,
            allow_shorts=self.settings.allow_shorts,
        )

        print(
            f"Bar={bar_key} price={price:.6f} prediction={prediction:.8f} "
            f"fee={fee_rate:.6f} signal={signal.action} desired={signal.desired_position} "
            f"target_notional=${signal.target_notional:,.4f}"
        )

        plan = {
            "bar": bar_key,
            "price": price,
            "prediction": prediction,
            "fee_rate": fee_rate,
            "signal": asdict(signal),
            "dry_run": self.settings.dry_run,
            "account_value": account.account_value,
        }
        self.state.last_signal = plan

        if self.settings.dry_run:
            self.state.last_processed_bar = bar_key
            self.state_store.save(self.state)
            append_jsonl(self.settings.trade_log_file, {"event": "dry_run", **plan})
            print("DRY_RUN=True -> no order sent.")
            return {"status": "dry_run", **plan}

        safety = self.risk.check_account(account)
        if not safety.allowed:
            raise RuntimeError(safety.reason)
        if not self.risk.liquidation_distance_ok(current_position, price):
            raise RuntimeError("Existing position is too close to liquidation price")

        actions = self.reconciler.reconcile(
            self.settings.instrument,
            signal.desired_position,
            signal.target_notional,
            price,
        )

        # Do not automatically retry if an order call had an uncertain
        # network outcome. The label can be checked explicitly on the exchange.
        after = self.broker.account_snapshot()
        self.state.last_processed_bar = bar_key
        self.state.last_order = {
            "actions": actions,
            "after_position": asdict(after.position_for(self.settings.instrument)),
        }
        self.state_store.save(self.state)
        append_jsonl(self.settings.trade_log_file, {"event": "execution", **plan, "actions": actions})
        return {"status": "executed", **plan, "actions": actions}

    def run_forever(self) -> None:
        print(
            f"Starting Coinbase bot: instrument={self.settings.instrument}, "
            f"interval={self.settings.interval}, dry_run={self.settings.dry_run}"
        )
        while True:
            try:
                self.run_once(force=False)
            except Exception as exc:
                print(f"ERROR: {type(exc).__name__}: {exc}")
            time.sleep(self.settings.poll_seconds)
