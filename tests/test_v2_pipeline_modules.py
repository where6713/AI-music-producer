from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.v2.compose import compose
from src.v2.distill_emotion import distill_emotion
from src.v2.main import run_v2
from src.v2.perceive_music import perceive_music
from src.v2.select_corpus import select_corpus, select_golden_anchors, select_golden_anchors_with_mode
from src.v2.self_review import self_review


def test_perceive_music_returns_5_keys() -> None:
    out = perceive_music("深夜慢一点，想写内省情绪", ref_audio="demo.wav")
    assert set(out.keys()) >= {"genre_guess", "bpm_range", "vibe", "audio_hint", "intent"}
    assert out["audio_hint"] == ".wav"


def test_distill_emotion_motive_and_hook_seed() -> None:
    portrait = {"texture": "indie lazy groove"}
    out = distill_emotion("失恋后一个人回家", portrait)
    assert isinstance(out["inner_motive"], str)
    assert isinstance(out["arc"], str)
    assert isinstance(out["hook_seed"], str)


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


def test_select_golden_anchors_dedup_selected_ids(tmp_path: Path) -> None:
    p = tmp_path / "corpus" / "golden_dozen"
    p.mkdir(parents=True)
    a = p / "a.txt"
    a.write_text("# source: x\n# style: indie pop 慵懒\n# texture: x\n# version: v1\n\n词", encoding="utf-8")
    pool = [
        {"id": str(a)},
        {"id": str(a)},
    ]
    out = select_golden_anchors(pool, {"genre_guess": "indie pop"})
    assert len(out) == 1
    assert out[0]["id"] == str(a)


def test_select_golden_anchors_match_by_style_header(tmp_path: Path) -> None:
    p = tmp_path / "corpus" / "golden_dozen"
    p.mkdir(parents=True)
    indie = p / "indie.txt"
    indie.write_text("# source: x\n# style: indie pop 慵懒\n# texture: x\n# version: v1\n\n词", encoding="utf-8")
    ballad = p / "ballad.txt"
    ballad.write_text("# source: x\n# style: 慢板抒情\n# texture: x\n# version: v1\n\n词", encoding="utf-8")
    pool = [
        {"id": str(ballad)},
        {"id": str(indie)},
    ]
    out = select_golden_anchors(pool, {"genre_guess": "indie pop"})
    assert out
    assert out[0]["id"] == str(indie)


def test_select_golden_anchors_style_token_intersection(tmp_path: Path) -> None:
    p = tmp_path / "corpus" / "golden_dozen"
    p.mkdir(parents=True)
    indie = p / "indie.txt"
    indie.write_text("# source: x\n# style: 慵懒 indie pop\n# texture: x\n# version: v1\n\n词", encoding="utf-8")
    out = select_golden_anchors([{"id": str(indie)}], {"genre_guess": "indie pop"})
    assert out and out[0]["id"] == str(indie)


def test_select_golden_anchors_fallback_global_when_no_match(tmp_path: Path) -> None:
    p = tmp_path / "corpus" / "golden_dozen"
    p.mkdir(parents=True)
    a = p / "a.txt"
    b = p / "b.txt"
    a.write_text("# source: x\n# style: 古典中国风\n# texture: x\n# version: v1\n\n词", encoding="utf-8")
    b.write_text("# source: x\n# style: 慢板抒情\n# texture: x\n# version: v1\n\n词", encoding="utf-8")
    out, mode = select_golden_anchors_with_mode([{"id": str(b)}, {"id": str(a)}], {"genre_guess": "electro dance"})
    assert mode == "fallback_global"
    assert [x["id"] for x in out] == [str(a), str(b)]


def test_select_golden_anchors_cap_two_sorted_when_three_match(tmp_path: Path) -> None:
    p = tmp_path / "corpus" / "golden_dozen"
    p.mkdir(parents=True)
    a = p / "a.txt"
    b = p / "b.txt"
    c = p / "c.txt"
    for f in (a, b, c):
        f.write_text("# source: x\n# style: indie pop 慵懒\n# texture: x\n# version: v1\n\n词", encoding="utf-8")
    out, mode = select_golden_anchors_with_mode([{"id": str(c)}, {"id": str(a)}, {"id": str(b)}], {"genre_guess": "indie pop"})
    assert mode == "matched"
    assert [x["id"] for x in out] == [str(a), str(b)]


def test_select_corpus_empty_pool_marks_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V2_DISABLE_FS_FALLBACK", "1")
    out, mode = select_golden_anchors_with_mode([{"id": "corpus/_clean/x.txt"}], {"genre_guess": "R&B"})
    assert out == []
    assert mode == "empty_pool"


def test_select_corpus_matched_path_with_fixtures() -> None:
    root = Path(__file__).parent / "fixtures" / "mock_golden"
    rnb = root / "mock_rnb.txt"
    indie = root / "mock_indie.txt"
    out, mode = select_golden_anchors_with_mode(
        [{"id": str(indie)}, {"id": str(rnb)}],
        {"genre_guess": "R&B"},
    )
    assert mode == "matched"
    assert any(str(rnb) == str(x.get("id", "")) for x in out)


def test_select_golden_anchors_reads_real_filesystem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    g = tmp_path / "corpus" / "golden_dozen"
    g.mkdir(parents=True)
    (g / "aa.txt").write_text("# source: t\n# style: r&b 律动\n# texture: x\n# version: t\n\n词", encoding="utf-8")
    (g / "bb.txt").write_text("# source: t\n# style: r&b 律动\n# texture: x\n# version: t\n\n词", encoding="utf-8")
    monkeypatch.setenv("V2_DISABLE_FS_FALLBACK", "0")
    monkeypatch.setattr("src.v2._golden_match._repo_golden_files", lambda: [str(g / "aa.txt"), str(g / "bb.txt")])
    out, mode = select_golden_anchors_with_mode([], {"genre_guess": "r&b"})
    assert mode == "fallback_filesystem"
    assert 1 <= len(out) <= 2


def test_compose_pass1_id_grounding() -> None:
    pool = [{"id": "x"}, {"id": "y"}]
    draft = compose(
        {"texture": "indie lazy groove"},
        {"arc": "压抑→冲动→克制→释然", "inner_motive": "想联络却不敢", "hook_seed": "我还要等你吗"},
        golden_refs=[],
        corpus_pool=pool,
    )
    assert draft["selected_ids"] == []


def test_self_review_preserves_section_count() -> None:
    draft = compose(
        {"texture": "indie lazy groove"},
        {"arc": "压抑→冲动→克制→释然", "inner_motive": "删了又写", "hook_seed": "你会回头吗"},
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
