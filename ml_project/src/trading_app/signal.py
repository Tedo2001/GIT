# Trading Rule/Signal

def prediction_to_position(pred, threshold, allow_shorts=True):
    threshold = abs(threshold)
    if pred > threshold:
        return 1
    elif allow_shorts and pred < -threshold:
        return -1
    else:
        return 0
