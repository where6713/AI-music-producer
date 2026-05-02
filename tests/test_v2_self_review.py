from __future__ import annotations

from src.v2 import self_review as mod


def test_self_review_retries_on_props_stack(monkeypatch) -> None:
    draft = {"lyrics": "[Verse 1]\n后视镜里的人还在看我\n[Chorus]\n我只轻轻说再见", "selected_ids": [], "selection_mode": "matched"}

    def fake_call(_prompt, temperature=0.3):
        return "[Verse 1]\n灯慢慢熄了\n[Chorus]\n我只轻轻说再见", {"tokens_in": 1, "tokens_out": 1}

    monkeypatch.setattr(mod, "llm_call", fake_call)
    out = mod.self_review(draft)
    assert out["retry_count"] == 1
    assert out["quality_gate_failed"] is False


def test_self_review_retries_on_inversion_overload(monkeypatch) -> None:
    draft = {"lyrics": "[Verse 1]\n我把梦放下\n你将话藏起\n替沉默做证\n把昨天拧干\n将回忆折叠\n[Chorus]\n我只轻轻说再见", "selected_ids": [], "selection_mode": "matched"}

    def fake_call(_prompt, temperature=0.3):
        return "[Verse 1]\n灯慢慢熄了\n[Chorus]\n我只轻轻说再见", {"tokens_in": 1, "tokens_out": 1}

    monkeypatch.setattr(mod, "llm_call", fake_call)
    out = mod.self_review(draft)
    assert out["retry_count"] == 1
    assert out["quality_gate_failed"] is False


def test_self_review_clean_lyrics_no_retry() -> None:
    out = mod.self_review({"lyrics": "[Verse 1]\n灯慢慢熄了\n[Chorus]\n我只轻轻说再见", "selected_ids": [], "selection_mode": "matched"})
    assert out["retry_count"] == 0
    assert out["quality_gate_failed"] is False


def test_retry_surgical_fix_mode(monkeypatch) -> None:
    draft = {"lyrics": "[Verse 1]\n后视镜里的人还在看我\n[Chorus]\n我只轻轻说再见", "selected_ids": [], "selection_mode": "matched"}
    calls = []

    def fake_call(prompt, temperature=0.3):
        calls.append(prompt[:30])
        if len(calls) == 1:
            return "[Verse 1]\n后视镜里的人还在看我\n[Chorus]\n我只轻轻说再见", {"tokens_in": 1, "tokens_out": 1}
        return "[Verse 1]\n灯慢慢熄了\n[Chorus]\n我只轻轻说再见", {"tokens_in": 1, "tokens_out": 1}

    monkeypatch.setattr(mod, "llm_call", fake_call)
    out = mod.self_review(draft)
    assert out["retry_count"] == 2
    assert out["retry_modes"] == ["full_revise", "surgical_fix"]
    assert out["quality_gate_failed"] is False
