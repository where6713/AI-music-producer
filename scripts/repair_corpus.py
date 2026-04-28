"""
repair_corpus.py — 修复 corpus/ 下两个主语料文件的已知质量问题

修复项：
  lyrics_modern_zh.json:
    F1. source_id / title cp437 乱码还原为 UTF-8 中文
    F2. learn_point 截断：去掉【原文佐证】及之后的内容，只保留前置指导句
    F3. 去除 content 头部的元数据行（曲/词/编/歌曲 开头的行）
    F4. 标记粤语条目（添加 lang_note 字段），不删除（保留供未来过滤）

  poetry_classical.json:
    F5. 删除 content 字符数 < 20 的碎片条目

用法：
    python -m scripts.repair_corpus [--dry-run] [--out-dir corpus]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


# ── 编码修复 ────────────────────────────────────────────────────────────────

def _fix_cp437(s: str) -> str:
    """cp437 误读为 unicode 的字符串 → 还原为正确 UTF-8 中文。"""
    try:
        return s.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def fix_source_id(sid: str) -> str:
    """修复 source_id 路径段乱码，保留 github:owner/repo: 前缀和 #author 后缀。"""
    m = re.match(r"^(github:[^:]+:)", sid)
    if not m:
        return sid
    prefix = m.group(1)
    rest = sid[len(prefix):]
    if "#" in rest:
        path_part, author = rest.rsplit("#", 1)
        return prefix + _fix_cp437(path_part) + "#" + author
    return prefix + _fix_cp437(rest)


# ── learn_point 截断 ─────────────────────────────────────────────────────────

_EVIDENCE_MARKERS = re.compile(
    r"【原文佐证】|【原文】|【佐证】|【示例】|【例句】|【例文】"
)

def clean_learn_point(lp: str) -> str:
    """
    去掉【原文佐证】及之后的全部内容。
    如果本身只有一句（无佐证块），原样返回。
    如果以【分析】开头，去掉【分析】：前缀，只保留分析正文第一句。
    """
    # 去掉【分析】：前缀
    lp = re.sub(r"^【分析】[：:]?\s*", "", lp.strip())
    # 截断到【原文佐证】等标记之前
    m = _EVIDENCE_MARKERS.search(lp)
    if m:
        lp = lp[: m.start()].strip()
    # 再截断到第一个句号/。/换行，确保只保留一句
    m2 = re.search(r"[。\n]", lp)
    if m2:
        lp = lp[: m2.start()].strip()
    # 去掉行尾多余标点
    lp = lp.rstrip("，、：: ")
    return lp if lp else "学习用具体场景和物件映射情绪，避免直白宣告。"


# ── content 头部元数据清洗 ───────────────────────────────────────────────────

_META_HEADER_RE = re.compile(
    r"^(歌曲[^\n]*|曲[^\n]*|词[^\n]*|作词[^\n]*|作曲[^\n]*|编[^\n]*)\n",
    re.MULTILINE,
)

def strip_content_metadata(content: str) -> str:
    """去除 content 开头的 '曲xxx词xxx' 类元数据行（保守：只去第一行）。"""
    lines = content.strip().splitlines()
    if not lines:
        return content
    first = lines[0].strip()
    # 判断第一行是否纯元数据（无实质歌词内容）
    is_meta = bool(re.match(
        r"^(歌曲|曲\s|词\s|曲:|词:|作词|作曲|编\s|编曲|唱|演唱|制作)",
        first
    )) and len(first) < 60
    if is_meta:
        return "\n".join(lines[1:]).strip()
    return content.strip()


# ── 粤语检测 ─────────────────────────────────────────────────────────────────

_CANTONESE_MARKERS = {"哋", "嗌", "唔", "喺", "佢", "啩", "咁", "咋", "嘅", "囉"}

def is_cantonese(content: str) -> bool:
    return sum(1 for c in content if c in _CANTONESE_MARKERS) >= 3


# ── 主修复逻辑 ───────────────────────────────────────────────────────────────

def repair_lyrics(data: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict]:
    stats: dict[str, int] = {
        "total": len(data),
        "source_id_fixed": 0,
        "title_fixed": 0,
        "learn_point_cleaned": 0,
        "content_meta_stripped": 0,
        "cantonese_marked": 0,
    }

    result = []
    for entry in data:
        e = dict(entry)

        # F1: source_id 乱码修复
        fixed_sid = fix_source_id(e.get("source_id", ""))
        if fixed_sid != e.get("source_id"):
            e["source_id"] = fixed_sid
            stats["source_id_fixed"] += 1

        # F1: title 乱码修复
        fixed_title = _fix_cp437(e.get("title", ""))
        if fixed_title != e.get("title"):
            e["title"] = fixed_title
            stats["title_fixed"] += 1

        # F2: learn_point 截断
        lp = e.get("learn_point", "")
        cleaned_lp = clean_learn_point(lp)
        if cleaned_lp != lp:
            e["learn_point"] = cleaned_lp
            stats["learn_point_cleaned"] += 1

        # F3: content 元数据头清洗
        content = str(e.get("content", ""))
        stripped = strip_content_metadata(content)
        if stripped != content:
            e["content"] = stripped
            stats["content_meta_stripped"] += 1

        # F4: 粤语标记
        if is_cantonese(str(e.get("content", ""))):
            e["lang_note"] = "cantonese"
            stats["cantonese_marked"] += 1

        result.append(e)

    return result, stats


def repair_poetry(data: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict]:
    before = len(data)
    # F5: 去除 content < 20 字的碎片
    result = [e for e in data if len(str(e.get("content", "")).strip()) >= 20]
    removed = before - len(result)
    stats = {"total_before": before, "total_after": len(result), "fragments_removed": removed}
    return result, stats


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Repair corpus JSON files.")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only, do not write.")
    parser.add_argument("--out-dir", default="corpus", help="Output directory (default: corpus)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    corpus_dir = Path("corpus")

    # ── lyrics_modern_zh ────────────────────────────────────────────────────
    lyrics_path = corpus_dir / "lyrics_modern_zh.json"
    with open(lyrics_path, encoding="utf-8") as f:
        lyrics_data = json.load(f)

    repaired_lyrics, lyrics_stats = repair_lyrics(lyrics_data)
    print("=== lyrics_modern_zh.json ===")
    for k, v in lyrics_stats.items():
        print(f"  {k}: {v}")

    # ── poetry_classical ────────────────────────────────────────────────────
    poetry_path = corpus_dir / "poetry_classical.json"
    with open(poetry_path, encoding="utf-8") as f:
        poetry_data = json.load(f)

    repaired_poetry, poetry_stats = repair_poetry(poetry_data)
    print("\n=== poetry_classical.json ===")
    for k, v in poetry_stats.items():
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return

    # backup originals
    for src in [lyrics_path, poetry_path]:
        bak = src.with_suffix(".json.bak")
        if not bak.exists():
            shutil.copy2(src, bak)
            print(f"[backup] {bak}")

    out_lyrics = out_dir / "lyrics_modern_zh.json"
    out_poetry = out_dir / "poetry_classical.json"

    with open(out_lyrics, "w", encoding="utf-8") as f:
        json.dump(repaired_lyrics, f, ensure_ascii=False, indent=2)
    print(f"\n[written] {out_lyrics}  ({len(repaired_lyrics)} entries)")

    with open(out_poetry, "w", encoding="utf-8") as f:
        json.dump(repaired_poetry, f, ensure_ascii=False, indent=2)
    print(f"[written] {out_poetry}  ({len(repaired_poetry)} entries)")


if __name__ == "__main__":
    main()
