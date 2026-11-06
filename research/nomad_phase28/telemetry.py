"""Convert telemetry at output boundaries, without changing controller values."""
import numpy as np


def builtin(value):
    if isinstance(value, np.ndarray):
        return builtin(value.tolist())
    if isinstance(value, np.generic):
        return builtin(value.item())
    if isinstance(value, dict):
        return {builtin(k): builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [builtin(v) for v in value]
    return value
