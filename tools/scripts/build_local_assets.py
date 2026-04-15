"""Build zero-complexity local JSON assets for lyric pipeline.

Outputs:
- visual_montage_nouns.json
- cliche_blacklist.json
- shisanzhe_map.json
- chinese_pop_grids.json
- modern_literary_lexicon.json
- emotion_acoustic_router.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


THUOCL_FILES = [
    "THUOCL_animal.txt",
    "THUOCL_food.txt",
    "THUOCL_medical.txt",
    "THUOCL_car.txt",
]

FUNNLP_FILES = [
    "常见中文网络流行语.txt",
    "中文褒贬义词典.txt",
]

TARGET_ARTISTS = [
    "周杰伦",
    "陈奕迅",
    "陶喆",
    "林俊杰",
    "王力宏",
    "蔡依林",
    "孙燕姿",
    "梁静茹",
    "薛之谦",
    "李荣浩",
]


def _read_lines(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    return [
        x.strip()
        for x in path.read_text(encoding="utf-8", errors="ignore").splitlines()
    ]


def _normalize_token(token: str) -> str:
    token = token.strip()
    token = re.sub(r"\s+", "", token)
    return token


def build_visual_montage_nouns(thuocl_dir: Path) -> dict[str, object]:
    nouns: set[str] = set()
    for filename in THUOCL_FILES:
        for row in _read_lines(thuocl_dir / filename):
            if not row:
                continue
            token = _normalize_token(row.split("\t")[0])
            if len(token) < 2:
                continue
            if token.isdigit():
                continue
            nouns.add(token)

    return {
        "version": "1.0.0",
        "source": "THUOCL",
        "nouns": sorted(nouns),
    }


def build_cliche_blacklist(funnlp_dir: Path, top_n: int = 1000) -> dict[str, object]:
    freq: Counter[str] = Counter()
    for filename in FUNNLP_FILES:
        for row in _read_lines(funnlp_dir / filename):
            if not row:
                continue
            token = _normalize_token(row.split()[0])
            if len(token) < 2:
                continue
            if re.fullmatch(r"[A-Za-z0-9_\-]+", token):
                continue
            freq[token] += 1

    seed = {"孤独", "灵魂", "宿命", "星辰", "破碎", "治愈", "悲伤", "命运"}
    for s in seed:
        freq[s] += 10000

    top = [w for w, _ in freq.most_common(top_n)]
    return {
        "version": "1.0.0",
        "source": "funNLP",
        "blacklist": top,
    }


def build_shisanzhe_map() -> dict[str, object]:
    mapping = {
        "发花辙": ["a", "ia", "ua"],
        "梭波辙": ["o", "e", "uo"],
        "乜斜辙": ["ie", "ve"],
        "姑苏辙": ["u"],
        "一七辙": ["i", "er", "v"],
        "怀来辙": ["ai", "uai"],
        "灰堆辙": ["ei", "ui"],
        "遥条辙": ["ao", "iao"],
        "由求辙": ["ou", "iu"],
        "言前辙": ["an", "ian", "uan", "van"],
        "人辰辙": ["en", "in", "un", "vn"],
        "江阳辙": ["ang", "iang", "uang"],
        "中东辙": ["eng", "ing", "ong", "iong"],
    }
    return {
        "version": "1.0.0",
        "map": mapping,
        "open_vowel_finals": ["a", "ai", "ao"],
    }


def _dehydrate_line(line: str) -> str:
    line = re.sub(r"\s+", "", line)
    chunks = re.split(r"([，。！？；：,.!?;:])", line)
    out: list[str] = []
    i = 0
    while i < len(chunks):
        text = chunks[i].strip()
        punct = chunks[i + 1].strip() if i + 1 < len(chunks) else ""
        if text:
            han = re.findall(r"[\u4e00-\u9fff]", text)
            if han:
                out.append(str(len(han)) + punct)
        i += 2
    if not out:
        han = re.findall(r"[\u4e00-\u9fff]", line)
        if han:
            out.append(str(len(han)))
    return "[" + "，".join(x for x in out if x) + "]" if out else ""


def build_chinese_pop_grids(lyrics_dir: Path, top_k: int = 50) -> dict[str, object]:
    counter: Counter[str] = Counter()
    for artist_dir in lyrics_dir.iterdir() if lyrics_dir.exists() else []:
        if not artist_dir.is_dir():
            continue
        if not any(name in artist_dir.name for name in TARGET_ARTISTS):
            continue
        for txt in artist_dir.glob("*.txt"):
            for line in _read_lines(txt):
                grid = _dehydrate_line(line)
                if grid:
                    counter[grid] += 1

    top = [{"grid": g, "count": c} for g, c in counter.most_common(top_k)]
    return {
        "version": "1.0.0",
        "source": "Chinese_Lyrics",
        "grids": top,
    }


def build_modern_literary_lexicon(
    visual_nouns: list[str],
) -> dict[str, object]:
    buckets = {
        "material": ["铁锈", "玻璃", "灰烬", "霓虹", "混凝土"],
        "nature": ["潮汐", "飞鸟", "雨幕", "薄雾", "深海"],
        "motion": ["坠落", "漂移", "折返", "淹没", "燃烧"],
        "urban": [],
    }

    urban_seed = ["后视镜", "斑马线", "便利店", "站台", "广告牌", "咖啡杯", "阿司匹林"]
    merged = list(dict.fromkeys(urban_seed + visual_nouns))
    buckets["urban"] = [w for w in merged if len(w) >= 2][:80]

    return {
        "version": "1.0.0",
        "buckets": buckets,
        "rules": {
            "chorus_min_visual_nouns": 2,
            "forbid_abstract_emotion_only": True,
        },
    }


def build_emotion_acoustic_router() -> dict[str, object]:
    return {
        "version": "1.0.0",
        "routes": [
            {
                "intent": "极度悲伤/失恋",
                "acoustic_lock": {
                    "bpm_min": 58,
                    "bpm_max": 75,
                    "key_mode": "minor",
                    "exclude_instruments": [
                        "brass",
                        "edm_synth",
                        "upbeat_percussion",
                    ],
                    "vocal_prompt": "breathiness, close-mic, intimate, crying tone",
                },
            },
            {
                "intent": "upbeat/R&B",
                "acoustic_lock": {
                    "bpm_min": 88,
                    "bpm_max": 106,
                    "key_mode": "minor_or_dorian",
                    "exclude_instruments": ["orchestral_brass"],
                    "vocal_prompt": "rhythmic phrasing, dry lead vocal, tight groove",
                },
            },
        ],
    }


def _must_exist(path: Path, label: str) -> None:
    if not path.exists():
        raise ValueError(f"missing required input: {label}: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local lyric data assets")
    parser.add_argument("--thuocl-dir", required=True)
    parser.add_argument("--funnlp-dir", required=True)
    parser.add_argument("--lyrics-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    thuocl_dir = Path(args.thuocl_dir).expanduser().resolve()
    funnlp_dir = Path(args.funnlp_dir).expanduser().resolve()
    lyrics_dir = Path(args.lyrics_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()

    try:
        _must_exist(thuocl_dir, "thuocl-dir")
        _must_exist(funnlp_dir, "funnlp-dir")
        _must_exist(lyrics_dir, "lyrics-dir")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    visual = build_visual_montage_nouns(thuocl_dir)
    cliche = build_cliche_blacklist(funnlp_dir)
    shisanzhe = build_shisanzhe_map()
    grids = build_chinese_pop_grids(lyrics_dir)
    visual_nouns_obj = visual.get("nouns", [])
    visual_nouns = visual_nouns_obj if isinstance(visual_nouns_obj, list) else []
    modern = build_modern_literary_lexicon([str(x) for x in visual_nouns])
    acoustic = build_emotion_acoustic_router()

    (out_dir / "visual_montage_nouns.json").write_text(
        json.dumps(visual, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "cliche_blacklist.json").write_text(
        json.dumps(cliche, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "shisanzhe_map.json").write_text(
        json.dumps(shisanzhe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "chinese_pop_grids.json").write_text(
        json.dumps(grids, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "modern_literary_lexicon.json").write_text(
        json.dumps(modern, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "emotion_acoustic_router.json").write_text(
        json.dumps(acoustic, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
