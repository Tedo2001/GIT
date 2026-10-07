def prediction_to_position(pred, threshold_multiplier, taker_fee_rate, slippage_rate, allow_shorts=True):
    one_way_cost = taker_fee_rate + slippage_rate
    threshold = abs(threshold_multiplier * one_way_cost)
    if pred > threshold:
        return 1
    elif allow_shorts and pred < -threshold:
        return -1
    else:
        return 0