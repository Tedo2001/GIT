def make_signal_from_closed_data(raw_closed_df):
    global _wf_previous_position, _wf_previous_size_usd

    df, feature_cols, target_col = build_features(raw_closed_df, HORIZON)

    if len(df) <= HORIZON:
        raise ValueError(
            f"Need more than {HORIZON} rows; got {len(df)}."
        )

    X = df[feature_cols].to_numpy(dtype=float)
    y = df[target_col].to_numpy(dtype=float)

    model = LinearRegressionModel(
        n_features=len(feature_cols),
        lr=LR,
        model_l2=MODEL_L2,
    )

    # Replay history causally: at row i, the label from i - HORIZON
    # is now known.
    for i in range(len(df)):
        matured_idx = i - HORIZON

        if matured_idx >= 0:
            x_matured = X[matured_idx]
            y_matured = y[matured_idx]

            if np.isfinite(y_matured) and np.all(np.isfinite(x_matured)):
                model.update(x_matured, float(y_matured))

    x_current = X[-1]

    if not np.all(np.isfinite(x_current)):
        raise ValueError("Latest row has missing/non-finite features.")

    pred = float(np.asarray(model.predict(x_current)).reshape(-1)[0])
    pred = float(np.clip(pred, -0.2, 0.2))

    desired_position = int(
        prediction_to_position(
            pred,
            THRESHOLD_MULTIPLIER,
            TAKER_FEE_RATE,
            SLIPPAGE_RATE,
            ALLOW_SHORTS,
        )
    )

    timestamp = df.index[-1]
    price = float(df["close"].iloc[-1])

    if not np.isfinite(price) or price <= 0:
        raise ValueError(f"Invalid latest close price: {price}")

    previous_position = int(_wf_previous_position)
    previous_size_usd = float(_wf_previous_size_usd)

    # This is target notional, not a stop-loss-based risk amount.
    target_size_usd = EQUITY * LEVERAGE * RISK_PER_TRADE

    if desired_position == previous_position:
        action = "HOLD" if desired_position != 0 else "STAY_FLAT"
        signal_size_usd = previous_size_usd
        order_signed_quantity = 0.0

    elif desired_position == 0:
        action = "CLOSE"
        signal_size_usd = 0.0
        order_signed_quantity = (
            -previous_position * previous_size_usd / price
        )

    else:
        if previous_position == 0:
            action = "OPEN_LONG" if desired_position == 1 else "OPEN_SHORT"
        else:
            action = (
                "REVERSE_TO_LONG"
                if desired_position == 1
                else "REVERSE_TO_SHORT"
            )

        signal_size_usd = target_size_usd

        current_signed_quantity = (
            previous_position * previous_size_usd / price
        )
        target_signed_quantity = desired_position * target_size_usd / price
        order_signed_quantity = (
            target_signed_quantity - current_signed_quantity
        )

    signal = {
        "timestamp": timestamp,
        "prediction": pred,
        "previous_position": previous_position,
        "position": desired_position,
        "action": action,
        "size_usd": float(signal_size_usd),
        "order_signed_quantity": float(order_signed_quantity),
    }

    # For paper trading only: assume the signal filled.
    # For live trading, update this state after confirmed fills instead.
    if ASSUME_SIGNAL_FILLED and desired_position != previous_position:
        _wf_previous_position = desired_position
        _wf_previous_size_usd = (
            target_size_usd if desired_position != 0 else 0.0
        )

    return signal