from __future__ import annotations

import codex


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
