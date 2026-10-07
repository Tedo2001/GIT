import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Account
EQUITY = 10_000
RISK_PER_TRADE = 0.10
LEVERAGE = 1.0

# Costs/Fees
TAKER_FEE_RATE = 0.0010
SLIPPAGE_RATE = 0.0005

# Data
BASE_URL = "https://data-api.binance.vision"
SYMBOL = "BTCUSDT"
BAR_SIZE = "1h"

# Strategy Parameters
HORIZON = 37
THRESHOLD_MULTIPLIER = 1.0          # multiply round-trip cost
ALLOW_SHORTS = True

# Model Parameters
LR = 0.00325
MODEL_L2 = 0.425

# For fixed-length Binance intervals used here.
# Add other intervals if you use them.
BAR_SECONDS = {
    "1m": 60,
    "3m": 3 * 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 60 * 60,
    "2h": 2 * 60 * 60,
    "4h": 4 * 60 * 60,
    "6h": 6 * 60 * 60,
    "8h": 8 * 60 * 60,
    "12h": 12 * 60 * 60,
    "1d": 24 * 60 * 60,
}

if BAR_SIZE not in BAR_SECONDS:
    raise ValueError(
        f"Unsupported BAR_SIZE={BAR_SIZE!r}. "
        f"Supported values: {list(BAR_SECONDS)}"
    )

BAR_SECONDS_VALUE = BAR_SECONDS[BAR_SIZE]

# Wait a few seconds after the expected close before requesting data.
CLOSE_GRACE_SECONDS = 3

# Keep the last handled candle timestamp across kernel restarts
# if this file remains in the notebook's working directory.
LAST_PROCESSED_FILE = Path("last_processed_bar.txt")

# Existing position state. This survives cell reruns, but not kernel restarts.
if "_wf_previous_position" not in globals():
    _wf_previous_position = 0
    _wf_previous_size_usd = 0.0

# Paper/simulation convenience only. In live trading, reconcile position state
# from confirmed fills rather than assuming a generated signal was filled.
ASSUME_SIGNAL_FILLED = True