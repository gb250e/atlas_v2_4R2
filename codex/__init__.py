from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


# Repository layout
_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _REPO_ROOT / "configs" / "ATLAS_thresholds_v2.4R2.json"
_VERSION_PATH = _REPO_ROOT / "VERSION"
_LATEST_PATH = _REPO_ROOT / "docs" / "LATEST.md"
_META_PATH = _REPO_ROOT / "codex.meta.json"


_PLACEHOLDER_VALUES: Dict[str, set] = {
    "epsilon_caus": {"from_anchor"},
    "v_LR": {"from_anchor"},
    "anchor_metric.scales": {"from_anchor_or_units"},
    "windows.tau": {"specify in units"},
    "triage.roc.external_set_doi": {"TBD"},
}

_MANDATORY_TRUE_PATHS = [
    "temporal_gauge.tg_independence.log_required",
    "triage.roc.external_validation_required",
    "cost_reporting.required",
]

_FORBIDDEN_ROOT_KEYS = {"schema_migration", "aliases", "deprecated"}
_FORBIDDEN_EXACT_PATHS = {
    "temporal_gauge.tg_independence.log_required",
    "triage.roc.external_validation_required",
    "cost_reporting.required",
    "provenance.require_external_anchor",
}
_APPEND_ONLY_LIST_PATHS = {
    "log_format.fields",
    "triage.report.metrics",
}
_ALLOWED_KMS_POLICIES = {"geometric_only", "strict", "disabled"}


_FIGURE_SET = [
    "F1_dashboard",
    "F2_tg_ind",
    "F3_delta_map",
    "F4_nmod_stability",
    "F5_hlb_budget",
    "F6_roc",
    "F7_scope_gate",
    "F8_kms",
    "F9_cost",
    "F10_determinism",
]

_FIGURE_OUTPUTS = [f"figures/{fig}/{fig}.pdf" for fig in _FIGURE_SET]


def _normalize_stage_name(stage: str) -> str:
    stage_lower = stage.lower()
    if stage_lower.startswith("sg"):
        return "sg"
    if stage_lower == "cost_reporting":
        return "cost"
    return stage_lower


def _read_stage_log(path: Path) -> Tuple[list, Dict[str, Any]]:
    if not path.exists():
        raise AtlasFiguresError(f"Stage log not found: {path}")
    records = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise AtlasFiguresError(f"Invalid JSON on line {lineno}: {exc}") from exc
            records.append(obj)
    if not records:
        raise AtlasFiguresError("Stage log is empty.")

    manifest_info = {
        "commits": {rec.get("commit") for rec in records if rec.get("commit")},
        "seeds": {rec.get("seed") for rec in records if rec.get("seed") is not None},
        "thresholds_sha256": {rec.get("thresholds_sha256") for rec in records if rec.get("thresholds_sha256")},
    }
    return records, manifest_info


