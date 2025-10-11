from __future__ import annotations

from typing import Any, Dict, Iterable

import numpy as np

from atlas.utils.logging import StageMeta, stage_line


def _series_stats(series: Iterable[float]) -> Dict[str, Any]:
    arr = np.asarray(list(series), dtype=np.float64)
    if arr.size == 0:
        return {"count": 0}
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
    }


def evaluate(state: Dict[str, Any], cfg: Dict[str, Any], meta: StageMeta) -> Dict[str, Any]:
    observables = state.get("observables", {})
    anchor_id = state.get("id", "unknown")
    tau = float(cfg.get("tau_delta", 0.15))
    value = observables.get("Delta")
    try:
        delta_value = float(value)
    except (TypeError, ValueError):
        delta_value = float("nan")
    series = (
        observables.get("Delta_series")
        or observables.get("Delta_samples")
        or observables.get("delta_series")
    )
    aux: Dict[str, Any] = {"tau_delta": tau, "series_available": bool(series)}
    if series:
        aux["series_stats"] = _series_stats(series)
    status = "PASS"
    notes = ""
    if not np.isfinite(delta_value):
        status = "FAIL"
        notes = "Delta is not finite."
    elif delta_value > tau:
        status = "WARN"
        notes = "Delta exceeds tolerance."
    aux["delta_chart"] = delta_value
    return stage_line(
        meta,
        anchor_id=anchor_id,
        stage="delta",
        status=status,
        metric="delta_chart",
        value=delta_value,
        threshold=tau,
        aux=aux,
        notes=notes,
    )
