from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    timestamp: object
    price: float
    prediction: float
    previous_position: int
    desired_position: int
    action: str
    target_notional: float


def prediction_to_position(
    pred: float,
    threshold_multiplier: float,
    fee_rate: float,
    slippage_rate: float,
    allow_shorts: bool,
) -> int:
    threshold = abs(threshold_multiplier * (fee_rate + slippage_rate))
    if pred > threshold:
        return 1
    if allow_shorts and pred < -threshold:
        return -1
    return 0


def make_signal(
    pred: float,
    timestamp: object,
    price: float,
    previous_position: int,
    target_notional: float,
    threshold_multiplier: float,
    fee_rate: float,
    slippage_rate: float,
    allow_shorts: bool,
) -> Signal:
    desired = prediction_to_position(
        pred, threshold_multiplier, fee_rate, slippage_rate, allow_shorts
    )
    if desired == previous_position:
        action = "HOLD" if desired else "STAY_FLAT"
    elif desired == 0:
        action = "CLOSE"
    elif previous_position == 0:
        action = "OPEN_LONG" if desired == 1 else "OPEN_SHORT"
    else:
        action = "REVERSE_TO_LONG" if desired == 1 else "REVERSE_TO_SHORT"
    return Signal(
        timestamp=timestamp,
        price=price,
        prediction=float(pred),
        previous_position=int(previous_position),
        desired_position=int(desired),
        action=action,
        target_notional=float(target_notional if desired != 0 else 0.0),
    )
