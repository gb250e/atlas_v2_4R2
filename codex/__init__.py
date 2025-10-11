from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

_REGISTRY_PATH = Path(__file__).resolve().parent / "atlas_registry.json"
_MISSING = object()


def _load_registry() -> Dict[str, Any]:
    with _REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


class _AtlasRegistry:
    def __init__(self) -> None:
        raw = _load_registry()
        self._atlas = raw["atlas"]
        self._profiles = self._atlas["profile_details"]
        self._aliases = self._atlas["aliases"]
        # Allow direct id lookup and short name aliasing.
        for summary in self._atlas.get("profiles", []):
            self._aliases.setdefault(summary["name"], summary["id"])
        for profile_id in self._profiles:
            self._aliases.setdefault(profile_id, profile_id)

    def latest(self) -> str:
        return self._atlas["latest"]

    def profiles(self) -> Iterable[Dict[str, Any]]:
        return list(self._atlas.get("profiles", []))

    def resolve_profile_id(self, name_or_id: str) -> str:
        if name_or_id in self._profiles:
            return name_or_id
        resolved = self._aliases.get(name_or_id)
        if resolved in self._profiles:
            return resolved
        # Fallback to lower-case for ASCII aliases.
        lower_key = name_or_id.lower()
        for key, value in self._aliases.items():
            if isinstance(key, str) and key.lower() == lower_key:
                return value
        raise KeyError(f"Unknown ATLAS profile identifier: {name_or_id}")

    def profile(self, name_or_id: str) -> Dict[str, Any]:
        resolved = self.resolve_profile_id(name_or_id)
        return deepcopy(self._profiles[resolved])

    def migration_map(self) -> Dict[str, Any]:
        return deepcopy(self._atlas.get("migration_map", {}))

    def migrate(self, payload: Any) -> Any:
        if isinstance(payload, str):
            obj = json.loads(payload)
        else:
            obj = deepcopy(payload)
        rules = self._atlas.get("migration_map", {}).get("rules", [])
        for rule in rules:
            if "from" in rule and "to" in rule:
                value = _get_path(obj, rule["from"])
                if value is not _MISSING:
                    _set_path(obj, rule["to"], value)
                    if rule["from"] != rule["to"]:
                        _delete_path(obj, rule["from"])
            if "defaults" in rule:
                for path, value in rule["defaults"].items():
                    if _get_path(obj, path) is _MISSING:
                        _set_path(obj, path, value)
        return obj


_REGISTRY_CACHE: Optional[_AtlasRegistry] = None


def _registry() -> _AtlasRegistry:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        _REGISTRY_CACHE = _AtlasRegistry()
    return _REGISTRY_CACHE


def get(key: str, identifier: Optional[str] = None) -> Any:
    registry = _registry()
    if key == "atlas.latest":
        return registry.latest()
    if key == "atlas.profiles":
        return registry.profiles()
    if key == "atlas.profile":
        if identifier is None:
            raise ValueError("identifier argument required for atlas.profile")
        return registry.profile(identifier)
    raise KeyError(f"Unsupported codex.get key: {key}")


def migrate_thresholds(json_old: Any) -> Any:
    return _registry().migrate(json_old)


def _get_path(obj: Any, dotted: str) -> Any:
    parts = dotted.split(".")
    cur = obj
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def _set_path(obj: Dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = obj
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _delete_path(obj: Dict[str, Any], dotted: str) -> None:
    parts = dotted.split(".")
    cur = obj
    for part in parts[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            return
        cur = cur[part]
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)


__all__ = ["get", "migrate_thresholds"]
