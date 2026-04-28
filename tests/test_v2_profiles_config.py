from __future__ import annotations

import json
from pathlib import Path


def test_profile_registry_contains_required_profiles() -> None:
    registry_path = Path("src/profiles/registry.json")
    assert registry_path.exists()

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", {})
    assert isinstance(profiles, dict)

    required = {
        "urban_introspective",
        "classical_restraint",
        "uplift_pop",
        "club_dance",
        "ambient_meditation",
    }
    assert required.issubset(set(profiles.keys()))


def test_profile_registry_fields_for_urban_introspective() -> None:
    payload = json.loads(Path("src/profiles/registry.json").read_text(encoding="utf-8"))
    profile = payload["profiles"]["urban_introspective"]

    assert profile["display_name"]
    assert isinstance(profile["typical_genres"], list)
    assert isinstance(profile["typical_moods"], list)
    assert profile["craft_focus"]
    assert "R15_concrete_density" in profile
    assert "R16_profile_forbidden" in profile
    assert "R17_first_person_ratio_max" in profile
    assert "narrative_style" in profile
    assert "variant_differentiation" in profile
    assert "chorus_repetition_allowed" in profile
    assert "abstraction_tolerance" in profile


def test_profile_registry_has_registry_metadata() -> None:
    payload = json.loads(Path("src/profiles/registry.json").read_text(encoding="utf-8"))
    assert payload.get("version") == "profile-registry/v1.0"
    assert isinstance(payload.get("extensible"), str)


def test_global_rules_contains_global_always_forbidden() -> None:
    rules_path = Path("src/profiles/global_rules.json")
    assert rules_path.exists()
    payload = json.loads(rules_path.read_text(encoding="utf-8"))

    forbidden = payload.get("global_always_forbidden")
    assert isinstance(forbidden, list)
    assert len(forbidden) >= 10
    assert isinstance(payload.get("规则"), str)
