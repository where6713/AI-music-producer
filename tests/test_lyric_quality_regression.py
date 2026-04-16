"""Golden fixture regression checks for lyric quality metrics."""

from __future__ import annotations

import json
from pathlib import Path


def test_golden_fixture_quality_metrics() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "golden_lyrics.json"
    assert fixture_path.exists()

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    sections = payload.get("sections", [])
    assert isinstance(sections, list)
    assert len(sections) == 6

    quality_gate = payload.get("quality_gate", {})
    assert isinstance(quality_gate, dict)
    assert quality_gate.get("pass") is True

    stats = payload.get("stats", {})
    assert isinstance(stats, dict)
    cliche_density = float(stats.get("cliche_density_pct", 0.0))
    tone_collision = float(stats.get("tone_collision_pct", 0.0))
    line_length_violation_count = int(stats.get("line_length_violation_count", 0))

    assert cliche_density <= 5.0 * 1.2
    assert tone_collision <= 15.0
    assert line_length_violation_count == 0
