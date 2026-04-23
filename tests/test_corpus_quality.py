from __future__ import annotations

import json

from scripts.corpus_quality_lint import lint_corpus_row
from scripts.run_corpus_ingestion import run_ingestion


def test_corpus_quality_lint_rejects_three_digit_sequences() -> None:
    row = {
        "source_id": "lyric-up-001",
        "type": "modern_lyric",
        "title": "明亮流行001",
        "emotion_tags": ["joy"],
        "profile_tag": "uplift_pop",
        "valence": "positive",
        "learn_point": "学习具象描写",
        "content": "清晨第001束光落肩，笑着把今天唱开。",
    }

    report = lint_corpus_row(row)

    assert report.passed is False
    assert "RULE_C1" in report.failed_rules


def test_corpus_quality_lint_accepts_valid_row() -> None:
    row = {
        "source_id": "lyric-up-a01",
        "type": "modern_lyric",
        "title": "明亮流行晨光",
        "emotion_tags": ["joy", "sunshine"],
        "profile_tag": "uplift_pop",
        "valence": "positive",
        "learn_point": "以具象晨光起句并保持动词推进",
        "content": "清晨风起肩头，笑着把今天唱开。",
    }

    report = lint_corpus_row(row)

    assert report.passed is True
    assert report.failed_rules == []


def test_run_ingestion_writes_clean_rejected_and_report(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "source_id": "lyric-up-a01",
            "type": "modern_lyric",
            "title": "明亮流行晨光",
            "emotion_tags": ["joy", "sunshine"],
            "profile_tag": "uplift_pop",
            "valence": "positive",
            "learn_point": "以具象晨光起句并保持动词推进",
            "content": "清晨风起肩头，笑着把今天唱开。",
        },
        {
            "source_id": "lyric-up-a02",
            "type": "modern_lyric",
            "title": "明亮流行晚风",
            "emotion_tags": ["joy"],
            "profile_tag": "uplift_pop",
            "valence": "positive",
            "learn_point": "用晚风推进节奏并保持动作感",
            "content": "晚风掠过肩头，我们并肩把路走亮。",
        },
    ]

    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (corpus_dir / "poetry_classical.json").write_text("[]", encoding="utf-8")

    summary = run_ingestion(repo_root=tmp_path, strict=False)

    clean_file = tmp_path / "corpus" / "_clean" / "lyrics_modern_zh.json"
    rejected_file = tmp_path / "corpus" / "_rejected" / "lyrics_modern_zh.json"
    report_file = tmp_path / "corpus" / "_ingestion_report.md"

    assert clean_file.exists()
    assert rejected_file.exists()
    assert report_file.exists()
    assert summary["total"] == 2
    assert summary["accepted"] == 2
    assert summary["rejected"] == 0


def test_run_ingestion_enriches_rows_and_strict_mode_reports_rejections(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "source_id": "lyric-up-001",
            "type": "modern_lyric",
            "title": "明亮流行001",
            "emotion_tags": ["joy"],
            "content": "清晨第001束光落肩，笑着把今天唱开。",
        }
    ]
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (corpus_dir / "poetry_classical.json").write_text("[]", encoding="utf-8")

    summary = run_ingestion(repo_root=tmp_path, strict=True)

    clean_rows = json.loads((tmp_path / "corpus" / "_clean" / "lyrics_modern_zh.json").read_text(encoding="utf-8"))
    report_text = (tmp_path / "corpus" / "_ingestion_report.md").read_text(encoding="utf-8")
    assert summary["rejected"] == 0
    assert summary["accepted"] == 1
    assert clean_rows[0]["profile_tag"] == "uplift_pop"
    assert clean_rows[0]["valence"] == "positive"
    assert len(clean_rows[0]["learn_point"]) >= 5
    assert "001" not in clean_rows[0]["content"]
    assert "001" not in clean_rows[0]["source_id"]
    assert "- none: 0" in report_text
