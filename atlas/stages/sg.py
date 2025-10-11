from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from atlas.utils.logging import StageMeta, stage_line


def _finite(*values: Any) -> bool:
    return all(np.isfinite(float(v)) for v in values if v is not None)


def evaluate(
    state: Dict[str, Any],
    cfg: Dict[str, Any],
    meta: StageMeta,
    delta_row: Dict[str, Any],
    nmod_row: Dict[str, Any],
    htop_row: Dict[str, Any],
) -> List[Dict[str, Any]]:
    anchor_id = state.get("id", "unknown")
    observables = state.get("observables", {})

    results: List[Dict[str, Any]] = []

    required_keys = {"Delta", "deltaN", "H_obs"}
    missing = sorted(k for k in required_keys if k not in observables)
    status = "PASS" if not missing and _finite(*observables.values()) else "FAIL"
    aux0 = {
        "missing": missing,
        "finite": _finite(
            observables.get("Delta"),
            observables.get("deltaN"),
            observables.get("H_obs"),
        ),
    }
    notes = "" if status == "PASS" else "Missing or non-finite observables."
    results.append(
        stage_line(
            meta,
            anchor_id=anchor_id,
            stage="SG-0",
            status=status,
            metric="sanity",
            value=None,
            threshold=None,
            aux=aux0,
            notes=notes,
        )
    )

    status1 = "PASS"
    notes1 = ""
    if delta_row["status"] == "FAIL" or nmod_row["status"] == "FAIL":
        status1 = "FAIL"
        notes1 = "Core metric failure."
    elif delta_row["status"] != "PASS" or nmod_row["status"] != "PASS":
        status1 = "WARN"
        notes1 = "Delta/N warnings present."
    aux1 = {
        "delta_status": delta_row["status"],
        "nmod_status": nmod_row["status"],
        "guard_pass": nmod_row.get("aux", {}).get("guard_pass", False),
    }
    results.append(
        stage_line(
            meta,
            anchor_id=anchor_id,
            stage="SG-1",
            status=status1,
            metric="delta_n_gate",
            value=None,
            threshold=None,
            aux=aux1,
            notes=notes1,
        )
    )

    plateau = bool(htop_row.get("aux", {}).get("plateau_detected", False))
    h_lb = htop_row.get("aux", {}).get("H_lb")
    status2 = "PASS"
    notes2 = ""
    if not plateau:
        status2 = "WARN"
        notes2 = "Plateau not confirmed."
    if not _finite(h_lb):
        status2 = "FAIL"
        notes2 = (notes2 + " " if notes2 else "") + "H lower bound invalid."
    aux2 = {"plateau": plateau, "H_lb": h_lb}
    results.append(
        stage_line(
            meta,
            anchor_id=anchor_id,
            stage="SG-2",
            status=status2,
            metric="plateau_gate",
            value=None,
            threshold=None,
            aux=aux2,
            notes=notes2.strip(),
        )
    )

    status3 = "PASS"
    notes3 = ""
    if status in ("FAIL",) or status1 == "FAIL" or status2 == "FAIL":
        status3 = "FAIL"
        notes3 = "Upstream gate failure."
    elif any(r["status"] == "WARN" for r in results):
        status3 = "WARN"
        notes3 = "Propagation of upstream warnings."
    aux3 = {
        "inputs": [r["status"] for r in results[:-1]],
    }
    results.append(
        stage_line(
            meta,
            anchor_id=anchor_id,
            stage="SG-3",
            status=status3,
            metric="readiness",
            value=None,
            threshold=None,
            aux=aux3,
            notes=notes3,
        )
    )
    return results
