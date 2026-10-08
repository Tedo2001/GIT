
from src.trading.engine import TradingEngine

if __name__ == "__main__":
    result = TradingEngine().run_once(force=True)
    print(result)
