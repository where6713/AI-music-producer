from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.v2.compose import compose
from src.v2.distill_emotion import distill_emotion
from src.v2.main import run_v2
from src.v2.perceive_music import perceive_music
from src.v2.select_corpus import select_corpus
from src.v2.self_review import self_review


def test_perceive_music_returns_5_keys() -> None:
    out = perceive_music("深夜慢一点，想写内省情绪", ref_audio="demo.wav")
    assert set(out.keys()) >= {"genre_guess", "bpm_range", "vibe", "audio_hint", "intent"}
    assert out["audio_hint"] == ".wav"


def test_distill_emotion_central_image_length() -> None:
    portrait = {"texture": "indie lazy groove"}
    out = distill_emotion("失恋后一个人回家", portrait)
    assert out["valence"] == "negative"
    assert out["arc"] == "descend-then-breathe"
    assert len(out["central_image"]) <= 20


def test_select_corpus_recall_size_and_golden_anchor(tmp_path: Path) -> None:
    rows = [
        {"id": "corpus/golden_dozen/demo.txt", "title": "锚点", "summary_50chars": "indie groove city", "emotion_tags": ["孤独"], "char_count": 100},
        {"id": "a", "title": "夜色", "summary_50chars": "urban introspective city", "emotion_tags": ["孤独"], "char_count": 100},
        {"id": "b", "title": "晴天", "summary_50chars": "bright pop youth", "emotion_tags": ["青春"], "char_count": 120},
    ]
    index = tmp_path / "index.json"
    index.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    out = select_corpus(index, {"texture": "urban introspective", "tempo": "slow", "energy": "low"}, limit=118)
    assert 1 <= len(out) <= 118
    assert any("golden_dozen" in str(x.get("id", "")) for x in out)


def test_compose_pass1_id_grounding() -> None:
    pool = [{"id": "x"}, {"id": "y"}]
    draft = compose(
        {"texture": "indie lazy groove"},
        {"arc": "hold-and-release", "central_image": "street lamp"},
        golden_refs=[],
        corpus_pool=pool,
    )
    assert set(draft["selected_ids"]) <= {"x", "y"}


def test_self_review_preserves_section_count() -> None:
    draft = compose(
        {"texture": "indie lazy groove"},
        {"arc": "hold-and-release", "central_image": "street lamp"},
        golden_refs=[],
        corpus_pool=[{"id": "x"}],
    )
    sections_before = draft["lyrics"].count("[")
    reviewed = self_review(draft)
    sections_after = reviewed["lyrics"].count("[")
    assert sections_before == sections_after
    assert isinstance(reviewed["review_notes"], str)


def test_run_v2_end_to_end_with_local_index(tmp_path: Path) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("needs real LLM")
    rows = [
        {
            "id": "corpus/golden_dozen/demo.txt",
            "title": "demo",
            "author": "tester",
            "first_line": "line",
            "summary_50chars": "indie groove city night",
            "emotion_tags": ["内省", "夜"],
            "char_count": 120,
        }
    ]
    index = tmp_path / "index.json"
    index.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    out = run_v2("深夜想放下", index_path=str(index))
    assert isinstance(out.get("lyrics"), str)
    assert isinstance(out.get("style"), str)
    assert isinstance(out.get("exclude"), str)
