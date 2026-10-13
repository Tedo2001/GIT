from __future__ import annotations

import pandas as pd


def _resolution(interval: str) -> str:
    mapping = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "2h": "120", "4h": "240", "1d": "1D"}
    if interval not in mapping:
        raise ValueError(f"Unsupported interval {interval}. Supported: {', '.join(mapping)}")
    return mapping[interval]


def normalize_chart_data(raw: dict, now_ms: int | None = None) -> pd.DataFrame:
    now_ms = now_ms or int(pd.Timestamp.utcnow().timestamp() * 1000)
    ticks = raw.get("ticks", [])
    opens = raw.get("open", [])
    highs = raw.get("high", [])
    lows = raw.get("low", [])
    closes = raw.get("close", [])
    volumes = raw.get("volume", [])

    rows = []
    for i, tick in enumerate(ticks):
        close_time = int(tick)
        if close_time >= now_ms:
            continue
        rows.append(
            {
                "open_time": close_time,
                "close_time": close_time,
                "open": float(opens[i]),
                "high": float(highs[i]),
                "low": float(lows[i]),
                "close": float(closes[i]),
                "volume": float(volumes[i]) if i < len(volumes) else 0.0,
            }
        )

    if not rows:
        raise ValueError("No fully closed Coinbase Global Derivatives candles were returned")

    df = pd.DataFrame(rows)
    df = df.drop_duplicates("close_time").sort_values("close_time").reset_index(drop=True)
    df.index = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    return df


def interval_to_ms(interval: str) -> int:
    units = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    if interval[-1] not in units:
        raise ValueError(f"Unsupported interval: {interval}")
    return int(interval[:-1]) * units[interval[-1]]
