from __future__ import annotations

from pathlib import Path

from src.v2.main import run_v2


def test_pipeline_produces_non_empty_lyrics(monkeypatch) -> None:
    import src.v2.perceive_music as perceive_mod
    import src.v2.distill_emotion as distill_mod
    import src.v2.compose as compose_mod
    import src.v2.self_review as review_mod
    import src.v2.select_corpus as corpus_mod

    monkeypatch.setattr(perceive_mod, "llm_call", lambda _p, temperature=0.3: ('{"genre_guess":"indie pop","bpm_range":"100-120","vibe":"x","audio_hint":".wav","intent":"x"}', {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr(distill_mod, "llm_call", lambda _p, temperature=0.3: ("这首歌的根是票根 标题句是我先睡了 情绪从否认到承认再到放过 韵部选江阳", {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr(compose_mod, "llm_call", lambda _p, temperature=0.9: ('{"lyrics":"[Verse 1]\\n票根在掌心\\n[Verse 2]\\n夜路很安静\\n[Chorus]\\n我先睡了\\n风还在耳边\\n我先睡了\\n[Bridge]\\n把想念放轻","style":"x","exclude":"x"}', {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr(review_mod, "llm_call", lambda _p, temperature=0.3: ("[Verse 1]\n票根在掌心\n[Verse 2]\n夜路很安静\n[Chorus]\n我先睡了\n风还在耳边\n我先睡了\n[Bridge]\n把想念放轻", {"tokens_in": 1, "tokens_out": 1}))
    monkeypatch.setattr(corpus_mod, "select_corpus", lambda _i, _p, limit=100: [{"id": "x"}])
    monkeypatch.setattr(corpus_mod, "select_golden_anchors_with_mode", lambda _pool, _p: ([{"id": "x.txt"}], "matched"))

    out = run_v2("夜里独自开车想念一个人", index_path=str(Path("corpus/_index.json")))
    assert isinstance(out.get("lyrics"), str) and out["lyrics"].strip()
    assert isinstance(out.get("brief"), str) and out["brief"].strip()


def test_polish_stops_when_output_unchanged(monkeypatch) -> None:
    import src.v2.self_review as review_mod

    calls = {"n": 0}

    def fake_call(_p, temperature=0.3):
        calls["n"] += 1
        if calls["n"] == 1:
            return "[Verse 1]\n今夜风很轻", {"tokens_in": 1, "tokens_out": 1}
        return "[Verse 1]\n今夜风很轻", {"tokens_in": 1, "tokens_out": 1}

    monkeypatch.setattr(review_mod, "llm_call", fake_call)
    out = review_mod.self_review({"lyrics": "[Verse 1]\n今夜风很轻", "brief": {"brief": "一段笔记"}})
    assert out["polish_passes"] == 2
