from __future__ import annotations

from src.v2 import self_review as mod


def test_self_review_retries_on_props_stack(monkeypatch) -> None:
    draft = {"lyrics": "[Verse 1]\n后视镜看座椅\n[Verse 2]\n还是看我\n[Bridge]\n晚一点\n[Chorus]\n我只轻轻说再见", "selected_ids": [], "selection_mode": "matched", "brief": {"central_image": "票根", "cognitive_hook": "我先睡了", "arc_3_stations": ["否认-装没事", "承认-痛被看见", "放过-不再追问"]}}

    def fake_call(_prompt, temperature=0.3):
        return "[Verse 1]\n票根装没事\n[Verse 2]\n票根见了痛\n[Chorus]\n我先睡了\n我先睡了\n[Bridge]\n票根不追问", {"tokens_in": 1, "tokens_out": 1}

    monkeypatch.setattr(mod, "llm_call", fake_call)
    out = mod.self_review(draft)
    assert out["retry_count"] == 1
    assert out["quality_gate_failed"] is False


def test_self_review_retries_on_inversion_overload(monkeypatch) -> None:
    draft = {"lyrics": "[Verse 1]\n我把梦放下\n你将话藏起\n替沉默做证\n把昨天拧干\n将回忆折叠\n[Verse 2]\n还在等\n[Bridge]\n晚一点\n[Chorus]\n我只轻轻说再见", "selected_ids": [], "selection_mode": "matched", "brief": {"central_image": "票根", "cognitive_hook": "我先睡了", "arc_3_stations": ["否认-装没事", "承认-痛被看见", "放过-不再追问"]}}

    def fake_call(_prompt, temperature=0.3):
        return "[Verse 1]\n票根装没事\n[Verse 2]\n票根见了痛\n[Chorus]\n我先睡了\n我先睡了\n[Bridge]\n票根不追问", {"tokens_in": 1, "tokens_out": 1}

    monkeypatch.setattr(mod, "llm_call", fake_call)
    out = mod.self_review(draft)
    assert out["retry_count"] == 1
    assert out["quality_gate_failed"] is False


def test_self_review_clean_lyrics_no_retry() -> None:
    out = mod.self_review({"lyrics": "[Verse 1]\n票根装没事\n[Verse 2]\n票根见了痛\n[Chorus]\n我先睡了\n风吹旧衣襟\n我先睡了\n[Bridge]\n票根不追问", "selected_ids": [], "selection_mode": "matched", "brief": {"central_image": "票根", "cognitive_hook": "我先睡了", "arc_3_stations": ["否认-装没事", "承认-痛被看见", "放过-不再追问"]}})
    assert out["retry_count"] == 0
    assert out["quality_gate_failed"] is False


def test_retry_surgical_fix_mode(monkeypatch) -> None:
    draft = {"lyrics": "[Verse 1]\n后视镜看座椅\n[Verse 2]\n还是看我\n[Bridge]\n晚一点\n[Chorus]\n我只轻轻说再见", "selected_ids": [], "selection_mode": "matched", "brief": {"central_image": "票根", "cognitive_hook": "我先睡了", "arc_3_stations": ["否认-装没事", "承认-痛被看见", "放过-不再追问"]}}
    calls = []

    def fake_call(prompt, temperature=0.3):
        calls.append(prompt[:30])
        return "[Verse 1]\n票根装没事\n[Verse 2]\n票根见了痛\n[Chorus]\n我先睡了\n我先睡了\n[Bridge]\n票根不追问", {"tokens_in": 1, "tokens_out": 1}

    monkeypatch.setattr(mod, "llm_call", fake_call)
    out = mod.self_review(draft)
    assert out["retry_count"] == 1
    assert out["retry_modes"] == ["surgical_fix"]


def test_self_review_flags_missing_hook(monkeypatch) -> None:
    draft = {
        "lyrics": "[Verse 1]\n我装没事\n[Verse 2]\n不再追问\n[Chorus]\n天亮\n风把灯吹暗\n[Bridge]\n我先睡了",
        "selected_ids": [],
        "selection_mode": "matched",
        "brief": {"central_image": "票根", "cognitive_hook": "我先睡了", "arc_3_stations": ["否认-装没事", "承认-痛被看见", "放过-不再追问"]},
    }

    monkeypatch.setattr(mod, "llm_call", lambda _prompt, temperature=0.3: (draft["lyrics"], {"tokens_in": 1, "tokens_out": 1}))
    out = mod.self_review(draft)
    assert out["quality_gate_failed"] is True
    assert "brief_violation_hook" in out["failure_reasons"]
