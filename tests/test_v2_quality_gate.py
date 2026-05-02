from __future__ import annotations

from src.v2._quality_rules import check
from src.v2.perceive_music import perceive_music


def test_quality_gate_catches_punctuation() -> None:
    text = "[Verse 1]\n你在夜里，没说话"
    hard, _ = check(text)
    assert "punctuation_violation" in hard


def test_quality_gate_catches_line_too_long() -> None:
    text = "[Verse 1]\n这是一条超过十个汉字的长句"
    hard, _ = check(text)
    assert "line_too_long" in hard


def test_cn_en_mix_relaxed_still_catches_word() -> None:
    text = "[Verse 1]\n我在city里走"
    hard, _ = check(text)
    assert "cn_en_mix" in hard


def test_clean_lyrics_pass_gate() -> None:
    text = "[Verse 1]\n灯慢慢熄了\n[Chorus]\n我只轻轻说再见"
    hard, _ = check(text)
    assert hard == []




def test_perceive_hybs_indie_pop() -> None:
    import src.v2.perceive_music as perceive_mod

    monkey = __import__('pytest').MonkeyPatch()
    monkey.setattr(perceive_mod, "llm_call", lambda _prompt, temperature=0.3: ('{"genre_guess":"indie pop","bpm_range":"100-120","vibe":"x","audio_hint":".flac","intent":"x"}', {"tokens_in": 1, "tokens_out": 1}))
    out = perceive_music("夜里独自开车想念一个人", ref_audio="F:/Onedrive/桌面/Dancing with my phone - HYBS.flac")
    monkey.undo()
    assert out.get("genre_guess") == "indie pop"
    assert out.get("bpm_range") in {"100-120"}

