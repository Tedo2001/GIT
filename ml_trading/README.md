
# ML Binance Trading Bot — based on `appl.ipynb`

This project converts the supplied `appl.ipynb` strategy into a small execution engine.

## What is preserved from the notebook

- `BTCUSDT` / configurable symbol
- 1h / configurable bar size
- return windows: 125, 150, 175, 200, 225, 250
- future-return horizon: 37 by default
- causal online linear regression
- `LR=0.00325`
- `MODEL_L2=0.425`
- cost threshold logic
- LONG / SHORT / FLAT signal logic
- target notional = `EQUITY * LEVERAGE * RISK_PER_TRADE`

Important: the notebook's `ASSUME_SIGNAL_FILLED=True` behavior is NOT used by the live engine.
The exchange is the source of truth for the actual position.

## Supported modes

### Futures
- Binance USDT-M Futures
- one-way position mode
- LONG / SHORT / FLAT
- MARKET orders
- reduce-only closes

### Spot
- Binance Spot
- LONG / FLAT only
- the project refuses to start Spot mode if `ALLOW_SHORTS=true`

## Safety

The default configuration is:

```text
ENVIRONMENT=DEMO
```

For LIVE trading you must explicitly set:

```text
ENVIRONMENT=LIVE
LIVE_TRADING_CONFIRM=YES_I_UNDERSTAND
```

Never put API secrets into Git.

For the first run, also use:

```text
DRY_RUN=true
```

The code will then calculate and log the intended orders without sending them.

## Install

Python 3.11+ is recommended.

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Then:

```bash
pip install -r requirements.txt
```

Copy:

```text
.env.example -> .env
```

and fill in the API key/secret from the appropriate Binance Demo environment.

## First test

Set:

```text
MARKET_TYPE=FUTURES
ENVIRONMENT=DEMO
DRY_RUN=true
```

Then:

```bash
python run_once.py
```

You should get a prediction, signal, actual exchange position, and intended order information.

When the behavior is correct:

```text
DRY_RUN=false
ENVIRONMENT=DEMO
```

and run:

```bash
python run_once.py
```

This allows the bot to place orders in the Binance Demo environment.

## 24/7 loop

```bash
python run_bot.py
```

Do not run two copies against the same account/symbol at the same time.

## Going LIVE

Only after extensive Demo testing:

```text
ENVIRONMENT=LIVE
LIVE_TRADING_CONFIRM=YES_I_UNDERSTAND
DRY_RUN=false
```

Use a dedicated API key with only the permissions required for trading. Never enable withdrawal permissions for a trading bot.

## Risk warning

`RISK_PER_TRADE=0.10` in the original notebook is a target-notional rule. It is NOT a 10% stop-loss risk model. A 10% target notional and a 10% capital-at-risk stop-loss are very different things.

Before live deployment, add/verify:
- maximum daily loss
- maximum position notional
- maximum order frequency
- stop-loss / liquidation protection
- network/API failure handling
- reconciliation after restarts
- persistent order/fill logging
- monitoring/alerts

The current project deliberately does not invent a stop-loss model that was not present in your notebook.

## Notebook

`notebooks/appl/appl_reworked.ipynb` demonstrates:
1. loading closed candles
2. running the same causal ML prediction
3. generating a signal
4. showing the intended execution

The notebook does not contain an automatic infinite live loop.

## Binance API

This project uses Binance's documented REST endpoints directly via `requests`, avoiding dependence on a third-party trading SDK.
