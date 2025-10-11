from __future__ import annotations

import pytest

import codex


@pytest.fixture(autouse=True)
def _reset_codex_state():
    codex.reset_dynamic_profiles()
    codex.clear_store()
    codex.reload()
    yield


def test_codex_get_latest():
    assert codex.get("atlas.latest") == "2.4R2"


def test_codex_profiles_summary():
    profiles = codex.get("atlas.profiles")
    assert isinstance(profiles, list)
    assert len(profiles) == 5
    ids = {p["id"] for p in profiles}
    assert "atlas:profile:v2.4R2:default" in ids


def test_codex_profile_alias_resolution():
    profile = codex.get("atlas.profile", "レビューア")
    assert profile["id"] == "atlas:profile:v2.4R2:reviewer"
    assert "missing_placeholders" in profile
    assert "profile" in profile


def test_codex_migration_defaults_and_moves():
    legacy = {
        "epsilon": 0.1,
        "triage": {
            "report": {}
        }
    }
    migrated = codex.migrate_thresholds(legacy)
    assert migrated["N_mod"]["regularization_epsilon"] == 0.1
    assert "epsilon" not in migrated
    assert migrated["triage"]["report"]["required"] is True


def test_dynamic_profile_ready_state():
    overrides = {
        "epsilon_caus": 0.02,
        "v_LR": 0.55,
        "anchor_metric": {"scales": [1.0, 1.0, 1.0]},
        "windows": {"tau": 0.25},
        "triage": {"roc": {"external_set_doi": "10.1234/example"}},
    }
    entry = codex.select_profile("custom", overrides=overrides)
    assert entry["id"] == "atlas:profile:v2.4R2:dynamic:custom"
    assert entry["state"] == "READY"
    fetched = codex.get("atlas.profile", "custom")
    assert fetched["id"] == entry["id"]
    assert fetched["profile"]["epsilon_caus"] == 0.02
    summaries = codex.get("atlas.profiles")
    assert any(item["id"] == entry["id"] for item in summaries)


def test_dynamic_profile_rejects_normative_override():
    with pytest.raises(codex.AtlasRegistryError):
        codex.select_profile(
            "noncompliant",
            overrides={"cost_reporting": {"required": False}},
        )


def test_append_only_fields_enforced():
    overrides = {
        "log_format": {"fields": []},
        "epsilon_caus": 0.02,
        "v_LR": 0.55,
        "anchor_metric": {"scales": [1.0, 1.0, 1.0]},
        "windows": {"tau": 0.2},
        "triage": {"roc": {"external_set_doi": "10.1/abc"}},
    }
    with pytest.raises(codex.AtlasRegistryError):
        codex.select_profile("trim", overrides=overrides)


def test_store_overrides_used_when_selecting():
    overrides = {
        "epsilon_caus": 0.02,
        "v_LR": 0.44,
        "anchor_metric": {"scales": [1.0, 2.0]},
        "windows": {"tau": 0.3},
        "triage": {"roc": {"external_set_doi": "10.55/xyz"}},
    }
    codex.store("atlas.profile_overrides.alt", overrides)
    entry = codex.select_profile("alt")
    assert entry["id"] == "atlas:profile:v2.4R2:dynamic:alt"
    assert entry["state"] == "READY"
