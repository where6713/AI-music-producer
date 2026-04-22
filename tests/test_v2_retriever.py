from __future__ import annotations

import json

from src.retriever import retrieve_few_shot_examples
from src.schemas import UserInput


def test_retriever_returns_real_corpus_examples(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / "poetry_classical.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "poem-jys-001",
                    "type": "classical_poem",
                    "title": "静夜思",
                    "emotion_tags": ["nostalgia", "restraint"],
                    "content": "举头望明月，低头思故乡。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (corpus / "lyrics_modern_zh.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "lyric-modern-101",
                    "type": "modern_lyric",
                    "title": "凌晨未发送",
                    "emotion_tags": ["breakup", "late-night"],
                    "content": "对话框停在最后一句。",
                },
                {
                    "source_id": "lyric-modern-102",
                    "type": "modern_lyric",
                    "title": "不再拨通",
                    "emotion_tags": ["distance", "regret"],
                    "content": "手在拨出前停住。",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    items = retrieve_few_shot_examples(
        UserInput(raw_intent="分手后深夜想发消息又克制住"),
        repo_root=tmp_path,
        top_k=3,
    )

    assert len(items) >= 2
    assert all(not row["source_id"].startswith("fallback") for row in items)


def test_retriever_returns_profile_vote_metadata(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / "poetry_classical.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "poem-jys-001",
                    "type": "classical_poem",
                    "title": "静夜思",
                    "emotion_tags": ["nostalgia", "restraint"],
                    "profile_tag": "classical_restraint",
                    "content": "举头望明月，低头思故乡。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (corpus / "lyrics_modern_zh.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "lyric-modern-101",
                    "type": "modern_lyric",
                    "title": "凌晨未发送",
                    "emotion_tags": ["breakup", "late-night"],
                    "profile_tag": "urban_introspective",
                    "content": "对话框停在最后一句。",
                },
                {
                    "source_id": "lyric-modern-102",
                    "type": "modern_lyric",
                    "title": "不再拨通",
                    "emotion_tags": ["distance", "regret"],
                    "profile_tag": "urban_introspective",
                    "content": "手在拨出前停住。",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = retrieve_few_shot_examples(
        UserInput(raw_intent="分手后深夜想发消息又克制住"),
        repo_root=tmp_path,
        top_k=3,
        return_metadata=True,
    )

    assert isinstance(result, dict)
    assert len(result["samples"]) >= 2
    assert result["profile_vote"] == "urban_introspective"
    assert result["vote_confidence"] >= (2 / 3)
