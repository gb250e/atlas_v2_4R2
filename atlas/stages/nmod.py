from __future__ import annotations

from typing import Any, Dict, Iterable

import numpy as np

from atlas.utils.logging import StageMeta, stage_line


def _guard_metrics(series: Iterable[float]) -> Dict[str, Any]:
    arr = np.asarray(list(series), dtype=np.float64)
    metrics: Dict[str, Any] = {"count": int(arr.size)}
    if arr.size >= 2:
        metrics["order_disagreement"] = float(abs(arr[-1] - arr[-2]))
    if arr.size >= 3:
        diffs = np.diff(arr)
        metrics["oscillations"] = int(np.sum(np.sign(diffs[1:]) != np.sign(diffs[:-1])))
        metrics["max_step"] = float(np.max(np.abs(diffs)))
    metrics["max_abs"] = float(np.max(np.abs(arr))) if arr.size else 0.0
    return metrics


def evaluate(state: Dict[str, Any], cfg: Dict[str, Any], meta: StageMeta) -> Dict[str, Any]:
    observables = state.get("observables", {})
    anchor_id = state.get("id", "unknown")
    tau = float(cfg.get("tau_n", 0.05))
    guards_cfg = cfg.get("N_mod", {}).get("extrapolation_guard", {})
    order_tol = float(guards_cfg.get("order_agreement_tol", 5e-3))
    osc_max = int(guards_cfg.get("oscillation_max", 3))
    series = (
        observables.get("deltaN_series")
        or observables.get("deltaN_samples")
        or observables.get("n_series")
    )
    value = observables.get("deltaN")
    try:
        delta_n = float(value)
    except (TypeError, ValueError):
        delta_n = float("nan")
    abs_delta_n = float(abs(delta_n)) if np.isfinite(delta_n) else float("nan")
    aux: Dict[str, Any] = {
        "tau_n": tau,
        "guard_thresholds": {
            "order_agreement_tol": order_tol,
            "oscillation_max": osc_max,
        },
    }
    status = "PASS"
    notes = ""

    guard_pass = True
    if series:
        metrics = _guard_metrics(series)
        aux["guard_metrics"] = metrics
        if metrics.get("order_disagreement", 0.0) and metrics["order_disagreement"] > order_tol:
            guard_pass = False
            notes += "Order disagreement above tolerance. "
        if metrics.get("oscillations", 0) and metrics["oscillations"] > osc_max:
            guard_pass = False
            notes += "Oscillation count above limit. "
    else:
        aux["guard_metrics"] = {"count": 0}
        guard_pass = False
        notes += "Missing series data for guard checks. "

    if not np.isfinite(abs_delta_n):
        status = "FAIL"
        notes += "deltaN is not finite."
    elif abs_delta_n > tau:
        status = "WARN"
        notes += "deltaN exceeds tolerance. "

    if not guard_pass and status == "PASS":
        status = "WARN"
        notes += "Extrapolation guard raised warnings."

    aux["abs_delta_N"] = abs_delta_n
    aux["guard_pass"] = guard_pass
    return stage_line(
        meta,
        anchor_id=anchor_id,
        stage="nmod",
        status=status,
        metric="abs_delta_N",
        value=abs_delta_n,
        threshold=tau,
        aux=aux,
        notes=notes.strip(),
    )