def _validate_figures(records: list, entry: ProfileEntry) -> Tuple[list, list, Dict[str, Any]]:
    errors: list = []
    warnings: list = []

    stage_buckets: Dict[str, list] = {k: [] for k in [
        "delta",
        "nmod",
        "htop",
        "roc",
        "tg_ind",
        "sg",
        "kms",
        "cost",
        "determinism",
    ]}

    for rec in records:
        stage = rec.get("stage")
        if not stage:
            continue
        normalized = _normalize_stage_name(stage)
        if normalized in stage_buckets:
            stage_buckets[normalized].append(rec)

    tg_records = stage_buckets["tg_ind"]
    if not tg_records:
        errors.append("F2_tg_ind: missing tg_ind stage entries.")
    else:
        if not any(
            isinstance(rec.get("aux"), dict)
            and rec["aux"].get("frobenius_resid") is not None
            and rec["aux"].get("orthogonality_resid") is not None
            for rec in tg_records
        ):
            errors.append("F2_tg_ind: tg_ind entries lack frobenius_resid and orthogonality_resid.")

    if not stage_buckets["delta"] or not stage_buckets["nmod"] or not stage_buckets["htop"]:
        errors.append("F1_dashboard: requires delta, nmod, and htop stages.")
    else:
        for rec in stage_buckets["delta"]:
            aux = rec.get("aux", {})
            if "delta_chart" not in aux:
                errors.append("F1_dashboard: delta stage missing aux.delta_chart.")
                break
        for rec in stage_buckets["nmod"]:
            aux = rec.get("aux", {})
            if "abs_delta_N" not in aux:
                errors.append("F1_dashboard: nmod stage missing aux.abs_delta_N.")
                break
        for rec in stage_buckets["htop"]:
            aux = rec.get("aux", {})
            eb = aux.get("error_budget", {})
            if not all(k in eb for k in ("E_disc", "E_loc", "E_resp")):
                errors.append("F1_dashboard: htop error_budget incomplete (needs E_disc, E_loc, E_resp).")
                break

    if any("chart_coords" not in rec.get("aux", {}) for rec in stage_buckets["delta"]):
        errors.append("F3_delta_map: delta stage requires aux.chart_coords for heatmap.")

    for rec in stage_buckets["nmod"]:
        aux = rec.get("aux", {})
        guard = aux.get("guard_metrics", {})
        thresholds = aux.get("guard_thresholds", {})
        if not guard or "order_agreement_tol" not in thresholds:
            errors.append("F4_nmod_stability: missing guard metrics or thresholds.")
            break

    if not stage_buckets["htop"]:
        errors.append("F5_hlb_budget: requires htop stage.")

    if not stage_buckets["roc"]:
        errors.append("F6_roc: requires roc stage entries.")
    profile_roc_doi = _get_path(entry.profile, "triage.roc.external_set_doi")
    if entry.state == "READY" and profile_roc_doi in {"TBD", None}:
        warnings.append("Profile READY but triage.roc.external_set_doi is placeholder.")

    if not stage_buckets["sg"]:
        warnings.append("F7_scope_gate: no SG stage entries found.")

    if not stage_buckets["kms"]:
        warnings.append("F8_kms: no kms stage entries.")
    else:
        for rec in stage_buckets["kms"]:
            aux = rec.get("aux", {})
            policy = aux.get("policy")
            if policy not in _ALLOWED_KMS_POLICIES:
                errors.append("F8_kms: kms policy must be geometric_only or stricter.")
                break

    if not stage_buckets["cost"]:
        warnings.append("F9_cost: no cost stage entries.")
    else:
        required_cost_fields = {"wall_seconds", "cpu_seconds", "max_rss_kb"}
        if not any(required_cost_fields.issubset(rec.get("aux", {}).keys()) for rec in stage_buckets["cost"]):
            errors.append("F9_cost: cost stage missing required fields (wall_seconds, cpu_seconds, max_rss_kb).")

    if not stage_buckets["determinism"]:
        errors.append("F10_determinism: requires determinism stage entries.")
    else:
        required_det_fields = {"rng", "seed", "dtype", "bit_generator"}
        for rec in stage_buckets["determinism"]:
            aux = rec.get("aux", {})
            if not required_det_fields.issubset(aux.keys()):
                errors.append("F10_determinism: determinism stage missing rng/seed/dtype/bit_generator.")
                break

    log_info = {"stages": stage_buckets}
    return errors, warnings, log_info


