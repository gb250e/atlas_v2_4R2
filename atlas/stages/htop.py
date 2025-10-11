from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import numpy as np

from atlas.utils.logging import StageMeta, stage_line
from atlas.utils.plateau import theil_sen_plateau
from atlas.utils.richardson import richardson_error


def _as_array(values: Optional[Iterable[float]]) -> np.ndarray:
    if values is None:
        return np.array([], dtype=np.float64)
    return np.asarray(list(values), dtype=np.float64)


def evaluate(
    state: Dict[str, Any],
    cfg: Dict[str, Any],
    meta: StageMeta,
    delta_row: Dict[str, Any],
    nmod_row: Dict[str, Any],
) -> Dict[str, Any]:
    observables = state.get("observables", {})
    anchor_id = state.get("id", "unknown")
    h_obs = observables.get("H_obs")
    try:
        h_value = float(h_obs)
    except (TypeError, ValueError):
        h_value = float("nan")
    h_series = _as_array(observables.get("H_series") or observables.get("H_samples"))
    h_times = _as_array(observables.get("H_times"))
    plateau_cfg = cfg.get("H_top", {})
    alpha = float(plateau_cfg.get("alpha", 0.10))
    slope_tol = float(plateau_cfg.get("slope_tol", 5e-3))
    plateau = False
    plateau_aux: Dict[str, Any] = {"series_count": int(h_series.size)}
    gt_plateau = state.get("ground_truth", {}).get("H_plateau")
    if h_series.size >= 2:
        res = theil_sen_plateau(
            h_series,
            x=h_times if h_times.size == h_series.size else None,
            alpha=alpha,
            slope_tol=slope_tol,
        )
        plateau = bool(res["plateau"])
        plateau_aux.update(res)
    elif gt_plateau is not None:
        plateau = bool(gt_plateau)
        plateau_aux["reason"] = "ground_truth_fallback"
    elif np.isfinite(h_value):
        plateau = True
        plateau_aux["reason"] = "single_sample"
        plateau_aux["slope"] = 0.0
        plateau_aux["p_value"] = 1.0
    else:
        plateau_aux["reason"] = "no_data"

    err_cfg = plateau_cfg.get("error_budget", {})
    c_delta = float(err_cfg.get("c_delta", 0.5))
    c_n = float(err_cfg.get("c_n", 0.5))
    richardson = richardson_error(h_series if h_series.size else [h_value])
    e_disc = float(richardson["error"])
    delta_val = delta_row.get("aux", {}).get("delta_chart")
    abs_delta_n = nmod_row.get("aux", {}).get("abs_delta_N")
    e_loc = c_delta * float(delta_val if delta_val is not None else 0.0)
    e_resp = c_n * float(abs_delta_n if abs_delta_n is not None else 0.0)
    total_err = e_disc + e_loc + e_resp
    h_lb = h_value - total_err if np.isfinite(h_value) else float("nan")
    lb_floor = float(plateau_cfg.get("lower_bound_min", 0.0))
    status = "PASS"
    notes = ""
    if not np.isfinite(h_value):
        status = "FAIL"
        notes = "H_obs not finite."
    elif not plateau:
        status = "WARN"
        notes = "Plateau criteria not met."
    elif np.isfinite(h_lb) and h_lb < lb_floor:
        status = "WARN"
        notes = "Lower bound below minimum tolerance."

    aux = {
        "H_obs": h_value,
        "plateau_detected": plateau,
        "plateau_details": plateau_aux,
        "error_budget": {
            "E_disc": e_disc,
            "E_loc": e_loc,
            "E_resp": e_resp,
            "total": total_err,
            "coefficients": {"c_delta": c_delta, "c_n": c_n},
        },
        "H_lb": h_lb,
        "lower_bound_min": lb_floor,
    }
    if h_series.size:
        aux["series_tail"] = [float(x) for x in h_series[-5:]]

    return stage_line(
        meta,
        anchor_id=anchor_id,
        stage="htop",
        status=status,
        metric="H_obs",
        value=h_value,
        threshold=None,
        aux=aux,
        notes=notes,
    )
