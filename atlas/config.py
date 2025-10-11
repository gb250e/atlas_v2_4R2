from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def load_config(path: str | Path, profile: str = "default") -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        cfg_all = json.load(f)
    if "profiles" in cfg_all:
        cfg = cfg_all["profiles"].get(profile, cfg_all.get("default", {}))
    elif "default" in cfg_all:
        cfg = cfg_all["default"]
    else:
        cfg = cfg_all
    with config_path.open("rb") as f:
        cfg["thresholds_sha256"] = hashlib.sha256(f.read()).hexdigest()
    return cfg
