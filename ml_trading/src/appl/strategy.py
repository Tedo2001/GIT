
from dataclasses import dataclass

@dataclass(frozen=True)
class Signal:
    timestamp: object
    price: float
    prediction: float
    previous_position: int
    position: int
    action: str
    target_notional: float
    signed_delta_qty: float

def prediction_to_position(pred, threshold_multiplier, taker_fee_rate, slippage_rate, allow_shorts=True):
    one_way_cost = taker_fee_rate + slippage_rate
    threshold = abs(threshold_multiplier * one_way_cost)
    if pred > threshold:
        return 1
    if allow_shorts and pred < -threshold:
        return -1
    return 0

def make_signal(pred, timestamp, price, previous_position, previous_notional,
                equity, risk_per_trade, leverage, threshold_multiplier,
                taker_fee_rate, slippage_rate, allow_shorts):
    desired = prediction_to_position(
        pred, threshold_multiplier, taker_fee_rate, slippage_rate, allow_shorts
    )
    target_notional = equity * leverage * risk_per_trade

    if desired == previous_position:
        action = "HOLD" if desired else "STAY_FLAT"
        notional = previous_notional
        delta_qty = 0.0
    elif desired == 0:
        action = "CLOSE"
        notional = 0.0
        delta_qty = -(previous_position * previous_notional / price)
    else:
        if previous_position == 0:
            action = "OPEN_LONG" if desired == 1 else "OPEN_SHORT"
        else:
            action = "REVERSE_TO_LONG" if desired == 1 else "REVERSE_TO_SHORT"
        notional = target_notional
        current_qty = previous_position * previous_notional / price
        target_qty = desired * target_notional / price
        delta_qty = target_qty - current_qty

    return Signal(
        timestamp=timestamp,
        price=price,
        prediction=float(pred),
        previous_position=int(previous_position),
        position=int(desired),
        action=action,
        target_notional=float(notional),
        signed_delta_qty=float(delta_qty),
    )
