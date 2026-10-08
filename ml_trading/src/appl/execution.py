
import hashlib
import hmac
import time
from decimal import Decimal, ROUND_DOWN
import requests

def _fmt(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    return format(Decimal(str(value)), "f")

class BinanceREST:
    def __init__(self, api_key, api_secret, base_url, futures=False, dry_run=False):
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.base_url = base_url.rstrip("/")
        self.futures = futures
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": api_key})
        self._exchange_info = None

    def _request(self, method, path, params=None, signed=False):
        params = dict(params or {})
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            query = "&".join(f"{k}={requests.utils.quote(str(v), safe='')}" for k, v in params.items())
            params["signature"] = hmac.new(
                self.api_secret, query.encode(), hashlib.sha256
            ).hexdigest()

        url = f"{self.base_url}{path}"
        r = self.session.request(method, url, params=params, timeout=(5, 20))
        if not r.ok:
            raise RuntimeError(f"Binance {r.status_code}: {r.text}")
        return r.json()

    def exchange_info(self):
        if self._exchange_info is None:
            path = "/fapi/v1/exchangeInfo" if self.futures else "/api/v3/exchangeInfo"
            self._exchange_info = self._request("GET", path)
        return self._exchange_info

    def symbol_rules(self, symbol):
        info = next(x for x in self.exchange_info()["symbols"] if x["symbol"] == symbol)
        lot = next((f for f in info["filters"] if f["filterType"] in {"LOT_SIZE", "MARKET_LOT_SIZE"}), None)
        if not lot:
            raise RuntimeError(f"No LOT_SIZE filter for {symbol}")
        return {
            "step_size": Decimal(lot["stepSize"]),
            "min_qty": Decimal(lot["minQty"]),
            "base_asset": info["baseAsset"],
            "quote_asset": info["quoteAsset"],
        }

    def round_qty(self, symbol, qty):
        rules = self.symbol_rules(symbol)
        step = rules["step_size"]
        q = Decimal(str(abs(qty)))
        rounded = (q / step).to_integral_value(rounding=ROUND_DOWN) * step
        if rounded < rules["min_qty"]:
            return Decimal("0")
        return rounded

    def futures_position(self, symbol):
        if not self.futures:
            raise RuntimeError("futures_position is only available in Futures mode")
        rows = self._request("GET", "/fapi/v2/positionRisk", {"symbol": symbol}, signed=True)
        row = rows[0]
        qty = Decimal(row["positionAmt"])
        entry = Decimal(row["entryPrice"])
        return {"qty": qty, "entry_price": entry, "side": 1 if qty > 0 else (-1 if qty < 0 else 0)}

    def spot_balance(self, asset):
        rows = self._request("GET", "/api/v3/account", signed=True)["balances"]
        row = next((x for x in rows if x["asset"] == asset), None)
        if not row:
            return Decimal("0")
        return Decimal(row["free"]) + Decimal(row["locked"])

    def _futures_order(self, symbol, side, qty, reduce_only=False):
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": _fmt(qty),
            "newOrderRespType": "RESULT",
        }
        if reduce_only:
            params["reduceOnly"] = "true"
        return self._request("POST", "/fapi/v1/order", params, signed=True)

    def _spot_order(self, symbol, side, qty):
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": _fmt(qty),
            "newOrderRespType": "FULL",
        }
        return self._request("POST", "/api/v3/order", params, signed=True)

    def close_futures(self, symbol):
        pos = self.futures_position(symbol)
        qty = self.round_qty(symbol, pos["qty"])
        if qty == 0:
            return {"status": "NO_POSITION"}
        side = "SELL" if pos["qty"] > 0 else "BUY"
        if self.dry_run:
            return {"status": "DRY_RUN", "side": side, "quantity": str(qty)}
        return self._futures_order(symbol, side, qty, reduce_only=True)

    def open_futures(self, symbol, direction, quantity):
        qty = self.round_qty(symbol, quantity)
        if qty == 0:
            raise RuntimeError("Rounded Futures quantity is below exchange minimum.")
        side = "BUY" if direction > 0 else "SELL"
        if self.dry_run:
            return {"status": "DRY_RUN", "side": side, "quantity": str(qty)}
        return self._futures_order(symbol, side, qty, reduce_only=False)

    def execute_futures_target(self, symbol, target_position, target_qty_abs):
        """One-way Futures mode: reconcile actual Binance position to target LONG/SHORT/FLAT."""
        actual = self.futures_position(symbol)["qty"]
        target = Decimal(str(target_qty_abs)) * Decimal(str(target_position))

        actions = []
        if actual != 0 and ((actual > 0 and target < 0) or (actual < 0 and target > 0) or (target == 0)):
            actions.append(self.close_futures(symbol))
            actual = Decimal("0")

        if target != 0:
            if actual == 0:
                actions.append(self.open_futures(symbol, 1 if target > 0 else -1, abs(target)))
            elif (actual > 0 and target > actual) or (actual < 0 and target < actual):
                extra = abs(target - actual)
                actions.append(self.open_futures(symbol, 1 if target > 0 else -1, extra))
            elif (actual > 0 and target < actual) or (actual < 0 and target > actual):
                reduce_qty = abs(actual - target)
                side = "SELL" if actual > 0 else "BUY"
                q = self.round_qty(symbol, reduce_qty)
                if q:
                    if self.dry_run:
                        actions.append({"status": "DRY_RUN", "side": side, "quantity": str(q), "reduceOnly": True})
                    else:
                        actions.append(self._futures_order(symbol, side, q, reduce_only=True))
        return actions

    def execute_spot_target(self, symbol, target_position, target_qty_abs):
        if target_position < 0:
            raise RuntimeError("Spot execution cannot open SHORT.")
        rules = self.symbol_rules(symbol)
        asset = rules["base_asset"]
        actual = self.spot_balance(asset)
        target = self.round_qty(symbol, target_qty_abs)

        actions = []
        if target == 0:
            qty = self.round_qty(symbol, actual)
            if qty:
                if self.dry_run:
                    actions.append({"status": "DRY_RUN", "side": "SELL", "quantity": str(qty)})
                else:
                    actions.append(self._spot_order(symbol, "SELL", qty))
        elif actual < target:
            qty = self.round_qty(symbol, target - actual)
            if qty:
                if self.dry_run:
                    actions.append({"status": "DRY_RUN", "side": "BUY", "quantity": str(qty)})
                else:
                    actions.append(self._spot_order(symbol, "BUY", qty))
        elif actual > target:
            qty = self.round_qty(symbol, actual - target)
            if qty:
                if self.dry_run:
                    actions.append({"status": "DRY_RUN", "side": "SELL", "quantity": str(qty)})
                else:
                    actions.append(self._spot_order(symbol, "SELL", qty))
        return actions
