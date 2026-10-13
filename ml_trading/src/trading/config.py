from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _bool(name: str, default: bool) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


def _float(name: str, default: float) -> float:
    value = _env(name)
    return default if value is None else float(value)


def _int(name: str, default: int) -> int:
    value = _env(name)
    return default if value is None else int(value)


@dataclass(frozen=True)
class Settings:
    market_type: str
    environment: str
    instrument: str
    currency: str
    interval: str
    horizon: int
    data_limit: int
    threshold_multiplier: float
    taker_fee_rate_fallback: float
    slippage_rate: float
    market_order_slippage: float
    allow_shorts: bool
    position_fraction: float
    max_position_fraction: float
    max_leverage_cap: float
    max_daily_loss_pct: float
    min_account_value_usdc: float
    dry_run: bool
    live_trading_confirm: str | None
    poll_seconds: int
    close_grace_seconds: int
    state_file: Path
    trade_log_file: Path
    api_key: str | None
    api_secret: str | None
    key_file: Path | None
    request_timeout: float

    @property
    def is_live(self) -> bool:
        return self.environment == "LIVE"

    def validate(self) -> None:
        if self.market_type != "GLOBAL_DERIVATIVES":
            raise ValueError("This build targets Coinbase Global Derivatives/perpetuals.")
        if self.environment not in {"LIVE"}:
            raise ValueError("ENVIRONMENT must be LIVE; keep DRY_RUN=true for the initial read-only test.")
        if not self.instrument:
            raise ValueError("INSTRUMENT must be set, e.g. BTC_USDC-PERPETUAL")
        if self.position_fraction <= 0 or self.position_fraction > 1:
            raise ValueError("POSITION_FRACTION must be > 0 and <= 1")
        if self.max_position_fraction <= 0 or self.max_position_fraction > 1:
            raise ValueError("MAX_POSITION_FRACTION must be > 0 and <= 1")
        if self.position_fraction > self.max_position_fraction:
            raise ValueError("POSITION_FRACTION cannot exceed MAX_POSITION_FRACTION")
        if self.max_leverage_cap <= 0:
            raise ValueError("MAX_LEVERAGE_CAP must be > 0")
        if self.max_daily_loss_pct < 0 or self.max_daily_loss_pct >= 1:
            raise ValueError("MAX_DAILY_LOSS_PCT must be >= 0 and < 1")
        if not self.dry_run and self.live_trading_confirm != "YES_I_UNDERSTAND":
            raise ValueError(
                "Live order placement is locked. Set LIVE_TRADING_CONFIRM=YES_I_UNDERSTAND "
                "only when you explicitly want the bot to trade."
            )
        if self.api_key is None and self.key_file is None:
            raise ValueError(
                "Set COINBASE_API_KEY + COINBASE_API_SECRET or COINBASE_KEY_FILE. "
                "Keep credentials outside the repository."
            )


_API_KEY = _env("COINBASE_API_KEY")
_API_SECRET = _env("COINBASE_API_SECRET")
_KEY_FILE = _env("COINBASE_KEY_FILE")

SETTINGS = Settings(
    market_type=(_env("MARKET_TYPE", "GLOBAL_DERIVATIVES") or "GLOBAL_DERIVATIVES").upper(),
    environment=(_env("ENVIRONMENT", "LIVE") or "LIVE").upper(),
    instrument=(_env("INSTRUMENT", "BTC_USDC-PERPETUAL") or "BTC_USDC-PERPETUAL").upper(),
    currency=(_env("CURRENCY", "USDC") or "USDC").upper(),
    interval=_env("INTERVAL", "1h") or "1h",
    horizon=_int("HORIZON", 37),
    data_limit=_int("DATA_LIMIT", 1000),
    threshold_multiplier=_float("THRESHOLD_MULTIPLIER", 1.0),
    taker_fee_rate_fallback=_float("TAKER_FEE_RATE_FALLBACK", 0.0005),
    slippage_rate=_float("SLIPPAGE_RATE", 0.0005),
    market_order_slippage=_float("MARKET_ORDER_SLIPPAGE", 0.003),
    allow_shorts=_bool("ALLOW_SHORTS", True),
    position_fraction=_float("POSITION_FRACTION", 0.10),
    max_position_fraction=_float("MAX_POSITION_FRACTION", 0.25),
    max_leverage_cap=_float("MAX_LEVERAGE_CAP", 3.0),
    max_daily_loss_pct=_float("MAX_DAILY_LOSS_PCT", 0.05),
    min_account_value_usdc=_float("MIN_ACCOUNT_VALUE_USDC", 10.0),
    dry_run=_bool("DRY_RUN", True),
    live_trading_confirm=_env("LIVE_TRADING_CONFIRM"),
    poll_seconds=_int("POLL_SECONDS", 15),
    close_grace_seconds=_int("CLOSE_GRACE_SECONDS", 8),
    state_file=PROJECT_ROOT / (_env("STATE_FILE", "data/state.json") or "data/state.json"),
    trade_log_file=PROJECT_ROOT / (_env("TRADE_LOG_FILE", "logs/trades.jsonl") or "logs/trades.jsonl"),
    api_key=_API_KEY,
    api_secret=_API_SECRET,
    key_file=(Path(_KEY_FILE) if _KEY_FILE else None),
    request_timeout=_float("REQUEST_TIMEOUT", 15.0),
)
