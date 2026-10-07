def load_closed_data(symbol, base_url, interval, limit=1000, max_attempts=3):
    """
    Load recent Binance klines and return only candles that are closed.

    Retries are bounded. HTTP 429/418 are raised immediately so the caller
    can back off instead of repeatedly hitting the API.
    """
    if not 1 <= limit <= 1000:
        raise ValueError("'limit' must be between 1 and 1000.")

    url = f"{base_url.rstrip('/')}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    last_error = None

    for attempt in range(max_attempts):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=(3, 10),  # connect timeout, response timeout
            )

            # Don't automatically retry rate limits here. The outer loop
            # will respect Retry-After and wait before trying again.
            if response.status_code in (418, 429):
                response.raise_for_status()

            if response.status_code in (500, 502, 503, 504):
                response.raise_for_status()

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

            data = pd.DataFrame(rows, columns=columns)
            data["open_time"] = pd.to_datetime(
                data["open_time"], unit="ms", utc=True
            )
            data["close_time"] = pd.to_datetime(
                data["close_time"], unit="ms", utc=True
            )

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
                data[column] = pd.to_numeric(data[column], errors="coerce")

            # Leave a small grace period for exchange/data-feed timing.
            cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(seconds=2)
            data = data.loc[data["close_time"] < cutoff].copy()

            if data.empty:
                raise RuntimeError(
                    "Binance returned no fully closed candles yet."
                )

            data = (
                data.sort_values("open_time")
                    .drop_duplicates("open_time")
                    .set_index("open_time")
            )

            return data

        except requests.HTTPError:
            # Don't retry 429/418 here; caller handles Retry-After.
            raise

        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc

            if attempt + 1 >= max_attempts:
                break

            # Bounded retry delay for temporary network/server/data issues.
            time.sleep(1 + attempt)

    raise RuntimeError(
        f"Could not load closed candles after {max_attempts} attempts: "
        f"{last_error}"
    )