from src.trading.strategy import prediction_to_position

def test_strategy_long():
    assert prediction_to_position(0.01, 1.0, 0.001, 0.001, True) == 1

def test_strategy_flat():
    assert prediction_to_position(0.0001, 1.0, 0.001, 0.001, True) == 0

def test_strategy_short():
    assert prediction_to_position(-0.01, 1.0, 0.001, 0.001, True) == -1
