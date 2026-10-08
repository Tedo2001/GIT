
import numpy as np

RETURN_WINDOWS = [125, 150, 175, 200, 225, 250]

class LinearRegressionModel:
    """Same causal online linear model used in the supplied appl.ipynb."""
    def __init__(self, n_features, lr=0.001, model_l2=0.0):
        self.w = np.zeros(n_features, dtype=float)
        self.b = 0.0
        self.lr = lr
        self.model_l2 = model_l2

    def predict(self, x):
        x = np.asarray(x, dtype=float).reshape(-1)
        return float(np.dot(self.w, x) + self.b)

    def update(self, x, y):
        x = np.asarray(x, dtype=float).reshape(-1)
        y = float(y)
        pred = self.predict(x)
        err = pred - y
        self.w -= self.lr * (err * x + self.model_l2 * self.w)
        self.b -= self.lr * err
        return err

def build_features(raw_df, horizon=30):
    df = raw_df.copy()
    for window in RETURN_WINDOWS:
        df[f"ret_{window}"] = np.log(df["close"] / df["close"].shift(window))
    df["target"] = np.log(df["close"].shift(-horizon) / df["close"])
    feature_cols = [f"ret_{w}" for w in RETURN_WINDOWS]
    return df, feature_cols, "target"

def causal_predict(raw_closed_df, horizon=37, lr=0.00325, model_l2=0.425):
    df, feature_cols, target_col = build_features(raw_closed_df, horizon)
    if len(df) <= max(RETURN_WINDOWS) + horizon:
        raise ValueError("Not enough candles for the feature windows and target horizon.")

    X = df[feature_cols].to_numpy(dtype=float)
    y = df[target_col].to_numpy(dtype=float)

    model = LinearRegressionModel(len(feature_cols), lr=lr, model_l2=model_l2)

    for i in range(len(df)):
        matured_idx = i - horizon
        if matured_idx >= 0:
            x_matured, y_matured = X[matured_idx], y[matured_idx]
            if np.isfinite(y_matured) and np.all(np.isfinite(x_matured)):
                model.update(x_matured, y_matured)

    x_current = X[-1]
    if not np.all(np.isfinite(x_current)):
        raise ValueError("Latest feature row contains NaN/inf.")

    pred = float(np.clip(model.predict(x_current), -0.2, 0.2))
    return pred, df.index[-1], float(df["close"].iloc[-1])
