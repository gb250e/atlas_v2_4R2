from __future__ import annotations

import hashlib
import math
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    """Return a UTC timestamp in ISO-8601 format with explicit Z suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def get_git_commit(cwd: Optional[str] = None) -> str:
    """Fetch the current git commit if available, otherwise return 'unknown'."""
    try:
        commit = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=cwd or os.getcwd(),
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )
        if commit:
            return commit
    except Exception:
        pass
    return "unknown"


def sha256_of_file(path: str) -> str:
    """Compute the SHA-256 digest of a file, returning 'missing' if unavailable."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return "missing"


@dataclass(frozen=True)
class StageMeta:
    """Metadata attached to every StageResult row."""

    seed: int
    commit: str
    thresholds_sha256: str
    schema_version: str = "atlas.stage_result@1"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "commit": self.commit,
            "thresholds_sha256": self.thresholds_sha256,
            "schema_version": self.schema_version,
        }


def _coerce_number(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def stage_line(
    meta: StageMeta,
    *,
    anchor_id: str,
    stage: str,
    status: str,
    metric: Optional[str] = None,
    value: Optional[Any] = None,
    threshold: Optional[Any] = None,
    aux: Optional[Dict[str, Any]] = None,
    notes: str = "",
    cost: Optional[Any] = None,
) -> Dict[str, Any]:
    """Create a StageResult dictionary that conforms to the stage schema."""
    row: Dict[str, Any] = {
        "ts": utc_now(),
        "stage": stage,
        "status": status,
        "metric": metric,
        "value": _coerce_number(value),
        "threshold": _coerce_number(threshold),
        "aux": aux or {},
        "notes": notes,
        "anchor_id": anchor_id,
        **meta.as_dict(),
    }
    if cost is not None:
        row["cost"] = _coerce_number(cost)
    return row
