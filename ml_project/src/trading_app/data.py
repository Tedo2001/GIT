# Load historical market data loading from Binance's public market-data API

def load_data(symbol, base_url, interval, limit=300):
    """Load the most recent candles and return them indexed by candle open time."""
    if not 1 <= limit <= 1000:
        raise ValueError("'limit' must be between 1 and 1000.")

    url = f"{base_url}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    rows = response.json()

    if not rows:
        raise ValueError("No data returned from Binance.")

    columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
        "ignore",
    ]

    df = pd.DataFrame(rows, columns=columns)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
    ]
    
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return (
        df.sort_values("open_time")
          .drop_duplicates("open_time")
          .set_index("open_time")
    )
