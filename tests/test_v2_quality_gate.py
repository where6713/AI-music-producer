from __future__ import annotations

from src.v2._quality_rules import check
from src.v2.perceive_music import perceive_music


def test_no_syntax_crutch() -> None:
    text = "我把沉默折进外套口袋\n把晚安留给明天"
    violations = check(text)
    assert any(v.startswith("syntax_crutch") for v in violations)


def test_no_ngram_density() -> None:
    text = "[Verse 1]\n啊呢吧喔\n[Chorus]\n好像这样也行"
    violations = check(text)
    assert "ngram_density" in violations


def test_no_cn_en_mix() -> None:
    text = "city lights在窗边缓缓褪色"
    violations = check(text)
    assert "cn_en_mix" in violations


def test_no_ba_x_dong_cheng_y() -> None:
    text = "把夜色酿成酒\n把心事写成诗"
    violations = check(text)
    assert any(v.startswith("syntax_crutch") for v in violations)


def test_no_cliche_density() -> None:
    text = "站台有风，晚安又在站台，风还在吹。"
    violations = check(text)
    assert any(v.startswith("cliche_density") for v in violations)


def test_no_visual_prop_second_wave() -> None:
    text = "后视镜里的人还在看我\n仪表盘亮得像没说完的话"
    violations = check(text)
    assert any(v.startswith("blacklist:") for v in violations)


def test_no_hook_too_long() -> None:
    text = "[Chorus]\n想你想你想你想你想你想你想你\n[Verse 1]\n我还没说完"
    violations = check(text)
    assert "hook_too_long" in violations


def test_clean_lyrics_pass_gate() -> None:
    text = "[Verse 1]\n灯慢慢熄了\n[Chorus]\n我只轻轻说再见"
    assert check(text) == []


def test_perceive_hybs_indie_pop() -> None:
    import src.v2.perceive_music as perceive_mod

    monkey = __import__('pytest').MonkeyPatch()
    monkey.setattr(perceive_mod, "llm_call", lambda _prompt, temperature=0.3: ('{"genre_guess":"indie pop","bpm_range":"100-120","vibe":"x","audio_hint":".flac","intent":"x"}', {"tokens_in": 1, "tokens_out": 1}))
    out = perceive_music("夜里独自开车想念一个人", ref_audio="F:/Onedrive/桌面/Dancing with my phone - HYBS.flac")
    monkey.undo()
    assert out.get("genre_guess") == "indie pop"
    assert out.get("bpm_range") in {"100-120"}
