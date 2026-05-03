from __future__ import annotations

from pathlib import Path

from src.v2.main import run_v2
from src.v2._prompts import select_persona_a
from src.v2.distill_emotion import distill_emotion
from src.v2.select_corpus import extract_anchor_chorus
from src.v2.platform_adapt import PlatformAdaptError, adapt


def test_pipeline_produces_non_empty_lyrics(monkeypatch) -> None:
    import src.v2.perceive_music as perceive_mod
    import src.v2.distill_emotion as distill_mod
    import src.v2.compose as compose_mod
    import src.v2.second_pass as review_mod
    import src.v2.select_corpus as corpus_mod

    monkeypatch.setattr(perceive_mod, "llm_call", lambda _p, temperature=0.3: ('{"genre_guess":"indie pop","bpm_range":"100-120","vibe":"x","audio_hint":".wav","intent":"x"}', {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr(distill_mod, "llm_call", lambda _p, temperature=0.3: ("这首歌的根是票根 标题句是我先睡了 情绪从否认到承认再到放过 韵部选江阳", {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr(compose_mod, "llm_call", lambda _p, temperature=0.9: ('{"lyrics":"[Verse 1]\\n票根在掌心\\n[Verse 2]\\n夜路很安静\\n[Chorus]\\n我先睡了\\n风还在耳边\\n我先睡了\\n[Bridge]\\n把想念放轻","style":"x","exclude":"x"}', {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr(review_mod, "llm_call", lambda _p, temperature=0.3: ("[Verse 1]\n票根在掌心\n[Verse 2]\n夜路很安静\n[Chorus]\n我先睡了\n风还在耳边\n我先睡了\n[Bridge]\n把想念放轻", {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr("src.v2.platform_adapt.llm_call", lambda _p, temperature=0.3: ('{"style":"x","exclude":"x"}', {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr(corpus_mod, "select_corpus", lambda _i, _p, limit=100: [{"id": "x"}])
    monkeypatch.setattr(corpus_mod, "select_golden_anchors_with_mode", lambda _pool, _p: ([{"id": "x.txt"}], "matched"))

    out = run_v2("夜里独自开车想念一个人", index_path=str(Path("corpus/_index.json")))
    assert isinstance(out.get("lyrics"), str) and out["lyrics"].strip()
    assert isinstance(out.get("emotion_focus"), str) and out["emotion_focus"].strip()
    assert out.get("polish_passes") == 1


def test_polish_stops_when_output_unchanged(monkeypatch) -> None:
    import src.v2.second_pass as review_mod

    calls = {"n": 0}

    def fake_call(_p, temperature=0.3):
        calls["n"] += 1
        if calls["n"] == 1:
            return "[Verse 1]\n今夜风很轻", {"tokens_in": 1, "tokens_out": 1}
        return "[Verse 1]\n今夜风很轻", {"tokens_in": 1, "tokens_out": 1}

    monkeypatch.setattr(review_mod, "llm_call", fake_call)
    out = review_mod.second_pass({"lyrics": "[Verse 1]\n今夜风很轻", "brief": {"emotion_focus": "一段笔记"}})
    assert out["polish_passes"] == 1


def test_persona_selection_by_genre() -> None:
    assert select_persona_a({"genre_guess": "古风", "vibe": "空灵"}) == "fang_wenshan"


def test_distill_outputs_one_sentence(monkeypatch) -> None:
    import src.v2.distill_emotion as mod

    monkeypatch.setattr(mod, "llm_call", lambda _p, temperature=0.3: ("她在凌晨的路上 对旧爱说了再见", {"tokens_in": 1, "tokens_out": 1}))
    out = distill_emotion("夜里独自开车想念一个人", {"persona_used": "li_zongsheng"})
    assert isinstance(out["emotion_focus"], str)
    assert 0 < len(out["emotion_focus"]) <= 40


def test_select_corpus_raises_on_missing() -> None:
    try:
        extract_anchor_chorus("not-exists.txt")
        assert False
    except FileNotFoundError:
        assert True


def test_extract_anchor_chorus_never_empty(tmp_path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("# source: x\n\n第一行\n第二行\n第三行\n第四行\n", encoding="utf-8")
    out = extract_anchor_chorus(str(p))
    assert isinstance(out, str) and out.strip()


def test_platform_adapt_raises_on_bad_json(monkeypatch) -> None:
    import src.v2.platform_adapt as mod

    monkeypatch.setattr(mod, "llm_call", lambda _p, temperature=0.3: ("bad", {"tokens_in": 1, "tokens_out": 1}))
    try:
        adapt("歌词", {"genre_guess": "r&b"})
        assert False
    except PlatformAdaptError:
        assert True
