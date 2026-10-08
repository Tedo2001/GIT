
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

@dataclass(frozen=True)
class Settings:
    market_type: str = os.getenv("MARKET_TYPE", "FUTURES").upper()
    environment: str = os.getenv("ENVIRONMENT", "DEMO").upper()
    api_key: str = os.getenv("BINANCE_API_KEY", "")
    api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    live_confirm: str = os.getenv("LIVE_TRADING_CONFIRM", "")
    symbol: str = os.getenv("SYMBOL", "BTCUSDT").upper()
    bar_size: str = os.getenv("BAR_SIZE", "1h")
    horizon: int = int(os.getenv("HORIZON", "37"))
    threshold_multiplier: float = float(os.getenv("THRESHOLD_MULTIPLIER", "1.0"))
    allow_shorts: bool = _bool("ALLOW_SHORTS", True)
    equity: float = float(os.getenv("EQUITY", "10000"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "0.10"))
    leverage: float = float(os.getenv("LEVERAGE", "1.0"))
    taker_fee_rate: float = float(os.getenv("TAKER_FEE_RATE", "0.0010"))
    slippage_rate: float = float(os.getenv("SLIPPAGE_RATE", "0.0005"))
    data_limit: int = int(os.getenv("DATA_LIMIT", "1000"))
    close_grace_seconds: int = int(os.getenv("CLOSE_GRACE_SECONDS", "5"))
    state_file: Path = Path(os.getenv("STATE_FILE", "data/state.json"))
    dry_run: bool = _bool("DRY_RUN", False)

    def validate(self):
        if self.market_type not in {"FUTURES", "SPOT"}:
            raise ValueError("MARKET_TYPE must be FUTURES or SPOT")
        if self.environment not in {"DEMO", "LIVE"}:
            raise ValueError("ENVIRONMENT must be DEMO or LIVE")
        if not self.api_key or not self.api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET are required.")
        if self.market_type == "SPOT" and self.allow_shorts:
            raise ValueError("Spot mode does not support this strategy's SHORT state. Set ALLOW_SHORTS=false.")
        if self.data_limit < 300 or self.data_limit > 1000:
            raise ValueError("DATA_LIMIT must be between 300 and 1000.")
        if self.equity <= 0 or self.risk_per_trade < 0 or self.leverage <= 0:
            raise ValueError("Invalid equity/risk/leverage configuration.")
        if self.environment == "LIVE" and self.live_confirm != "YES_I_UNDERSTAND":
            raise ValueError(
                "LIVE trading is locked. Set LIVE_TRADING_CONFIRM=YES_I_UNDERSTAND explicitly."
            )

SETTINGS = Settings()
