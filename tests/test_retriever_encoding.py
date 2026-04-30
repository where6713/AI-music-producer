from __future__ import annotations

import json
from pathlib import Path

from src.retriever import _load_corpus, _type_allowed, retrieve_few_shot_examples
from src.schemas import UserInput


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_utf8_sig_and_ufffd_filter(tmp_path, monkeypatch) -> None:
    corpus_dir = tmp_path / "corpus" / "_clean"
    golden_dir = tmp_path / "corpus" / "_raw"
    modern = corpus_dir / "lyrics_modern_zh.json"
    classical = corpus_dir / "poetry_classical.json"
    golden_modern = golden_dir / "golden_anchors_modern_llm_enriched.json"
    golden_classical = golden_dir / "golden_anchors_classical.json"

    dirty = {
        "type": "modern_lyric",
        "title": "dirty",
        "emotion_tags": ["\ufffdbad", "late-night"],
        "content": "x",
        "learn_point": "x" * 60,
        "do_not_copy": "rule",
        "source_id": "dirty-1",
    }
    clean = {
        "type": "modern_lyric",
        "title": "clean",
        "emotion_tags": ["late-night", "regret"],
        "content": "凌晨 地铁 站台",
        "learn_point": "x" * 60,
        "do_not_copy": "rule",
        "source_id": "clean-1",
    }

    modern.parent.mkdir(parents=True, exist_ok=True)
    modern.write_text(json.dumps([dirty, clean], ensure_ascii=False), encoding="utf-8-sig")
    _write_json(classical, [])
    _write_json(golden_modern, [])
    _write_json(golden_classical, [])

    import src.retriever as retriever_mod

    class _Report:
        def __init__(self) -> None:
            self.passed = True
            self.failed_rules: list[str] = []

    monkeypatch.setattr(retriever_mod, "lint_corpus_row", lambda *_args, **_kwargs: _Report())

    monkeypatch.setattr(retriever_mod, "CLEAN_CORPUS_FILES", [
        "corpus/_clean/poetry_classical.json",
        "corpus/_clean/lyrics_modern_zh.json",
    ])
    monkeypatch.setattr(retriever_mod, "GOLDEN_ANCHOR_FILES", [
        "corpus/_raw/golden_anchors_modern_llm_enriched.json",
        "corpus/_raw/golden_anchors_classical.json",
    ])

    rows = _load_corpus(tmp_path)
    source_ids = {str(r.get("source_id", "")) for r in rows}
    assert "clean-1" in source_ids
    assert "dirty-1" not in source_ids


def test_type_routing_constraints() -> None:
    assert _type_allowed("classical_poem", "club_dance") is False
    assert _type_allowed("modern_lyric", "club_dance") is True
    assert _type_allowed("classical_poem", "classical_restraint") is True


def test_source_id_chinese_path_url_encoded_and_classical_priority(tmp_path, monkeypatch) -> None:
    corpus_dir = tmp_path / "corpus" / "_clean"
    golden_dir = tmp_path / "corpus" / "_raw"

    modern_row = {
        "type": "modern_lyric",
        "title": "modern row",
        "emotion_tags": ["nostalgia"],
        "content": "夜雨 心事",
        "learn_point": "x" * 60,
        "do_not_copy": "rule",
        "source_id": "github:owner/repo:corpus/中文路径.json",
        "profile_tag": "classical_restraint",
        "profile_confidence": 0.8,
    }
    classical_row = {
        "type": "classical_poem",
        "title": "classical row",
        "emotion_tags": ["nostalgia"],
        "content": "落叶 满空山",
        "learn_point": "古典意象与留白",
        "do_not_copy": "",
        "source_id": "github:owner/repo:corpus/诗词库.json",
        "profile_tag": "classical_restraint",
        "profile_confidence": 0.95,
    }

    _write_json(corpus_dir / "lyrics_modern_zh.json", [modern_row])
    _write_json(corpus_dir / "poetry_classical.json", [classical_row])
    _write_json(golden_dir / "golden_anchors_modern_llm_enriched.json", [])
    _write_json(golden_dir / "golden_anchors_classical.json", [])

    import src.retriever as retriever_mod

    class _Report:
        def __init__(self) -> None:
            self.passed = True
            self.failed_rules: list[str] = []

    monkeypatch.setattr(retriever_mod, "lint_corpus_row", lambda *_args, **_kwargs: _Report())

    monkeypatch.setattr(retriever_mod, "CLEAN_CORPUS_FILES", [
        "corpus/_clean/poetry_classical.json",
        "corpus/_clean/lyrics_modern_zh.json",
    ])
    monkeypatch.setattr(retriever_mod, "GOLDEN_ANCHOR_FILES", [
        "corpus/_raw/golden_anchors_modern_llm_enriched.json",
        "corpus/_raw/golden_anchors_classical.json",
    ])

    user = UserInput(raw_intent="古寺夜雨", profile_override="classical_restraint")
    data = retrieve_few_shot_examples(user, repo_root=tmp_path, return_metadata=True)
    samples = data["samples"]

    assert len(samples) >= 2
    assert samples[0]["type"] == "classical_poem"
    encoded_source_ids = [s["source_id"] for s in samples]
    assert any("%E4%B8%AD%E6%96%87" in sid or "%E8%AF%97%E8%AF%8D" in sid for sid in encoded_source_ids)
    assert all("中文" not in sid and "诗词" not in sid for sid in encoded_source_ids)
