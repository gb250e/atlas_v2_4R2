from __future__ import annotations

from typing import Dict, Iterable, Optional

import numpy as np
from scipy import stats


def theil_sen_plateau(
    values: Iterable[float],
    *,
    x: Optional[Iterable[float]] = None,
    alpha: float = 0.10,
    slope_tol: float = 5e-3,
) -> Dict[str, float | bool]:
    """Evaluate whether the supplied series is consistent with a plateau."""
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.size < 2:
        return {
            "plateau": bool(arr.size == 1),
            "slope": float(arr[-1]) if arr.size else 0.0,
            "intercept": float(arr[-1]) if arr.size else 0.0,
            "p_value": 1.0,
            "lower_ci": 0.0,
            "upper_ci": 0.0,
        }
    if x is None:
        x = np.arange(arr.size, dtype=np.float64)
    else:
        x = np.asarray(list(x), dtype=np.float64)
    slope, intercept, lo, hi = stats.theilslopes(arr, x, alpha=1.0 - alpha)
    tau = stats.kendalltau(x, arr)
    p_raw = tau.pvalue if tau.pvalue is not None else 1.0
    p_value = float(p_raw if p_raw is not None else 1.0)
    if not np.isfinite(p_value):
        p_value = 1.0
    plateau = bool(abs(slope) <= slope_tol and p_value > alpha and lo <= 0.0 <= hi)
    result = {
        "plateau": plateau,
        "slope": float(slope),
        "intercept": float(intercept),
        "p_value": p_value,
        "lower_ci": float(lo),
        "upper_ci": float(hi),
    }
    for key, default in ("slope", 0.0), ("intercept", 0.0), ("lower_ci", 0.0), ("upper_ci", 0.0):
        val = result[key]
        if not np.isfinite(val):
            result[key] = default
    return result
