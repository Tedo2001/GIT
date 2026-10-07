def build_features(raw_df, horizon=30):
    df = raw_df.copy()

    # Past multi-horizon log returns
    return_windows = [125, 150, 175, 200, 225, 250]
    for window in return_windows:
        df[f"ret_{window}"] = np.log(df["close"] / df["close"].shift(window))

    # Target - Future log return for "horizon"
    df["target"] = np.log(
        df["close"].shift(-horizon) / df["close"]
    )

    feature_cols = (
        [f"ret_{w}" for w in return_windows]
    )

    df = df.copy()

    return df, feature_cols, "target"