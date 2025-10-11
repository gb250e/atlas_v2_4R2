from __future__ import annotations

from typing import Any, Dict

import numpy as np

from atlas.utils.logging import StageMeta, stage_line


def evaluate(state: Dict[str, Any], cfg: Dict[str, Any], meta: StageMeta) -> Dict[str, Any]:
    anchor_id = state.get("id", "unknown")
    observables = state.get("observables", {})
    tg_cfg = cfg.get("temporal_gauge", {}).get("tg_independence", {})
    frob_tol = float(tg_cfg.get("frobenius_tol", 1e-3))
    orth_tol = float(tg_cfg.get("orthogonality_tol", 1e-6))

    matrix = (
        observables.get("TG_matrix")
        or observables.get("temporal_gauge_matrix")
        or observables.get("temporal_gauge")
    )
    status = "INCONCLUSIVE"
    notes = "Temporal gauge matrix missing."
    frob_resid = None
    orth_resid = None

    if matrix is not None:
        arr = np.asarray(matrix, dtype=np.float64)
        if arr.ndim == 2:
            gram = arr.T @ arr
            ident = np.eye(gram.shape[0], dtype=np.float64)
            frob_resid = float(np.linalg.norm(gram - ident, ord="fro"))
            orth_resid = float(np.linalg.norm(arr @ arr.T - ident, ord="fro"))
            status = "PASS"
            notes = ""
            if frob_resid > frob_tol or orth_resid > orth_tol:
                status = "WARN"
                notes = "Gauge independence tolerances exceeded."
        else:
            status = "FAIL"
            notes = "Temporal gauge data malformed."
    aux = {
        "frobenius_resid": frob_resid,
        "orthogonality_resid": orth_resid,
        "frobenius_tol": frob_tol,
        "orthogonality_tol": orth_tol,
    }
    diff = observables.get("TG_finite_diff")
    if diff is not None:
        diff_arr = np.asarray(diff, dtype=np.float64)
        aux["finite_diff_norm"] = float(np.linalg.norm(diff_arr))

    return stage_line(
        meta,
        anchor_id=anchor_id,
        stage="tg_ind",
        status=status,
        metric="verification",
        value=None,
        threshold=None,
        aux=aux,
        notes=notes,
    )
