from __future__ import annotations

from src.audio_intake import _infer_groove_level, _parse_bpm_text


def test_parse_bpm_text_extracts_number_in_range() -> None:
    assert _parse_bpm_text("约 102 BPM") == 102


def test_parse_bpm_text_rejects_out_of_range() -> None:
    assert _parse_bpm_text("55") is None


def test_infer_groove_level_mid_from_keywords() -> None:
    level, reason = _infer_groove_level(
        filename="HYBS groove demo",
        raw_intent="做一首慵懒律动",
        genre_hint="indie",
        mood_hint="微醺",
    )
    assert level in {"mid", "high"}
    assert "keyword" in reason