def _build_plan_dict(entry: ProfileEntry, log_path: Path, warnings: list) -> Dict[str, Any]:
    return {
        "profile_id": entry.id,
        "effective_sha256": entry.effective_sha256,
        "state": entry.state,
        "compliance": entry.compliance,
        "missing_placeholders": list(entry.missing_placeholders),
        "inputs": {"log_jsonl": str(log_path)},
        "outputs": list(_FIGURE_OUTPUTS),
        "steps": [
            {"fig": "F1_dashboard", "from": ["delta/*", "nmod/*", "htop/*"]},
            {"fig": "F2_tg_ind", "from": ["tg_ind/*"]},
            {"fig": "F3_delta_map", "from": ["delta/*"]},
            {"fig": "F4_nmod_stability", "from": ["nmod/*"]},
            {"fig": "F5_hlb_budget", "from": ["htop/*"]},
            {"fig": "F6_roc", "from": ["roc/*"]},
            {"fig": "F7_scope_gate", "from": ["sg/*"]},
            {"fig": "F8_kms", "from": ["kms/*"]},
            {"fig": "F9_cost", "from": ["cost/*"]},
            {"fig": "F10_determinism", "from": ["determinism/*"]},
        ],
        "manifest": "figures/manifest.json",
        "warnings": warnings,
    }


