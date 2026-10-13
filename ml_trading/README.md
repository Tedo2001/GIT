# Coinbase ML Trading Bot — APPL strategy

This rebuild keeps the same causal ML strategy and moves only the broker/data/execution layer to **Coinbase Global Derivatives**.

## Why Global Derivatives?

This is the closest Coinbase equivalent to the Hyperliquid perpetual setup. As of October 1, 2026, Coinbase says Global Derivatives on Advanced Trade run through a Deribit-powered gateway. The official Coinbase Python SDK exposes `DeribitRetailClient` for this path.

## Important safety model

The exchange is the source of truth for:
- account equity
- available funds
- current position
- leverage / liquidation fields returned by the account state
- open orders

There is **no `EQUITY`, `LEVERAGE`, or account size hardcoded in `.env`**.

`POSITION_FRACTION`, `MAX_POSITION_FRACTION`, and `MAX_LEVERAGE_CAP` are risk policy settings, not descriptions of the account. The bot calculates the actual target size from live account state.

## Credentials

Preferred:
1. Create a Coinbase CDP API key.
2. Download the JSON key file.
3. Store that JSON **outside this repository**.
4. Set `COINBASE_KEY_FILE` in `.env` to the file path, or set the same environment variable in PyCharm.

The official Coinbase SDK also supports `COINBASE_API_KEY` + `COINBASE_API_SECRET`.

Never commit the JSON key file or secret.

## First run

Create a PyCharm virtual environment and install:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env`.

Keep:

```text
DRY_RUN=true
```

Then run:

```text
run_once.py
```

The bot should:
1. authenticate with Coinbase,
2. read account summary,
3. read current positions/open orders,
4. fetch closed 1h candles,
5. run the causal ML model,
6. print LONG/SHORT/FLAT,
7. place no order because `DRY_RUN=true`.

## Before enabling live orders

Run with a **view-only** API key first if possible. Confirm that account, positions and market data are correct.

Only after the read-only flow is verified:
- give the key trade permission,
- set `DRY_RUN=false`,
- set `LIVE_TRADING_CONFIRM=YES_I_UNDERSTAND`,
- test with a very small position.

The project intentionally does not auto-retry an order when the network outcome is ambiguous. Each order gets a unique label so its state can be checked explicitly before any manual retry.

## Strategy parameters

The ML layer is kept from the APPL logic:
- return windows: 125, 150, 175, 200, 225, 250 bars
- online linear model
- horizon: 37 bars
- learning rate: 0.00325
- L2: 0.425

## Notes

Coinbase Advanced Trade and Global Derivatives are not the same API surface as the old INTX perpetuals API. The current SDK's Global Derivatives adapter is the appropriate integration path for perpetuals.

If you instead want **Coinbase Advanced Trade Spot**, that is a separate adapter and short positions are not available in the same way.
