from __future__ import annotations

import json
from pathlib import Path

from scripts import auto_tag_golden_anchors as anchors


def test_extract_chengyu_entries_enforces_max_len_and_filters_garbled() -> None:
    payload = {
        "中流砥柱": "比喻能担当重任，起中坚作用",
        "风月無邊��": "garbled",
        "晴天总会在明早到来呀": "too long",
    }

    rows = anchors.extract_chengyu_entries(payload)

    contents = [row["content"] for row in rows]
    assert "中流砥柱" in contents
    assert "风月無邊��" not in contents
    assert "晴天总会在明早到来呀" not in contents


def test_build_row_for_classical_uses_classical_profile_and_quality_hints() -> None:
    row = anchors.build_row(
        source_id="github:hanzhaodeng/chinese-ancient-text:caigentan#1",
        source_type="classical_poem",
        title="菜根谭",
        content="宠辱不惊，闲看庭前花开花落。",
        emotion_tags=["restraint", "equanimity"],
        profile_tag="classical_restraint",
        valence="mixed",
        learn_point="借景抒怀与对照构句结合，增强留白后的回味。",
        do_not_copy="禁止复写来源文本原句与意象排列顺序。",
    )

    assert row["type"] == "classical_poem"
    assert row["profile_tag"] == "classical_restraint"
    assert "借景" in row["learn_point"]


def test_parse_modern_lyric_lines_picks_valid_named_tracks() -> None:
    text = """
歌名: 红豆
作词: 林夕
歌词:
还没好好的感受 雪花绽放的气候
我们一起颤抖 会更明白 什么是温柔

歌名: 浮夸
作词: 黄伟文
歌词:
你叫我做浮夸吧 加几声嘘声也不怕
"""

    rows = anchors.parse_modern_lyric_lines(text, allowed_lyricists={"林夕", "方文山"})

    assert len(rows) == 1
    assert rows[0]["title"] == "红豆"
    assert rows[0]["lyricist"] == "林夕"


def test_collect_zengguang_rows_reads_liuxiaoxiao_real_text(tmp_path: Path) -> None:
    repo_root = tmp_path
    text_path = repo_root / "corpus" / "_raw" / "github" / "liuxiaoxiao666__zeng_guang_xian_wen" / "增广贤文.txt"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text("观今宜鉴古，无古不成今。\n知己知彼，将心比心。\n", encoding="utf-8")

    rows = anchors._collect_zengguang_rows(repo_root)

    assert len(rows) == 2
    assert all(row["source_family"] == "zengguangxianwen" for row in rows)
    assert all(str(row["source_id"]).startswith("github:liuxiaoxiao666/zeng_guang_xian_wen:") for row in rows)


def test_collect_caigentan_rows_reads_hanzhaodeng_json(tmp_path: Path) -> None:
    raw_root = tmp_path / "corpus" / "_raw" / "github"
    target = raw_root / "hanzhaodeng__chinese-ancient-text" / "菜根谭.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "name": "菜根谭",
                "articles": [
                    {"title": "修身", "content": ["欲做精金美玉的人品，定从烈火中煅来。", "一念错，便觉百行皆非。"]}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rows = anchors._collect_caigentan_rows(raw_root)

    assert len(rows) == 2
    assert all(row["source_family"] == "caigentan" for row in rows)
    assert all(str(row["source_id"]).startswith("github:hanzhaodeng/chinese-ancient-text:菜根谭.json#") for row in rows)


def test_collect_idiom_rows_reads_li1fan_idiom_json(tmp_path: Path) -> None:
    repo_root = tmp_path
    idiom_path = repo_root / "corpus" / "_raw" / "github" / "Li1Fan__chinese-idiom" / "data" / "idiom.json"
    idiom_path.parent.mkdir(parents=True, exist_ok=True)
    idiom_path.write_text(
        json.dumps(
            [
                {"word": "傍柳随花", "explanation": "比喻狎妓。"},
                {"word": "榜上无名", "explanation": "泛指落选。"},
                {"word": "晴天总会在明早到来呀", "explanation": "too long"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rows = anchors._collect_idiom_rows(repo_root, target_count=10)

    assert [row["content"] for row in rows] == ["傍柳随花", "榜上无名"]
    assert all(row["source_family"] == "chengyu" for row in rows)
    assert all(str(row["source_id"]).startswith("github:Li1Fan/chinese-idiom:data/idiom.json#") for row in rows)


def test_backfill_source_family_for_existing_classical_rows() -> None:
    rows = [
        {
            "source_id": "github:chinese-poetry/chinese-poetry:元曲/yuanqu.json#7",
            "type": "classical_poem",
            "profile_tag": "classical_restraint",
            "content": "测试",
        },
        {
            "source_id": "github:Li1Fan/chinese-idiom:data/idiom.json#3",
            "type": "classical_poem",
            "profile_tag": "classical_restraint",
            "content": "榜上无名",
        },
    ]

    patched = anchors._backfill_source_family(rows)

    assert patched[0]["source_family"] == "poetry_2000"
    assert patched[1]["source_family"] == "chengyu"


def test_merge_rows_by_source_id_dedupes_repeated_entries() -> None:
    base = [
        {"source_id": "github:a/repo:path#1", "content": "old"},
        {"source_id": "github:a/repo:path#2", "content": "stable"},
    ]
    incoming = [
        {"source_id": "github:a/repo:path#1", "content": "new"},
        {"source_id": "github:a/repo:path#3", "content": "add"},
    ]

    merged = anchors._merge_rows_by_source_id(base, incoming)

    assert len(merged) == 3
    by_id = {str(row.get("source_id")): row for row in merged}
    assert by_id["github:a/repo:path#1"]["content"] == "new"
    assert by_id["github:a/repo:path#2"]["content"] == "stable"
    assert by_id["github:a/repo:path#3"]["content"] == "add"
