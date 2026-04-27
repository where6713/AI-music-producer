from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
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
        "do_not_copy": "不要复写原句与段落顺序",
        "content": "清晨风起肩头，笑着把今天唱开。",
    }

    report = lint_corpus_row(row)

    assert report.passed is True
    assert report.failed_rules == []


def test_corpus_quality_lint_rejects_missing_do_not_copy() -> None:
    row = {
        "source_id": "lyric-up-a02",
        "type": "modern_lyric",
        "title": "明亮流行夜航",
        "emotion_tags": ["joy", "drive"],
        "profile_tag": "uplift_pop",
        "valence": "positive",
        "learn_point": "保留动作推进并给出场景锚点",
        "content": "我们并肩往前走，把夜色唱亮。",
    }

    report = lint_corpus_row(row)

    assert report.passed is False
    assert "RULE_C8" in report.failed_rules


def test_corpus_quality_lint_rejects_chinese_digit_sequences() -> None:
    row = {
        "source_id": "lyric-up-zhnum",
        "type": "modern_lyric",
        "title": "明亮流行零零零",
        "emotion_tags": ["joy"],
        "profile_tag": "uplift_pop",
        "valence": "positive",
        "learn_point": "保持明亮节奏并强化动词驱动",
        "do_not_copy": "不要复写原句与段落顺序",
        "content": "清晨第零零零束光落肩，笑着把今天唱开。",
    }

    report = lint_corpus_row(row)

    assert report.passed is False
    assert "RULE_C1" in report.failed_rules


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
            "do_not_copy": "不要复写原句与段落顺序",
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
            "do_not_copy": "不要复写原句与段落顺序",
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


def test_run_ingestion_strict_rejects_digit_sample_and_reports_rule_c1(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "source_id": "lyric-up-001",
            "type": "modern_lyric",
            "title": "明亮流行001",
            "emotion_tags": ["joy"],
            "profile_tag": "uplift_pop",
            "valence": "positive",
            "learn_point": "保持明亮节奏并强化动词驱动",
            "content": "清晨第001束光落肩，笑着把今天唱开。",
        }
    ]
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (corpus_dir / "poetry_classical.json").write_text("[]", encoding="utf-8")

    summary = run_ingestion(repo_root=tmp_path, strict=True)

    rejected_rows = json.loads(
        (tmp_path / "corpus" / "_rejected" / "lyrics_modern_zh.json").read_text(encoding="utf-8")
    )
    report_text = (tmp_path / "corpus" / "_ingestion_report.md").read_text(encoding="utf-8")

    assert summary["rejected"] == 1
    assert summary["accepted"] == 0
    assert len(rejected_rows) == 1
    assert "RULE_C1" in rejected_rows[0]["_rejected_rules"]
    assert "RULE_C1" in report_text


