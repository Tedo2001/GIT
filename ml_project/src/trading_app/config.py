"""Project configuration constants.

Import these values in other modules, for example:
    from config import HORIZON, SYMBOL, ONE_WAY_COST
"""

# Account
INITIAL_BALANCE = 10_000
RISK_PER_TRADE = 0.10
LEVERAGE = 1.0

# Costs / fees
TAKER_FEE_RATE = 0.0010
SLIPPAGE_RATE = 0.0005
ONE_WAY_COST = TAKER_FEE_RATE + SLIPPAGE_RATE

# Data
BASE_URL = "https://data-api.binance.vision"
SYMBOL = "BTCUSDT"
BAR_SIZE = "1h"

# Data window (UTC)
START = "2015-07-01 00:00:00"
END = "2026-08-01 00:00:00"

# Strategy parameters
HORIZON = 37
THRESHOLD_MULTIPLIER = 1.0  # Multiplier applied to ONE_WAY_COST in the notebook
ALLOW_SHORTS = True

# Model parameters
LR = 0.00325
MODEL_L2 = 0.425
