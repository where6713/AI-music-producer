from __future__ import annotations

from src.v2._quality_rules import check
from src.v2.perceive_music import perceive_music


def test_no_syntax_crutch() -> None:
    text = "我把沉默折进外套口袋\n把晚安留给明天"
    violations = check(text)
    assert any(v.startswith("syntax_crutch") for v in violations)


def test_no_cn_en_mix() -> None:
    text = "city lights在窗边缓缓褪色"
    violations = check(text)
    assert "cn_en_mix" in violations


def test_no_cliche_density() -> None:
    text = "站台有风，晚安又在站台，风还在吹。"
    violations = check(text)
    assert any(v.startswith("cliche_density") for v in violations)


def test_perceive_hybs_indie_pop() -> None:
    out = perceive_music("夜里独自开车想念一个人", ref_audio="F:/Onedrive/桌面/Dancing with my phone - HYBS.flac")
    assert out.get("genre_guess") == "indie pop"
    assert out.get("bpm_range") in {"100-120"}
