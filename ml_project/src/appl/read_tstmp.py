def read_last_processed_timestamp():
    if not LAST_PROCESSED_FILE.exists():
        return None

    text = LAST_PROCESSED_FILE.read_text().strip()
    if not text:
        return None

    return pd.Timestamp(text)


def save_last_processed_timestamp(timestamp):
    LAST_PROCESSED_FILE.write_text(pd.Timestamp(timestamp).isoformat())


def sleep_until_next_bar():
    now = time.time()

    next_boundary = (
        (int(now) // BAR_SECONDS_VALUE + 1) * BAR_SECONDS_VALUE
        + CLOSE_GRACE_SECONDS
    )

    sleep_seconds = max(1.0, next_boundary - now)
    print(f"Waiting about {sleep_seconds:.0f}s for the next bar check.")
    time.sleep(sleep_seconds)


def retry_after_seconds(exc):
    response = getattr(exc, "response", None)
    if response is None:
        return None

    value = response.headers.get("Retry-After")
    if value is None:
        return None

    try:
        return max(1.0, float(value))
    except ValueError:
        return None


last_processed_bar = read_last_processed_timestamp()
error_backoff = 5

print("Starting bar monitor.")
print("Previously processed bar:", last_processed_bar)

while True:
    try:
        # One full-history request per check. No separate timestamp-check request.
        raw_closed_df = load_closed_data(
            SYMBOL,
            BASE_URL,
            BAR_SIZE,
            limit=1000,
        )

        latest_closed_timestamp = raw_closed_df.index[-1]

        if (
            last_processed_bar is None
            or latest_closed_timestamp > last_processed_bar
        ):
            signal = make_signal_from_closed_data(raw_closed_df)

            print("New closed bar:", latest_closed_timestamp)
            display(signal)

            # Save only after the signal function succeeds.
            save_last_processed_timestamp(latest_closed_timestamp)
            last_processed_bar = latest_closed_timestamp
            error_backoff = 5
        else:
            print("No new closed bar.")

        sleep_until_next_bar()

    except KeyboardInterrupt:
        print("Stopped by user.")
        break

    except Exception as exc:
        wait_seconds = retry_after_seconds(exc)

        if wait_seconds is None:
            wait_seconds = error_backoff
            error_backoff = min(error_backoff * 2, 300)

        print(
            f"Data check failed: {exc}. "
            f"Waiting {wait_seconds:.0f}s before retrying."
        )
        time.sleep(wait_seconds)