def plan(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if action != "atlas.figures.build":
        raise KeyError(f"Unsupported plan action: {action}")
    ctx = _context()
    log_jsonl = params.get("log_jsonl")
    if not log_jsonl:
        raise AtlasFiguresError("Missing log_jsonl parameter.")
    log_path = Path(log_jsonl)
    profile_name = params.get("profile")
    overrides = params.get("overrides")
    config = params.get("config")
    env = params.get("env")

    entry = ctx.select_profile(profile_name, overrides, config, env)
    if entry.compliance != "CONFORMANT":
        raise AtlasFiguresError(f"Profile {entry.id} is NON_CONFORMANT.")

    records, manifest_info = _read_stage_log(log_path)

    warnings = []
    if manifest_info["thresholds_sha256"] and (
        entry.thresholds_sha256 not in manifest_info["thresholds_sha256"]
    ):
        warnings.append("Stage log thresholds_sha256 mismatch with current thresholds file.")

    errors, figure_warnings, _ = _validate_figures(records, entry)
    warnings.extend(figure_warnings)
    if errors:
        raise AtlasFiguresError("; ".join(errors))

    return _build_plan_dict(entry, log_path, warnings)


def validate(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if action != "atlas.figures.inputs":
        raise KeyError(f"Unsupported validate action: {action}")
    result = {"ok": False, "errors": [], "warnings": []}
    try:
        ctx = _context()
        log_jsonl = params.get("log_jsonl")
        if not log_jsonl:
            result["errors"].append("Missing log_jsonl parameter.")
            return result
        log_path = Path(log_jsonl)
        profile_name = params.get("profile")
        overrides = params.get("overrides")
        config = params.get("config")
        env = params.get("env")
        entry = ctx.select_profile(profile_name, overrides, config, env)
        if entry.compliance != "CONFORMANT":
            result["errors"].append(f"Profile {entry.id} is NON_CONFORMANT.")
            return result
        records, manifest_info = _read_stage_log(log_path)
    except AtlasFiguresError as exc:
        result["errors"].append(str(exc))
        return result
    except Exception as exc:  # pragma: no cover
        result["errors"].append(str(exc))
        return result

    if manifest_info["thresholds_sha256"] and (
        entry.thresholds_sha256 not in manifest_info["thresholds_sha256"]
    ):
        result["warnings"].append("Stage log thresholds_sha256 mismatch with current thresholds file.")
    errors, figure_warnings, _ = _validate_figures(records, entry)
    result["errors"].extend(errors)
    result["warnings"].extend(figure_warnings)
    result["ok"] = not result["errors"]
    return result

_ALIASES = {
    "default": "atlas:profile:v2.4R2:default",
    "標準": "atlas:profile:v2.4R2:default",
    "reviewer": "atlas:profile:v2.4R2:reviewer",
    "レビューア": "atlas:profile:v2.4R2:reviewer",
    "student": "atlas:profile:v2.4R2:student",
    "学生": "atlas:profile:v2.4R2:student",
    "benchmark": "atlas:profile:v2.4R2:benchmark",
    "ベンチマーク": "atlas:profile:v2.4R2:benchmark",
    "hpc": "atlas:profile:v2.4R2:hpc",
    "HPC": "atlas:profile:v2.4R2:hpc",
    "ハイパフォーマンス": "atlas:profile:v2.4R2:hpc",
}


class AtlasRegistryError(ValueError):
    """Raised when dynamic profile construction violates normative requirements."""


class AtlasFiguresError(AtlasRegistryError):
    """Raised when figure validation fails."""


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _hash_json(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


def _get_path(data: Dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_path(data: Dict[str, Any], dotted: str, value: Any) -> None:
    current = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        nxt = current.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            current[part] = nxt
        current = nxt
    current[parts[-1]] = value


def _delete_path(data: Dict[str, Any], dotted: str) -> None:
    current = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        nxt = current.get(part)
        if not isinstance(nxt, dict):
            return
        current = nxt
    if isinstance(current, dict):
        current.pop(parts[-1], None)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    stack = [(merged, override)]
    while stack:
        target, src = stack.pop()
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                stack.append((target[key], value))
            else:
                target[key] = deepcopy(value)
    return merged


def _ensure_list_append_only(path: str, base_list: Iterable[Any], candidate: Any) -> None:
    if candidate is None:
        return
    if not isinstance(candidate, list):
        raise AtlasRegistryError(f"Overrides must provide list for {path}")
    missing = [item for item in base_list if item not in candidate]
    if missing:
        raise AtlasRegistryError(
            f"Overrides may not remove entries from {path}: missing {missing}"
        )


def _detect_forbidden_paths(data: Dict[str, Any], prefix: str = "") -> Iterable[str]:
    offenders = []
    for key, value in data.items():
        current_path = f"{prefix}.{key}" if prefix else key
        if key in _FORBIDDEN_ROOT_KEYS and (prefix == "" or current_path.startswith(key)):
            offenders.append(current_path)
        if current_path in _FORBIDDEN_EXACT_PATHS:
            offenders.append(current_path)
        if isinstance(value, dict):
            offenders.extend(_detect_forbidden_paths(value, current_path))
    return offenders


@dataclass
class ProfileEntry:
    id: str
    name: str
    version: Optional[str]
    system_class: Optional[str]
    canonical_path: str
    thresholds_sha256: str
    profile: Dict[str, Any]
    state: str
    missing_placeholders: list
    compliance: str
    built_in: bool
    effective_sha256: str
    overrides_sha256: Optional[str] = None
    migration_applied: bool = False
    migration_summary: Dict[str, Any] = field(default_factory=lambda: {"moved": [], "defaults": []})


class AtlasContext:
    def __init__(self) -> None:
        self._dynamic_profiles: Dict[str, ProfileEntry] = {}
        self._override_store: Dict[str, Dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        self._config = _read_json(_CONFIG_PATH)
        self._version = _VERSION_PATH.read_text(encoding="utf-8").strip()
        latest_lines = _LATEST_PATH.read_text(encoding="utf-8").splitlines()
        first_bullet = next((line for line in latest_lines if line.strip().startswith("-")), "")
        if self._version != "2.4R2":
            raise AtlasRegistryError("VERSION mismatch: expected 2.4R2")
        if "Current latest" not in first_bullet or "v2.4R2" not in first_bullet:
            raise AtlasRegistryError("docs/LATEST.md must advertise v2.4R2")

        self.thresholds_sha256 = sha256(_CONFIG_PATH.read_bytes()).hexdigest()
        self.canonical_path = _relative_path(_CONFIG_PATH)
        self.migration_map = deepcopy(self._config["default"]["schema_migration"])

        self.aliases: Dict[str, str] = dict(_ALIASES)
        self._builtins: Dict[str, ProfileEntry] = {}
        profiles_cfg = self._config.get("profiles", {})
        for name, profile_cfg in profiles_cfg.items():
            entry = self._build_profile(name, profile_cfg, built_in=True)
            self._builtins[entry.id] = entry
            self.aliases.setdefault(name, entry.id)
            self.aliases.setdefault(entry.id, entry.id)

        self._default_id = "atlas:profile:v2.4R2:default"
        self._default_profile = deepcopy(self._builtins[self._default_id].profile)
        self._append_only_references = {
            path: deepcopy(_get_path(self._default_profile, path)) or []
            for path in _APPEND_ONLY_LIST_PATHS
        }

        self._dynamic_profiles.clear()

        meta = _read_json(_META_PATH) if _META_PATH.exists() else {}
        thresholds_meta = meta.get("atlas", {}).get("thresholds_sha256")
        self.health = {
            "version_file": self._version == "2.4R2",
            "latest_md": "Current latest" in first_bullet and "v2.4R2" in first_bullet,
            "thresholds_meta_match": thresholds_meta == self.thresholds_sha256 if thresholds_meta else True,
            "warnings": [] if thresholds_meta in (None, self.thresholds_sha256) else [
                {
                    "warning": "thresholds_sha256 mismatch",
                    "registry": self.thresholds_sha256,
                    "meta": thresholds_meta,
                }
            ],
        }

    # ------------------------------------------------------------------ helpers
    def _build_profile(self, name: str, spec: Dict[str, Any], *, built_in: bool) -> ProfileEntry:
        profile_copy = deepcopy(spec)
        state, missing = self._compute_state(profile_copy)
        compliance = self._compute_compliance(profile_copy, strict=built_in)
        profile_id = f"atlas:profile:v2.4R2:{name}"
        return ProfileEntry(
            id=profile_id,
            name=name,
            version=profile_copy.get("version"),
            system_class=profile_copy.get("system_class"),
            canonical_path=self.canonical_path,
            thresholds_sha256=self.thresholds_sha256,
            profile=profile_copy,
            state=state,
            missing_placeholders=missing,
            compliance=compliance,
            built_in=built_in,
            effective_sha256=_hash_json(profile_copy),
        )

    def _compute_state(self, profile: Dict[str, Any]) -> Tuple[str, list]:
        missing = [
            path
            for path, placeholder_values in _PLACEHOLDER_VALUES.items()
            if any(_get_path(profile, path) == placeholder for placeholder in placeholder_values)
        ]
        return ("READY" if not missing else "PROVISIONAL", missing)

    def _compute_compliance(self, profile: Dict[str, Any], *, strict: bool) -> str:
        offenders = [
            path for path in _MANDATORY_TRUE_PATHS if _get_path(profile, path) is not True
        ]
        if offenders and strict:
            raise AtlasRegistryError(
                f"Profile violates mandatory requirements: {', '.join(offenders)}"
            )
        return "CONFORMANT" if not offenders else "NON_CONFORMANT"

    def _resolve_identifier(self, key: str) -> Optional[str]:
        if key in self._builtins:
            return key
        if key in self._dynamic_profiles:
            return key
        if key in self.aliases:
            return self.aliases[key]
        lowered = key.lower()
        for alias_key, profile_id in self.aliases.items():
            if isinstance(alias_key, str) and alias_key.lower() == lowered:
                return profile_id
        return None

    def _apply_migration(self, overrides: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        migrated = deepcopy(overrides)
        summary = {"moved": [], "defaults": []}
        for rule in self.migration_map.get("rules", []):
            if "from" in rule and "to" in rule:
                value = _get_path(migrated, rule["from"])
                if value is not None:
                    _set_path(migrated, rule["to"], value)
                    if rule["from"] != rule["to"]:
                        _delete_path(migrated, rule["from"])
                        summary["moved"].append({"from": rule["from"], "to": rule["to"]})
            if "defaults" in rule:
                for path, value in rule["defaults"].items():
                    if _get_path(migrated, path) is None:
                        _set_path(migrated, path, value)
                        summary["defaults"].append(path)
        summary["moved"] = summary["moved"] or []
        summary["defaults"] = summary["defaults"] or []
        return migrated, summary

    def _validate_overrides(self, overrides: Dict[str, Any]) -> None:
        offenders = list(_detect_forbidden_paths(overrides))
        if offenders:
            raise AtlasRegistryError(
                f"Overrides touch forbidden paths: {', '.join(sorted(set(offenders)))}"
            )

    def _validate_append_lists(self, merged: Dict[str, Any], overrides: Dict[str, Any]) -> None:
        for path in _APPEND_ONLY_LIST_PATHS:
            override_list = _get_path(overrides, path)
            if override_list is None:
                continue
            base_list = self._append_only_references.get(path, [])
            candidate = _get_path(merged, path)
            _ensure_list_append_only(path, base_list, candidate)

    def _validate_kms_policy(self, merged: Dict[str, Any]) -> None:
        policy = _get_path(merged, "kms.policy")
        if policy is None:
            return
        if policy not in _ALLOWED_KMS_POLICIES:
            raise AtlasRegistryError(
                f"kms.policy must remain in {_ALLOWED_KMS_POLICIES}, got '{policy}'"
            )

    def _normalise_overrides(self, overrides: Optional[Any]) -> Dict[str, Any]:
        if overrides is None:
            return {}
        if isinstance(overrides, str):
            return json.loads(overrides)
        if isinstance(overrides, dict):
            return deepcopy(overrides)
        raise AtlasRegistryError("Overrides must be dict or JSON string")

    # ----------------------------------------------------------------- exposed
    def latest(self) -> str:
        return "2.4R2"

    def profiles_summary(self) -> Iterable[Dict[str, Any]]:
        entries = list(self._builtins.values()) + list(self._dynamic_profiles.values())
        summaries = [
            {
                "id": entry.id,
                "name": entry.name,
                "state": entry.state,
                "compliance": entry.compliance,
                "thresholds_sha256": entry.thresholds_sha256,
                **(
                    {"effective_sha256": entry.effective_sha256}
                    if not entry.built_in
                    else {}
                ),
            }
            for entry in entries
        ]
        summaries.sort(key=lambda item: item["id"])
        return summaries

    def get_entry(self, identifier: str) -> ProfileEntry:
        resolved = self._resolve_identifier(identifier)
        if not resolved:
            raise KeyError(f"Unknown ATLAS profile '{identifier}'")
        if resolved in self._builtins:
            return self._builtins[resolved]
        if resolved in self._dynamic_profiles:
            return self._dynamic_profiles[resolved]
        raise KeyError(f"Profile '{identifier}' not registered")

    def migrate(self, payload: Any) -> Any:
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = deepcopy(payload)
        migrated, _ = self._apply_migration(data)
        return migrated

    def store_override(self, key: str, value: Dict[str, Any]) -> None:
        self._override_store[key] = deepcopy(value)

    def clear_store(self) -> None:
        self._override_store.clear()

    def reset_dynamic_profiles(self) -> None:
        self._dynamic_profiles.clear()

    def select_profile(
        self,
        name: Optional[str],
        overrides: Optional[Any],
        config: Optional[Dict[str, Any]],
        env: Optional[Dict[str, str]],
    ) -> ProfileEntry:
        resolved_name = name
        env_map = env or os.environ

        if not resolved_name:
            if env_map.get("ATLAS_PROFILE"):
                resolved_name = env_map["ATLAS_PROFILE"]
            elif config and config.get("profile"):
                resolved_name = config["profile"]

        override_patch = overrides
        if resolved_name and override_patch is None:
            store_key = f"atlas.profile_overrides.{resolved_name}"
            if store_key in self._override_store:
                override_patch = self._override_store[store_key]

        override_dict = self._normalise_overrides(override_patch)

        if not resolved_name:
            return self._builtins[self._default_id]

        resolved_id = self._resolve_identifier(resolved_name)
        if resolved_id and override_dict:
            raise AtlasRegistryError(
                f"Profile '{resolved_name}' exists; supply a new name for overrides."
            )
        if resolved_id:
            return self.get_entry(resolved_id)

        return self._create_dynamic(resolved_name, override_dict)

    def _create_dynamic(self, name: str, overrides: Dict[str, Any]) -> ProfileEntry:
        migrated, summary = self._apply_migration(overrides)
        self._validate_overrides(migrated)
        merged = _deep_merge(self._default_profile, migrated)
        self._validate_append_lists(merged, migrated)
        self._validate_kms_policy(merged)
        state, missing = self._compute_state(merged)
        compliance = self._compute_compliance(merged, strict=True)
        profile_id = f"atlas:profile:v2.4R2:dynamic:{name}"
        entry = ProfileEntry(
            id=profile_id,
            name=name,
            version=merged.get("version", self._default_profile.get("version")),
            system_class=merged.get("system_class", self._default_profile.get("system_class")),
            canonical_path=self.canonical_path,
            thresholds_sha256=self.thresholds_sha256,
            profile=merged,
            state=state,
            missing_placeholders=missing,
            compliance=compliance,
            built_in=False,
            effective_sha256=_hash_json(merged),
            overrides_sha256=_hash_json(overrides),
            migration_applied=bool(summary["moved"] or summary["defaults"]),
            migration_summary=summary,
        )
        self._dynamic_profiles[profile_id] = entry
        self.aliases[name] = profile_id
        return entry


_CONTEXT: Optional[AtlasContext] = None


def _context() -> AtlasContext:
    global _CONTEXT
    if _CONTEXT is None:
        _CONTEXT = AtlasContext()
    return _CONTEXT


def get(key: str, identifier: Optional[str] = None) -> Any:
    ctx = _context()
    if key == "atlas.latest":
        return ctx.latest()
    if key in ("atlas.profiles", "atlas.figures.profiles"):
        return deepcopy(list(ctx.profiles_summary()))
    if key == "atlas.profile":
        if identifier is None:
            raise ValueError("identifier is required for atlas.profile")
        entry = ctx.get_entry(identifier)
        return _expose_entry(entry)
    if key == "atlas.figures.figure_set":
        return list(_FIGURE_SET)
    raise KeyError(f"Unsupported codex.get key: {key}")


def select_profile(
    name: Optional[str] = None,
    overrides: Optional[Any] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    entry = _context().select_profile(name, overrides, config, env)
    return _expose_entry(entry)


def migrate_thresholds(payload: Any) -> Any:
    return _context().migrate(payload)


def store(key: str, value: Dict[str, Any]) -> None:
    if not key.startswith("atlas.profile_overrides."):
        raise ValueError("Only atlas.profile_overrides.* keys are supported")
    _context().store_override(key, value)


def clear_store() -> None:
    _context().clear_store()


def reset_dynamic_profiles() -> None:
    _context().reset_dynamic_profiles()


def reload() -> None:
    _context().reload()


def _expose_entry(entry: ProfileEntry) -> Dict[str, Any]:
    exposed = {
        "id": entry.id,
        "name": entry.name,
        "version": entry.version,
        "system_class": entry.system_class,
        "canonical_path": entry.canonical_path,
        "thresholds_sha256": entry.thresholds_sha256,
        "profile": deepcopy(entry.profile),
        "state": entry.state,
        "missing_placeholders": list(entry.missing_placeholders),
        "compliance": entry.compliance,
        "built_in": entry.built_in,
        "effective_sha256": entry.effective_sha256,
    }
    if entry.overrides_sha256 is not None:
        exposed["overrides_sha256"] = entry.overrides_sha256
        exposed["migration_applied"] = entry.migration_applied
        exposed["migration_summary"] = deepcopy(entry.migration_summary)
    return exposed


__all__ = [
    "get",
    "select_profile",
    "migrate_thresholds",
    "store",
    "clear_store",
    "reset_dynamic_profiles",
    "reload",
    "plan",
    "validate",
    "AtlasRegistryError",
    "AtlasFiguresError",
]
