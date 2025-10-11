from __future__ import annotations

from typing import Any, Dict

import numpy as np

from atlas.utils.logging import StageMeta, stage_line


def evaluate(state: Dict[str, Any], cfg: Dict[str, Any], meta: StageMeta) -> Dict[str, Any]:
    anchor_id = state.get("id", "unknown")
    observables = state.get("observables", {})
    kms_cfg = cfg.get("kms", {})
    comm_max = float(kms_cfg.get("commutator_max", 0.05))
    pmax_tol = float(kms_cfg.get("pmax_tol", 0.10))
    commutator = observables.get("commutator_bound")
    pmax = observables.get("pmax")
    spectral = observables.get("spectral_radius")

    status = "PASS"
    notes = ""

    comm_val = None
    if commutator is not None:
        try:
            parsed = float(commutator)
            if np.isfinite(parsed):
                comm_val = parsed
        except (TypeError, ValueError):
            comm_val = None

    p_val = None
    if pmax is not None:
        try:
            parsed = float(pmax)
            if np.isfinite(parsed):
                p_val = parsed
        except (TypeError, ValueError):
            p_val = None

    policy = kms_cfg.get("policy", "full")

    if comm_val is None:
        status = "INCONCLUSIVE"
        notes = "Commutator bound unavailable."
    elif comm_val > comm_max:
        status = "WARN"
        notes = "Commutator exceeds bound."

    if p_val is not None and p_val > pmax_tol:
        status = "WARN"
        policy = "geometric_only"
        notes = (notes + " " if notes else "") + "pmax above tolerance."

    aux = {
        "commutator_bound": comm_val,
        "commutator_max": comm_max,
        "pmax": p_val,
        "pmax_tol": pmax_tol,
        "policy": policy,
        "spectral_radius": spectral,
    }

    return stage_line(
        meta,
        anchor_id=anchor_id,
        stage="kms",
        status=status,
        metric="compatibility",
        value=comm_val,
        threshold=comm_max,
        aux=aux,
        notes=notes,
    )
