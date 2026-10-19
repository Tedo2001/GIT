# Coinbase ML Trading Bot — APPL Strategy

A machine-learning-driven trading bot integrating Coinbase Global Derivatives with the APPL strategy. The project combines causal online learning, live account-state reconciliation, and configurable risk controls to generate trading signals and manage order execution.

> **Safety first:** The bot defaults to dry-run mode. Live trading must be explicitly enabled, and API credentials must be kept outside version control.

## Overview

The bot is designed to connect to Coinbase Global Derivatives, retrieve market and account data, generate machine-learning-based trading signals, and manage execution according to predefined risk policies.

The implementation follows three core principles:

- **Exchange-authoritative state:** Account equity, available funds, positions, open orders, and available leverage or liquidation information are obtained from Coinbase rather than hardcoded account assumptions.
- **Causal model execution:** The model operates on closed one-hour candles to avoid using incomplete candle data.
- **Explicit execution controls:** Dry-run mode is enabled by default, and live order placement requires deliberate configuration.

## Why Coinbase Global Derivatives?

Coinbase Global Derivatives provides a derivatives integration path for this project, making it a potential alternative to a Hyperliquid perpetual-futures setup.

The integration uses the Coinbase Python SDK's `DeribitRetailClient` for the Global Derivatives gateway.

**API distinction:** Coinbase Advanced Trade Spot and Global Derivatives are separate integration surfaces. The spot API does not provide short exposure in the same way as a derivatives product. API compatibility, regional availability, and account eligibility should be verified before deployment.

## Risk Management and Account State

The exchange is the source of truth for account-specific values, including:

- Account equity
- Available funds
- Current positions
- Leverage and liquidation fields returned by the account state
- Open orders

Account size and leverage are **not hardcoded in the `.env` file**.

The following environment variables define risk policies, not actual account properties:

| Parameter | Purpose |
|---|---|
| `POSITION_FRACTION` | Defines the intended position size relative to the relevant account value |
| `MAX_POSITION_FRACTION` | Caps the permitted position fraction |
| `MAX_LEVERAGE_CAP` | Defines the maximum leverage permitted by the bot's risk policy |

The bot calculates its target position using live account state and the configured risk limits.

These controls do not replace exchange-side margin requirements, liquidation rules, or independent risk validation.

## Prerequisites

- Python compatible with the versions specified by the project dependencies
- PyCharm or another Python development environment
- A Coinbase account with access to the intended derivatives product
- Coinbase API credentials with the required permissions
- Access to the relevant market data and account endpoints

## Installation

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/TeodorLechev/GIT.git
cd GIT/ml_trading
```

Create a virtual environment using PyCharm or your preferred Python environment manager.

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment configuration file by copying the example:

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` using File Explorer or PowerShell.

Keep the default setting:

```dotenv
DRY_RUN=true
```

Review `.env.example` and configure the required non-secret settings before running the bot.

## API Credentials

### Recommended: Coinbase CDP API Key

1. Create a Coinbase CDP API key.
2. Download the JSON key file.
3. Store the file outside the repository.
4. Set `COINBASE_KEY_FILE` to the absolute path of the key file, either in `.env` or in the environment used by PyCharm.

Alternatively, the official Coinbase SDK supports authentication through:

- `COINBASE_API_KEY`
- `COINBASE_API_SECRET`

Use the authentication method supported by the installed SDK version and the configured API integration.

### Security Requirements

- Never commit API keys, secrets, or private JSON key files.
- Keep `.env` and credential files out of version control.
- Prefer the minimum API permissions required for the task.
- Use view-only credentials for initial verification whenever supported.
- Never expose credentials in logs, screenshots, notebooks, or error reports.

Before committing changes, verify that sensitive files are excluded by `.gitignore`.

## First Run: Dry-Run Mode

Execute the bot once:

```bash
python run_once.py
```

With `DRY_RUN=true`, the expected workflow is:

