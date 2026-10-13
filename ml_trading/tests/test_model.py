import pandas as pd
import numpy as np

from src.trading.model import causal_predict

def test_causal_predict():
    n = 400
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    close = 100 + np.cumsum(np.sin(np.arange(n) / 17.0) * 0.1 + 0.02)
    df = pd.DataFrame({"close": close}, index=idx)
    pred, ts, price = causal_predict(df, horizon=37)
    assert np.isfinite(pred)
    assert ts == idx[-1]
    assert price == float(close[-1])
