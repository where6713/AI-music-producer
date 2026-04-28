from __future__ import annotations

import json
import pytest

from src.retriever import (
    InsufficientQualityFewShotError,
    corpus_balance_check,
    retrieve_few_shot_examples,
)
from src.schemas import UserInput


def _write_clean_corpus(corpus_dir, poetry_rows, lyric_rows) -> None:
    clean_dir = corpus_dir / "_clean"
    clean_dir.mkdir(parents=True, exist_ok=True)

    def _normalize(row: dict) -> dict:
        out = dict(row)
        row_type = str(out.get("type", "")).strip().lower()
        out.setdefault(
            "profile_tag",
            "classical_restraint" if row_type == "classical_poem" else "urban_introspective",
        )
        out.setdefault(
            "valence",
            "neutral" if out.get("profile_tag") == "classical_restraint" else "negative",
        )
        out.setdefault("learn_point", "保持具象化并避免模板化复写")
        out.setdefault("do_not_copy", "不要复写原句与段落顺序")
        return out

    (clean_dir / "poetry_classical.json").write_text(
        json.dumps([_normalize(r) for r in poetry_rows], ensure_ascii=False),
        encoding="utf-8",
    )
    (clean_dir / "lyrics_modern_zh.json").write_text(
        json.dumps([_normalize(r) for r in lyric_rows], ensure_ascii=False),
        encoding="utf-8",
    )