def test_ingestion_cli_strict_exits_zero_when_partial_rejected(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "source_id": "lyric-up-good",
            "type": "modern_lyric",
            "title": "明亮流行晨光",
            "emotion_tags": ["joy"],
            "profile_tag": "uplift_pop",
            "valence": "positive",
            "learn_point": "保持明亮节奏并强化动词驱动",
            "do_not_copy": "不要复写原句与段落顺序",
            "content": "晚风掠过肩头，我们并肩把路走亮。",
        },
        {
            "source_id": "lyric-up-002",
            "type": "modern_lyric",
            "title": "明亮流行002",
            "emotion_tags": ["joy"],
            "profile_tag": "uplift_pop",
            "valence": "positive",
            "learn_point": "保持明亮节奏并强化动词驱动",
            "do_not_copy": "不要复写原句与段落顺序",
            "content": "清晨第002束光落肩，笑着把今天唱开。",
        }
    ]
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (corpus_dir / "poetry_classical.json").write_text("[]", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_corpus_ingestion.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--strict"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0


def test_ingestion_cli_strict_exits_non_zero_when_clean_empty(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "source_id": "lyric-up-bad",
            "type": "modern_lyric",
            "title": "占位样本",
            "emotion_tags": ["joy"],
            "profile_tag": "uplift_pop",
            "valence": "positive",
            "learn_point": "sample",
            "content": "placeholder",
        }
    ]
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (corpus_dir / "poetry_classical.json").write_text("[]", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_corpus_ingestion.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--strict"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1


def test_run_ingestion_report_includes_github_uplift_proof_when_present(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    clean_dir = corpus_dir / "_clean"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    payload = [
        {
            "source_id": "github:dengxiuqi/Chinese-Lyric-Corpus:artist/song.txt",
            "type": "modern_lyric",
            "title": "向光走",
            "emotion_tags": ["uplift", "get-up"],
            "profile_tag": "uplift_pop",
            "valence": "positive",
            "learn_point": "保持动词推进并给出明亮场景",
            "do_not_copy": "不要复写原句与段落顺序",
            "content": "把窗推开，朝着亮处走。",
        }
    ]
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (corpus_dir / "poetry_classical.json").write_text("[]", encoding="utf-8")

    proof_payload = {
        "repo": "https://github.com/dengxiuqi/Chinese-Lyric-Corpus",
        "commit_sha": "abc123def456",
        "fetched_at": "2026-04-25T00:00:00+00:00",
        "accepted_count": 1,
        "rejected_count": 0,
        "sample_source_ids": ["github:dengxiuqi/Chinese-Lyric-Corpus:artist/song.txt"],
    }
    (clean_dir / "_github_uplift_pop_proof.json").write_text(
        json.dumps(proof_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    run_ingestion(repo_root=tmp_path, strict=False)
    report = (corpus_dir / "_ingestion_report.md").read_text(encoding="utf-8")

    assert "## github_uplift_pop_proof" in report
    assert "repo: https://github.com/dengxiuqi/Chinese-Lyric-Corpus" in report
    assert "commit_sha: abc123def456" in report


def test_run_ingestion_report_includes_multiple_github_profile_proofs(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    clean_dir = corpus_dir / "_clean"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    payload = [
        {
            "source_id": "github:gaussic/Chinese-Lyric-Corpus:path/a.txt",
            "type": "modern_lyric",
            "title": "夜里",
            "emotion_tags": ["breakup"],
            "profile_tag": "urban_introspective",
            "valence": "negative",
            "learn_point": "保持克制",
            "do_not_copy": "不要复写原句与段落顺序",
            "content": "夜里走到街口，把话删掉。",
        }
    ]
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (corpus_dir / "poetry_classical.json").write_text("[]", encoding="utf-8")

    (clean_dir / "_github_uplift_pop_proof.json").write_text(
        json.dumps(
            {
                "repo": "https://github.com/gaussic/Chinese-Lyric-Corpus",
                "commit_sha": "sha-up",
                "fetched_at": "2026-04-25T00:00:00+00:00",
                "accepted_count": 10,
                "rejected_count": 3,
                "sample_source_ids": ["github:gaussic/Chinese-Lyric-Corpus:path/up.txt"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (clean_dir / "_github_urban_introspective_proof.json").write_text(
        json.dumps(
            {
                "repo": "https://github.com/gaussic/Chinese-Lyric-Corpus",
                "commit_sha": "sha-ui",
                "fetched_at": "2026-04-25T00:00:00+00:00",
                "accepted_count": 20,
                "rejected_count": 5,
                "sample_source_ids": ["github:gaussic/Chinese-Lyric-Corpus:path/ui.txt"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    run_ingestion(repo_root=tmp_path, strict=False)
    report = (corpus_dir / "_ingestion_report.md").read_text(encoding="utf-8")

    assert "## github_uplift_pop_proof" in report
    assert "## github_urban_introspective_proof" in report
    assert "commit_sha: sha-up" in report
    assert "commit_sha: sha-ui" in report


def test_run_ingestion_allows_classical_rule_c7_only_rows(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    poetry_payload = [
        {
            "source_id": "github:chinese-poetry/chinese-poetry:json/poet.tang.1.json#1",
            "type": "classical_poem",
            "title": "春晓",
            "author": "孟浩然",
            "emotion_tags": ["nostalgia", "restraint", "imagery"],
            "profile_tag": "classical_restraint",
            "valence": "neutral",
            "learn_point": "学习意象并置与留白表达，避免直白抒情",
            "do_not_copy": "不要复写原句与段落顺序",
            "content": "春眠不觉晓\n处处闻啼鸟",
        }
    ]
    (corpus_dir / "poetry_classical.json").write_text(
        json.dumps(poetry_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (corpus_dir / "lyrics_modern_zh.json").write_text("[]", encoding="utf-8")

    summary = run_ingestion(repo_root=tmp_path, strict=True)

    assert summary["accepted"] == 1
    assert summary["rejected"] == 0
