from __future__ import annotations

from typing import Dict, Iterable

import numpy as np


def richardson_error(
    samples: Iterable[float],
    *,
    order: int = 2,
    safety_factor: float = 1.5,
) -> Dict[str, float]:
    """Estimate the discretisation error using a Richardson remainder model."""
    arr = np.asarray(list(samples), dtype=np.float64)
    if arr.size < 2:
        return {"estimate": float(arr[-1]) if arr.size else float("nan"), "error": 0.0}
    latest = arr[-1]
    prev = arr[-2]
    denom = max(1.0, float(2**order - 1))
    err = safety_factor * abs(latest - prev) / denom
    return {"estimate": float(latest), "error": float(err)}