def test_retriever_returns_real_corpus_examples(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = [
        {
            "source_id": "poem-jys-001",
            "type": "classical_poem",
            "title": "静夜思",
            "emotion_tags": ["nostalgia", "restraint"],
            "content": "举头望明月，低头思故乡，夜色慢慢凉。",
        }
    ]
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "不再拨通",
            "emotion_tags": ["distance", "regret"],
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
    ]
    (corpus / "poetry_classical.json").write_text(json.dumps(poetry_rows, ensure_ascii=False), encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(json.dumps(lyric_rows, ensure_ascii=False), encoding="utf-8")
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

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
    poetry_rows = [
        {
            "source_id": "poem-jys-001",
            "type": "classical_poem",
            "title": "静夜思",
            "emotion_tags": ["nostalgia", "restraint"],
            "profile_tag": "classical_restraint",
            "content": "举头望明月，低头思故乡，夜色慢慢凉。",
        }
    ]
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "profile_tag": "urban_introspective",
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "不再拨通",
            "emotion_tags": ["distance", "regret"],
            "profile_tag": "urban_introspective",
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
    ]
    (corpus / "poetry_classical.json").write_text(json.dumps(poetry_rows, ensure_ascii=False), encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(json.dumps(lyric_rows, ensure_ascii=False), encoding="utf-8")
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

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


def test_retriever_derives_profile_vote_when_profile_tag_missing(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = [
        {
            "source_id": "poem-jys-001",
            "type": "classical_poem",
            "title": "静夜思",
            "emotion_tags": ["nostalgia", "restraint"],
            "content": "举头望明月，低头思故乡，夜色慢慢凉。",
        }
    ]
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "不再拨通",
            "emotion_tags": ["distance", "regret"],
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
    ]
    (corpus / "poetry_classical.json").write_text(json.dumps(poetry_rows, ensure_ascii=False), encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(json.dumps(lyric_rows, ensure_ascii=False), encoding="utf-8")
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    result = retrieve_few_shot_examples(
        UserInput(raw_intent="分手后深夜想发消息又克制住"),
        repo_root=tmp_path,
        top_k=3,
        return_metadata=True,
    )

    assert isinstance(result, dict)
    assert result["profile_vote"] == "urban_introspective"
    assert result["vote_confidence"] >= (2 / 3)


def test_retriever_includes_profile_confidence_in_samples(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = []
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "profile_tag": "urban_introspective",
            "profile_confidence": 0.88,
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "不再拨通",
            "emotion_tags": ["distance", "regret"],
            "profile_tag": "urban_introspective",
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
    ]
    (corpus / "poetry_classical.json").write_text(json.dumps(poetry_rows, ensure_ascii=False), encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(json.dumps(lyric_rows, ensure_ascii=False), encoding="utf-8")
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    result = retrieve_few_shot_examples(
        UserInput(raw_intent="分手后深夜想发消息又克制住"),
        repo_root=tmp_path,
        top_k=3,
        return_metadata=True,
    )
    assert isinstance(result, dict)
    assert all("profile_confidence" in sample for sample in result["samples"])
    assert any(sample["profile_confidence"] == 0.88 for sample in result["samples"])


def test_corpus_balance_check_reports_warnings_when_under_minimum(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = []
    lyric_rows = []
    (corpus / "poetry_classical.json").write_text(json.dumps(poetry_rows, ensure_ascii=False), encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(json.dumps(lyric_rows, ensure_ascii=False), encoding="utf-8")
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    report = corpus_balance_check(tmp_path)
    assert isinstance(report, dict)
    assert len(report["warnings"]) >= 1
    assert "urban_introspective" in report["counts"]


def test_corpus_balance_keeps_classical_rows_with_rule_c7_only(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = [
        {
            "source_id": "github:chinese-poetry/chinese-poetry:json/poet.tang.1.json#1",
            "type": "classical_poem",
            "title": "春晓",
            "author": "孟浩然",
            "emotion_tags": ["nostalgia", "restraint", "imagery"],
            "profile_tag": "classical_restraint",
            "valence": "neutral",
            "learn_point": "学习意象并置与留白表达，避免直白抒情",
            "do_not_copy": "禁止复写来源文本原句与意象排列顺序",
            "content": "春眠不觉晓，处处闻啼鸟。",
        }
    ]
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "profile_tag": "urban_introspective",
            "valence": "negative",
            "learn_point": "保留克制语气并用动作推进情绪",
            "do_not_copy": "不要复写原句与段落顺序",
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "不再拨通",
            "emotion_tags": ["distance", "regret"],
            "profile_tag": "urban_introspective",
            "valence": "negative",
            "learn_point": "保留克制语气并用动作推进情绪",
            "do_not_copy": "不要复写原句与段落顺序",
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
    ]
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    report = corpus_balance_check(tmp_path)

    assert report["counts"]["classical_restraint"] == 1


def test_retriever_exposes_corpus_balance_and_monoculture_flags(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = [
        {
            "source_id": "poem-jys-001",
            "type": "classical_poem",
            "title": "静夜思",
            "emotion_tags": ["nostalgia", "restraint"],
            "profile_tag": "classical_restraint",
            "content": "举头望明月，低头思故乡，夜色慢慢凉。",
        }
    ]
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "profile_tag": "urban_introspective",
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "不再拨通",
            "emotion_tags": ["distance", "regret"],
            "profile_tag": "urban_introspective",
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
    ]
    (corpus / "poetry_classical.json").write_text(json.dumps(poetry_rows, ensure_ascii=False), encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(json.dumps(lyric_rows, ensure_ascii=False), encoding="utf-8")
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    result = retrieve_few_shot_examples(
        UserInput(raw_intent="分手后深夜想发消息又克制住"),
        repo_root=tmp_path,
        top_k=3,
        return_metadata=True,
    )

    assert isinstance(result, dict)
    assert "corpus_balance" in result
    assert "corpus_monoculture_risk" in result


def test_retriever_profile_override_prefers_same_profile_rows(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = []
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "profile_tag": "urban_introspective",
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "不再拨通",
            "emotion_tags": ["distance", "regret"],
            "profile_tag": "urban_introspective",
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
        {
            "source_id": "lyric-up-201",
            "type": "modern_lyric",
            "title": "向光走",
            "emotion_tags": ["uplift", "get-up"],
            "profile_tag": "uplift_pop",
            "content": "把窗推开，朝着亮处走。",
        },
    ]
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    result = retrieve_few_shot_examples(
        UserInput(raw_intent="想写深夜克制的遗憾", profile_override="urban_introspective"),
        repo_root=tmp_path,
        top_k=3,
        return_metadata=True,
    )

    assert isinstance(result, dict)
    assert result.get("fallback_level") == "override_profile_only"
    assert len(result["samples"]) >= 2
    assert all(sample.get("profile_tag") == "urban_introspective" for sample in result["samples"])


def test_retriever_profile_override_fallbacks_when_same_profile_insufficient(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = []
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "profile_tag": "urban_introspective",
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-up-201",
            "type": "modern_lyric",
            "title": "向光走",
            "emotion_tags": ["uplift", "get-up"],
            "profile_tag": "uplift_pop",
            "content": "把窗推开，朝着亮处走。",
        },
        {
            "source_id": "lyric-cd-301",
            "type": "modern_lyric",
            "title": "拍点起跳",
            "emotion_tags": ["dance", "release"],
            "profile_tag": "club_dance",
            "content": "鼓点往前推，脚步贴着拍。",
        },
    ]
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    result = retrieve_few_shot_examples(
        UserInput(raw_intent="想写深夜克制的遗憾", profile_override="urban_introspective"),
        repo_root=tmp_path,
        top_k=3,
        return_metadata=True,
    )

    assert isinstance(result, dict)
    assert result.get("fallback_level") == "fallback_to_global"
    assert len(result["samples"]) >= 2


def test_retriever_prefers_clean_corpus_when_available(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    clean = corpus / "_clean"
    corpus.mkdir(parents=True, exist_ok=True)
    clean.mkdir(parents=True, exist_ok=True)

    (corpus / "poetry_classical.json").write_text("[]", encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "lyric-modern-raw",
                    "type": "modern_lyric",
                    "title": "raw",
                    "emotion_tags": ["breakup"],
                    "content": "原始语料不应被读取",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (clean / "poetry_classical.json").write_text("[]", encoding="utf-8")
    (clean / "lyrics_modern_zh.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "lyric-modern-clean-1",
                    "type": "modern_lyric",
                    "title": "clean one",
                    "emotion_tags": ["breakup", "late-night"],
                    "profile_tag": "urban_introspective",
                    "valence": "negative",
                    "learn_point": "保留克制语气并用动作推进情绪",
                    "do_not_copy": "不要复写原句与段落顺序",
                    "profile_confidence": 0.9,
                    "content": "对话框停在最后一句，指尖仍然悬着。",
                },
                {
                    "source_id": "lyric-modern-clean-2",
                    "type": "modern_lyric",
                    "title": "clean two",
                    "emotion_tags": ["distance", "regret"],
                    "profile_tag": "urban_introspective",
                    "valence": "negative",
                    "learn_point": "保留克制语气并用动作推进情绪",
                    "do_not_copy": "不要复写原句与段落顺序",
                    "profile_confidence": 0.9,
                    "content": "手在拨出前停住，呼吸也跟着发颤。",
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

    assert all("clean" in row["source_id"] for row in items)


def test_retriever_fails_loud_when_clean_corpus_missing(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / "poetry_classical.json").write_text("[]", encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text("[]", encoding="utf-8")

    try:
        retrieve_few_shot_examples(
            UserInput(raw_intent="分手后深夜想发消息又克制住"),
            repo_root=tmp_path,
            top_k=3,
        )
    except RuntimeError as err:
        assert "clean corpus missing" in str(err)
        return

    raise AssertionError("expected RuntimeError when clean corpus is missing")


def test_retriever_raises_when_preinjection_validation_leaves_less_than_two(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = []
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "bad one",
            "emotion_tags": ["breakup"],
            "profile_tag": "urban_introspective",
            "valence": "negative",
            "learn_point": "短",
            "do_not_copy": "",
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "bad two",
            "emotion_tags": ["regret"],
            "profile_tag": "urban_introspective",
            "valence": "negative",
            "learn_point": "保留克制语气并用动作推进情绪",
            "do_not_copy": "",
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
    ]
    (corpus / "poetry_classical.json").write_text(json.dumps(poetry_rows, ensure_ascii=False), encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(json.dumps(lyric_rows, ensure_ascii=False), encoding="utf-8")
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    with pytest.raises(InsufficientQualityFewShotError):
        retrieve_few_shot_examples(
            UserInput(raw_intent="分手后深夜想发消息又克制住"),
            repo_root=tmp_path,
            top_k=3,
            return_metadata=True,
        )


def test_retriever_does_not_relint_rows_on_selection_path(monkeypatch, tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    poetry_rows = []
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "clean one",
            "emotion_tags": ["breakup", "late-night"],
            "profile_tag": "urban_introspective",
            "valence": "negative",
            "learn_point": "保留克制语气并用动作推进情绪",
            "do_not_copy": "不要复写原句与段落顺序",
            "profile_confidence": 0.9,
            "content": "对话框停在最后一句，指尖仍然悬着。",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "clean two",
            "emotion_tags": ["distance", "regret"],
            "profile_tag": "urban_introspective",
            "valence": "negative",
            "learn_point": "保留克制语气并用动作推进情绪",
            "do_not_copy": "不要复写原句与段落顺序",
            "profile_confidence": 0.9,
            "content": "手在拨出前停住，呼吸也跟着发颤。",
        },
    ]
    (corpus / "poetry_classical.json").write_text(json.dumps(poetry_rows, ensure_ascii=False), encoding="utf-8")
    (corpus / "lyrics_modern_zh.json").write_text(json.dumps(lyric_rows, ensure_ascii=False), encoding="utf-8")
    _write_clean_corpus(corpus, poetry_rows, lyric_rows)

    from src import retriever as retriever_mod

    call_count = {"n": 0}
    real_lint = retriever_mod.lint_corpus_row

    def _wrapped_lint(row, *, mode="ingestion"):
        call_count["n"] += 1
        return real_lint(row, mode=mode)

    monkeypatch.setattr(retriever_mod, "lint_corpus_row", _wrapped_lint)

    result = retrieve_few_shot_examples(
        UserInput(raw_intent="分手后深夜想发消息又克制住"),
        repo_root=tmp_path,
        top_k=3,
        return_metadata=True,
    )

    assert isinstance(result, dict)
    assert len(result["samples"]) == 2
    assert call_count["n"] == 2
