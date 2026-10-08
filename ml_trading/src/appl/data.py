import time
import requests
import pandas as pd

BAR_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600,
    "8h": 28800, "12h": 43200, "1d": 86400,
}


class BinanceMarketData:
    """Public Binance candle loader for Spot or USDⓈ-M Futures."""

    def __init__(self, base_url: str, symbol: str, interval: str, futures: bool = False, timeout=(5, 15)):
        self.base_url = base_url.rstrip("/")
        self.symbol = symbol
        self.interval = interval
        self.futures = futures
        self.timeout = timeout

    @property
    def kline_path(self) -> str:
        # Spot: /api/v3/klines
        # USDⓈ-M Futures: /fapi/v1/klines
        return "/fapi/v1/klines" if self.futures else "/api/v3/klines"

    def klines(self, limit=1000, max_attempts=3) -> pd.DataFrame:
        if self.interval not in BAR_SECONDS:
            raise ValueError(f"Unsupported interval: {self.interval}")
        url = f"{self.base_url}{self.kline_path}"
        params = {"symbol": self.symbol, "interval": self.interval, "limit": limit}
        last_error = None

        for attempt in range(max_attempts):
            try:
                r = requests.get(url, params=params, timeout=self.timeout)
                if r.status_code in (418, 429):
                    r.raise_for_status()
                if r.status_code in (500, 502, 503, 504):
                    r.raise_for_status()
                r.raise_for_status()
                rows = r.json()
                if not rows:
                    raise RuntimeError("No klines returned.")

                columns = [
                    "open_time", "open", "high", "low", "close", "volume", "close_time",
                    "quote_asset_volume", "number_of_trades",
                    "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
                ]
                df = pd.DataFrame(rows, columns=columns)
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
                df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
                numeric = [
                    "open", "high", "low", "close", "volume", "quote_asset_volume",
                    "number_of_trades", "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume"
                ]
                for c in numeric:
                    df[c] = pd.to_numeric(df[c], errors="coerce")

                cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(seconds=2)
                df = df[df["close_time"] < cutoff].copy()
                if df.empty:
                    raise RuntimeError("No fully closed candles yet.")

                return (
                    df.sort_values("open_time")
                      .drop_duplicates("open_time")
                      .set_index("open_time")
                )
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt + 1 < max_attempts:
                    time.sleep(1 + attempt)
        raise RuntimeError(f"Could not load candles: {last_error}")


class BinanceFuturesMarketData(BinanceMarketData):
    def __init__(self, base_url: str, symbol: str, interval: str, timeout=(5, 15)):
        super().__init__(base_url, symbol, interval, futures=True, timeout=timeout)
