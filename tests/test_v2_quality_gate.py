from __future__ import annotations

from src.v2._quality_rules import check
from src.v2.perceive_music import perceive_music


def test_no_syntax_crutch() -> None:
    text = "我把沉默折进外套口袋\n我把晚安留给明天"
    hard, soft = check(text)
    assert any(v.startswith("syntax_crutch") for v in hard)


def test_no_ngram_density() -> None:
    text = "[Verse 1]\n啊呢吧喔\n[Chorus]\n好像这样也行"
    hard, soft = check(text)
    assert "ngram_density" in hard


def test_no_cn_en_mix() -> None:
    text = "city lights在窗边缓缓褪色"
    hard, soft = check(text)
    assert "cn_en_mix" in hard


def test_no_ba_x_dong_cheng_y() -> None:
    text = "把夜色酿成酒\n把心事熬成药\n把回忆埋成灰"
    hard, soft = check(text)
    assert any(v.startswith("syntax_crutch") for v in hard)


def test_ba_phrase_density_under_threshold() -> None:
    text = "把夜色酿成酒\n把答案绣成花"
    hard, soft = check(text)
    assert not any(v.startswith("syntax_crutch") for v in hard)


def test_no_cliche_density() -> None:
    text = "站台有风，晚安又在站台，风还在吹。"
    hard, soft = check(text)
    assert any(v.startswith("cliche_density") for v in hard)


def test_cliche_cooccurrence_soft_only() -> None:
    text = "站台有风"
    hard, soft = check(text)
    assert "cliche_cooccurrence" in soft
    assert "cliche_cooccurrence" not in hard


def test_no_visual_prop_second_wave() -> None:
    text = "后视镜里的人还在看我\n仪表盘亮得像没说完的话"
    hard, soft = check(text)
    assert any(v.startswith("blacklist:") for v in hard)


def test_no_hook_too_long() -> None:
    text = "[Chorus]\n想你想你想你想你想你想你想你\n[Verse 1]\n我还没说完"
    hard, soft = check(text)
    assert "hook_too_long" in hard


def test_inversion_threshold_4() -> None:
    text = "[Verse 1]\n我把梦放下\n你将话藏起\n替沉默做证"
    hard, soft = check(text)
    assert "inversion_overload" not in hard


def test_clean_lyrics_pass_gate() -> None:
    text = "[Verse 1]\n灯慢慢熄了\n[Chorus]\n我只轻轻说再见"
    hard, soft = check(text)
    assert hard == []


def test_perceive_hybs_indie_pop() -> None:
    import src.v2.perceive_music as perceive_mod

    monkey = __import__('pytest').MonkeyPatch()
    monkey.setattr(perceive_mod, "llm_call", lambda _prompt, temperature=0.3: ('{"genre_guess":"indie pop","bpm_range":"100-120","vibe":"x","audio_hint":".flac","intent":"x"}', {"tokens_in": 1, "tokens_out": 1}))
    out = perceive_music("夜里独自开车想念一个人", ref_audio="F:/Onedrive/桌面/Dancing with my phone - HYBS.flac")
    monkey.undo()
    assert out.get("genre_guess") == "indie pop"
    assert out.get("bpm_range") in {"100-120"}
