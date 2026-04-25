from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.ingest_github_corpus import (
    build_urban_introspective_rows_from_raw,
    build_uplift_pop_rows_from_raw,
    write_proof_file,
)
from scripts.corpus_quality_lint import lint_corpus_row


def test_build_uplift_pop_rows_from_raw_generates_github_source_ids(tmp_path: Path) -> None:
    raw_repo = tmp_path / "raw_repo"
    (raw_repo / "artist_a").mkdir(parents=True, exist_ok=True)
    (raw_repo / "artist_b").mkdir(parents=True, exist_ok=True)

    (raw_repo / "artist_a" / "song_1.txt").write_text(
        "天空刚亮就出发\n把昨天放下\n向前走\n今天会更好\n",
        encoding="utf-8",
    )
    (raw_repo / "artist_b" / "song_2.txt").write_text(
        "风吹过街口\n我们抬头\n把心打开\n一路唱到天亮\n",
        encoding="utf-8",
    )

    rows = build_uplift_pop_rows_from_raw(
        raw_repo,
        owner="dengxiuqi",
        repo="Chinese-Lyric-Corpus",
        target_count=2,
    )

    assert len(rows) == 2
    assert all(str(row["source_id"]).startswith("github:dengxiuqi/Chinese-Lyric-Corpus:") for row in rows)
    assert all(row["profile_tag"] == "uplift_pop" for row in rows)


def test_write_proof_file_records_commit_and_samples(tmp_path: Path) -> None:
    proof_path = tmp_path / "proof.json"
    sample_rows = [
        {
            "source_id": "github:dengxiuqi/Chinese-Lyric-Corpus:artist_a/song_1.txt",
            "title": "song_1",
        },
        {
            "source_id": "github:dengxiuqi/Chinese-Lyric-Corpus:artist_b/song_2.txt",
            "title": "song_2",
        },
    ]

    write_proof_file(
        proof_path=proof_path,
        owner="dengxiuqi",
        repo="Chinese-Lyric-Corpus",
        commit_sha="abc123def456",
        rows=sample_rows,
        rejected_count=7,
    )

    payload = json.loads(proof_path.read_text(encoding="utf-8"))
    assert payload["repo"] == "https://github.com/dengxiuqi/Chinese-Lyric-Corpus"
    assert payload["commit_sha"] == "abc123def456"
    assert payload["accepted_count"] == 2
    assert payload["rejected_count"] == 7
    assert len(payload["sample_source_ids"]) == 2


def test_build_uplift_pop_rows_from_zip_archive(tmp_path: Path) -> None:
    raw_repo = tmp_path / "raw_repo"
    raw_repo.mkdir(parents=True, exist_ok=True)
    archive = raw_repo / "Chinese_Lyrics.zip"

    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "Chinese_Lyrics/artist_x/song_a.txt",
            "把窗推开\n迎着光\n今天继续向前\n一起唱\n",
        )
        zf.writestr(
            "Chinese_Lyrics/artist_y/song_b.txt",
            "抬头看天\n步伐变快\n把心点亮\n现在就出发\n",
        )

    rows = build_uplift_pop_rows_from_raw(
        raw_repo,
        owner="gaussic",
        repo="Chinese-Lyric-Corpus",
        target_count=2,
    )

    assert len(rows) == 2
    assert all("Chinese_Lyrics/" in str(row["source_id"]) for row in rows)


def test_build_uplift_pop_rows_are_runtime_lint_clean(tmp_path: Path) -> None:
    raw_repo = tmp_path / "raw_repo"
    (raw_repo / "artist_a").mkdir(parents=True, exist_ok=True)

    (raw_repo / "artist_a" / "song_ok.txt").write_text(
        "把门推开\n朝着亮处走\n我们一起唱\n把今天点亮\n",
        encoding="utf-8",
    )
    (raw_repo / "artist_a" / "song_bad.txt").write_text(
        "光 光 光\n亮 亮 亮\n天 天 天\n星 星 星\n",
        encoding="utf-8",
    )

    rows = build_uplift_pop_rows_from_raw(
        raw_repo,
        owner="dengxiuqi",
        repo="Chinese-Lyric-Corpus",
        target_count=5,
    )

    assert len(rows) == 1
    assert rows[0]["source_id"].endswith("song_ok.txt")
    assert lint_corpus_row(rows[0]).passed is True


def test_build_urban_introspective_rows_from_raw_generates_github_ids(tmp_path: Path) -> None:
    raw_repo = tmp_path / "raw_repo"
    (raw_repo / "artist_a").mkdir(parents=True, exist_ok=True)

    (raw_repo / "artist_a" / "song_urban_1.txt").write_text(
        "夜里走到街口\n把话删掉\n手机亮着又熄灭\n我还是没有按下发送\n",
        encoding="utf-8",
    )
    (raw_repo / "artist_a" / "song_urban_2.txt").write_text(
        "凌晨的地铁还在响\n把名字停在草稿\n呼吸慢下来\n我把手放回口袋\n",
        encoding="utf-8",
    )

    rows = build_urban_introspective_rows_from_raw(
        raw_repo,
        owner="gaussic",
        repo="Chinese-Lyric-Corpus",
        target_count=2,
    )

    assert len(rows) == 2
    assert all(str(row["source_id"]).startswith("github:gaussic/Chinese-Lyric-Corpus:") for row in rows)
    assert all(row["profile_tag"] == "urban_introspective" for row in rows)
