"""Tests for one-law local asset builder pipeline.

PRD linkage:
- visual_montage_nouns.json
- cliche_blacklist.json
- shisanzhe_map.json
- chinese_pop_grids.json
- modern_literary_lexicon.json
- emotion_acoustic_router.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "tools" / "scripts" / "build_local_assets.py"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_local_assets_generates_required_jsons(tmp_path: Path) -> None:
    """Builder should generate all required JSON assets in one run."""
    thuo_dir = tmp_path / "THUOCL"
    _write_text(thuo_dir / "THUOCL_animal.txt", "飞鸟\t100\n海豚\t88\n")
    _write_text(thuo_dir / "THUOCL_food.txt", "便当\t77\n咖啡杯\t55\n")
    _write_text(thuo_dir / "THUOCL_medical.txt", "阿司匹林\t66\n")
    _write_text(thuo_dir / "THUOCL_car.txt", "后视镜\t44\n斑马线\t33\n")

    fun_dir = tmp_path / "funNLP"
    _write_text(fun_dir / "常见中文网络流行语.txt", "宿命\n孤独\n星辰\n灵魂\n")
    _write_text(fun_dir / "中文褒贬义词典.txt", "悲伤\n治愈\n破碎\n")

    lyrics_dir = tmp_path / "Chinese_Lyrics"
    artist_dir = lyrics_dir / "周杰伦_2955"
    _write_text(
        artist_dir / "晴天_28169937.txt",
        "天青色等烟雨，而我在等你。\n便利店的灯影，落在旧衬衫上。\n",
    )

    out_dir = tmp_path / "out"
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "--thuocl-dir",
        str(thuo_dir),
        "--funnlp-dir",
        str(fun_dir),
        "--lyrics-dir",
        str(lyrics_dir),
        "--out-dir",
        str(out_dir),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr

    visual = out_dir / "visual_montage_nouns.json"
    cliche = out_dir / "cliche_blacklist.json"
    shisanzhe = out_dir / "shisanzhe_map.json"
    grids = out_dir / "chinese_pop_grids.json"
    modern = out_dir / "modern_literary_lexicon.json"
    acoustic = out_dir / "emotion_acoustic_router.json"

    for path in [visual, cliche, shisanzhe, grids, modern, acoustic]:
        assert path.exists(), f"missing asset: {path.name}"

    visual_data = json.loads(visual.read_text(encoding="utf-8"))
    assert "nouns" in visual_data
    assert "后视镜" in visual_data["nouns"]

    cliche_data = json.loads(cliche.read_text(encoding="utf-8"))
    assert "blacklist" in cliche_data
    assert "孤独" in cliche_data["blacklist"]

    shisanzhe_data = json.loads(shisanzhe.read_text(encoding="utf-8"))
    assert "map" in shisanzhe_data
    assert "发花辙" in shisanzhe_data["map"]
    assert shisanzhe_data.get("open_vowel_finals") == ["a", "ai", "ao"]

    grids_data = json.loads(grids.read_text(encoding="utf-8"))
    assert "grids" in grids_data
    assert any("，" in g.get("grid", "") for g in grids_data["grids"])

    modern_data = json.loads(modern.read_text(encoding="utf-8"))
    assert "buckets" in modern_data
    assert "urban" in modern_data["buckets"]
    assert isinstance(modern_data["buckets"]["urban"], list)

    acoustic_data = json.loads(acoustic.read_text(encoding="utf-8"))
    assert "routes" in acoustic_data
    sad_route = next(
        r for r in acoustic_data["routes"] if r.get("intent") == "极度悲伤/失恋"
    )
    lock = sad_route["acoustic_lock"]
    assert lock["bpm_max"] <= 75
    assert lock["key_mode"] == "minor"


def test_build_local_assets_requires_all_inputs(tmp_path: Path) -> None:
    """Builder should fail fast when required inputs are missing."""
    out_dir = tmp_path / "out"
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "--thuocl-dir",
        str(tmp_path / "missing_thuo"),
        "--funnlp-dir",
        str(tmp_path / "missing_fun"),
        "--lyrics-dir",
        str(tmp_path / "missing_lyrics"),
        "--out-dir",
        str(out_dir),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert completed.returncode != 0
    assert "missing required input" in (completed.stderr + completed.stdout).lower()
