from __future__ import annotations

import json
from pathlib import Path

from src.v2.compose import compose
from src.v2.distill_emotion import distill_emotion
from src.v2.main import run_v2
from src.v2.perceive_music import perceive_music
from src.v2.select_corpus import select_corpus
from src.v2.self_review import self_review


def test_perceive_music_outputs_expected_fields() -> None:
    out = perceive_music("深夜慢一点，想写内省情绪", ref_audio="demo.wav")
    assert out["tempo"] in {"slow", "mid", "fast"}
    assert out["energy"] in {"low", "medium", "high"}
    assert isinstance(out["texture"], str)
    assert out["audio_hint"] == ".wav"


def test_distill_emotion_derives_arc_and_image() -> None:
    portrait = {"texture": "indie lazy groove"}
    out = distill_emotion("失恋后一个人回家", portrait)
    assert out["valence"] == "negative"
    assert out["arc"] == "descend-then-breathe"
    assert out["central_image"] == "street lamp and late bus"


def test_select_corpus_prefers_matching_rows(tmp_path: Path) -> None:
    rows = [
        {"id": "a", "title": "夜色", "summary_50chars": "urban introspective city", "emotion_tags": ["孤独"], "char_count": 100},
        {"id": "b", "title": "晴天", "summary_50chars": "bright pop youth", "emotion_tags": ["青春"], "char_count": 120},
    ]
    index = tmp_path / "index.json"
    index.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    out = select_corpus(index, {"texture": "urban introspective", "tempo": "slow", "energy": "low"}, limit=10)
    assert len(out) >= 1
    assert out[0]["id"] == "a"


def test_compose_and_self_review_keep_structure() -> None:
    draft = compose(
        {"texture": "indie lazy groove"},
        {"arc": "hold-and-release", "central_image": "street lamp"},
        golden_refs=[],
        corpus_pool=[{"id": "x"}],
    )
    reviewed = self_review(draft)
    assert "[Verse]" in str(reviewed["lyrics"])
    assert "[Chorus]" in str(reviewed["lyrics"])
    assert reviewed["review_note"] == "light expression polish; structure unchanged"


def test_run_v2_end_to_end_with_local_index(tmp_path: Path) -> None:
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