1. Authenticate with Coinbase.
2. Retrieve the account summary.
3. Read current positions and open orders.
4. Fetch closed one-hour candles.
5. Run the causal machine learning model.
6. Generate and print a `LONG`, `SHORT`, or `FLAT` signal.
7. Skip order placement.

The first run should be used to verify authentication, data integrity, model execution, and account-state reconciliation.

**Expected behavior:** The bot may calculate a target position and produce a trading signal, but it must not submit an order while dry-run mode is enabled.

## Enabling Live Trading

Live execution should only be enabled after the read-only workflow has been verified.

Recommended procedure:

1. Run the bot with a view-only API key, if supported.
2. Confirm that account information, positions, open orders, and market data are correct.
3. Verify that only closed candles are used for signal generation.
4. Review the calculated target size and all risk limits.
5. Grant trade permissions only when necessary.
6. Set `DRY_RUN=false`.
7. Set `LIVE_TRADING_CONFIRM=YES_I_UNDERSTAND`.
8. Begin with a very small position and monitor execution carefully.

Do not enable live trading until the order lifecycle, position sizing, and failure-handling behavior have been reviewed.

### Order Execution Safety

The bot intentionally avoids automatically retrying an order when the network outcome is ambiguous.

Each order receives a unique label so its state can be checked explicitly before any manual retry. This reduces the risk of duplicate orders when an initial request may have reached the exchange but its response was lost.

An ambiguous order outcome should be reconciled against the exchange's order and position state before further action.

## APPL Strategy Configuration

The machine-learning layer retains the APPL strategy parameters.

| Parameter | Value |
|---|---:|
| Return windows | 125, 150, 175, 200, 225, 250 bars |
| Model | Online linear model |
| Prediction horizon | 37 bars |
| Learning rate | 0.00325 |
| L2 regularization | 0.425 |
| Candle interval | 1 hour |
| Signal outputs | `LONG`, `SHORT`, `FLAT` |

The model uses historical returns across multiple lookback windows to produce trading signals. The online learning configuration defines how the model updates and how strongly regularization constrains its coefficients.

The strategy's predictive performance and profitability are not guaranteed and should be assessed using appropriate out-of-sample testing, transaction costs, slippage assumptions, and risk metrics.

## Configuration Reference

| Variable | Description |
|---|---|
| `COINBASE_KEY_FILE` | Path to the Coinbase credential JSON file |
| `COINBASE_API_KEY` | Alternative API key authentication setting |
| `COINBASE_API_SECRET` | Alternative API secret authentication setting |
| `DRY_RUN` | Enables or disables order submission |
| `LIVE_TRADING_CONFIRM` | Explicit confirmation required by the live-trading configuration |
| `POSITION_FRACTION` | Position-sizing policy |
| `MAX_POSITION_FRACTION` | Maximum permitted position fraction |
| `MAX_LEVERAGE_CAP` | Maximum permitted leverage under the bot's policy |

Refer to `.env.example` and the implementation for exact defaults, accepted values, and any additional required settings.

## Limitations and Operational Considerations

- **Market risk:** Derivatives trading can result in rapid losses and liquidation.
- **Model risk:** Historical patterns may not persist in future market conditions.
- **Data quality:** Missing, delayed, or inconsistent market data can affect predictions.
- **Execution risk:** Network failures and exchange latency can leave order outcomes uncertain.
- **API compatibility:** Coinbase product availability, authentication requirements, and SDK interfaces may change.
- **Risk controls:** Local position limits do not guarantee that exchange-side margin or liquidation constraints will be satisfied.

The bot should be treated as an experimental trading system rather than a guaranteed source of returns.

## Disclaimer

This project is intended for educational, research, and software-development purposes only. It does not constitute financial or investment advice.

Automated derivatives trading involves substantial risk, including the potential loss of all allocated capital. Historical results and machine learning predictions do not guarantee future performance.

Use at your own risk. Validate the system thoroughly before allowing it to place live orders.

## Author

**Teodor Lechev**

GitHub: [TeodorLechev](https://github.com/TeodorLechev)
