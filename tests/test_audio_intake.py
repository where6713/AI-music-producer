from __future__ import annotations

from src.audio_intake import _parse_bpm_text


def test_parse_bpm_text_extracts_number_in_range() -> None:
    assert _parse_bpm_text("约 102 BPM") == 102


def test_parse_bpm_text_rejects_out_of_range() -> None:
    assert _parse_bpm_text("55") is None
