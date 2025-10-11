from __future__ import annotations

from typing import Any, Dict

from atlas.utils.logging import StageMeta, stage_line


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return float(max(lo, min(hi, value)))


def evaluate(
    state: Dict[str, Any],
    cfg: Dict[str, Any],
    meta: StageMeta,
    delta_row: Dict[str, Any],
    nmod_row: Dict[str, Any],
    htop_row: Dict[str, Any],
    tg_row: Dict[str, Any],
    kms_row: Dict[str, Any],
) -> Dict[str, Any]:
    anchor_id = state.get("id", "unknown")
    tau_delta = float(cfg.get("tau_delta", 0.15))
    tau_n = float(cfg.get("tau_n", 0.05))
    delta_value = delta_row.get("aux", {}).get("delta_chart")
    abs_delta_n = nmod_row.get("aux", {}).get("abs_delta_N")
    plateau = bool(htop_row.get("aux", {}).get("plateau_detected", False))

    delta_pass = delta_row.get("status") == "PASS"
    n_pass = nmod_row.get("status") == "PASS"

    if plateau and (not delta_pass or not n_pass):
        cls = "true_tear"
    elif (not plateau) and (not delta_pass or not n_pass):
        cls = "anomaly"
    elif plateau and delta_pass and n_pass:
        cls = "hard_spot"
    else:
        cls = "fake"

    try:
        delta_ratio = float(delta_value) / tau_delta
    except (TypeError, ValueError, ZeroDivisionError):
        delta_ratio = 0.0
    try:
        n_ratio = float(abs_delta_n) / tau_n
    except (TypeError, ValueError, ZeroDivisionError):
        n_ratio = 0.0

    confidence = _clamp(0.5 * (delta_ratio + n_ratio) + (0.5 if plateau else 0.0))

    aux = {
        "class": cls,
        "confidence": confidence,
        "plateau": plateau,
        "delta_status": delta_row.get("status"),
        "nmod_status": nmod_row.get("status"),
        "tg_ind_status": tg_row.get("status"),
        "kms_status": kms_row.get("status"),
        "H_lb": htop_row.get("aux", {}).get("H_lb"),
    }

    priority = cfg.get("triage", {}).get(
        "priority",
        ["true_tear", "anomaly", "hard_spot", "fake"],
    )
    aux["priority_index"] = int(priority.index(cls)) if cls in priority else -1

    return stage_line(
        meta,
        anchor_id=anchor_id,
        stage="triage",
        status="PASS",
        metric="class",
        value=None,
        threshold=None,
        aux=aux,
    )
