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


def test_run_ingestion_report_includes_source_family_pass_counts(tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "github:gaussic/Chinese-Lyric-Corpus:a.txt",
                    "type": "modern_lyric",
                    "title": "向光走",
                    "emotion_tags": ["uplift", "joy", "forward"],
                    "profile_tag": "uplift_pop",
                    "valence": "positive",
                    "learn_point": "用动作动词推进句群并在副歌处抬升情绪落点",
                    "do_not_copy": "不要复写原句与段落顺序",
                    "content": "把门推开\n朝着亮处走\n把今天唱开\n我们一起向前",
                    "source_family": "golden_lyricist",
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (corpus_dir / "poetry_classical.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "github:Li1Fan/chinese-idiom:data/idiom.json#1",
                    "type": "classical_poem",
                    "title": "榜上无名",
                    "emotion_tags": ["imagery", "compression", "restraint"],
                    "profile_tag": "classical_restraint",
                    "valence": "mixed",
                    "learn_point": "短语锚点用于副歌收束时的高压缩表达",
                    "do_not_copy": "不要复写原句与段落顺序",
                    "content": "榜上无名",
                    "source_family": "chengyu",
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    run_ingestion(repo_root=tmp_path, strict=False)
    report = (corpus_dir / "_ingestion_report.md").read_text(encoding="utf-8")

    assert "## source_family_pass_counts" in report
    assert "- chengyu: 1" in report
    assert "- golden_lyricist: 1" in report


def test_corpus_quality_lint_rejects_idiom_entry_longer_than_eight_chars() -> None:
    row = {
        "source_id": "idiom:custom:0001",
        "type": "classical_poem",
        "title": "晴天总会在明早到来呀",
        "emotion_tags": ["hope"],
        "profile_tag": "classical_restraint",
        "valence": "mixed",
        "learn_point": "短句锚点要凝练",
        "do_not_copy": "不要复写原句与段落顺序",
        "content": "晴天总会在明早到来呀",
        "source_family": "chengyu",
    }

    report = lint_corpus_row(row)

    assert report.passed is False
    assert "RULE_C9" in report.failed_rules


def test_corpus_quality_lint_rejects_garbled_idiom_text() -> None:
    row = {
        "source_id": "idiom:custom:0002",
        "type": "classical_poem",
        "title": "风月无边",
        "emotion_tags": ["nostalgia"],
        "profile_tag": "classical_restraint",
        "valence": "mixed",
        "learn_point": "意象句要避免乱码",
        "do_not_copy": "不要复写原句与段落顺序",
        "content": "风月無邊��",
        "source_family": "chengyu",
    }

    report = lint_corpus_row(row)

    assert report.passed is False
    assert "RULE_C10" in report.failed_rules


def test_classical_rows_do_not_trigger_modern_r16_blacklist() -> None:
    classical_row = {
        "source_id": "classical:caigentan:001",
        "type": "classical_poem",
        "title": "菜根谭语录",
        "emotion_tags": ["restraint"],
        "profile_tag": "classical_restraint",
        "valence": "mixed",
        "learn_point": "文言句法用于哲学升华",
        "do_not_copy": "不要复写原句与段落顺序",
        "content": "各自安好，且看浮云，且听松风。",
    }
    modern_row = {
        "source_id": "modern:urban:001",
        "type": "modern_lyric",
        "title": "都市夜话",
        "emotion_tags": ["breakup"],
        "profile_tag": "urban_introspective",
        "valence": "negative",
        "learn_point": "口语化叙事避免模板陈词",
        "do_not_copy": "不要复写原句与段落顺序",
        "content": "我们说好各自安好，再走回原点。",
    }

    classical_report = lint_corpus_row(classical_row)
    modern_report = lint_corpus_row(modern_row)

    assert "RULE_R16_MODERN" not in classical_report.failed_rules
    assert "RULE_R16_MODERN" in modern_report.failed_rules
