from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

IMAGERY_WORDS = {
    "月", "风", "花", "雪", "云", "雨", "秋", "春", "山", "水", "江", "夜", "梦",
    "柳", "梅", "雁", "烟", "霜", "灯", "酒", "愁", "相思", "归", "泪", "叶",
    "星", "露", "雾", "潮", "舟", "桥", "楼", "窗", "帘", "笛", "琴", "钟",
    "鸿", "莺", "蝶", "蝉", "鸦", "鹤", "鹿", "鱼", "荷", "菊", "桃", "杏",
    "松", "竹", "柏", "梧", "桐", "桑", "麦田", "稻", "桑", "蚕", "蜂", "蝶",
}

EMOTION_MAP = {
    "愁": ("哀愁的沉溺", "失乐园"),
    "恨": ("无法释怀的执念", "失乐园"),
    "泪": ("悲伤的释放", "失乐园"),
    "相思": ("求而不得的怅惘", "纳西索斯"),
    "思": ("求而不得的怅惘", "纳西索斯"),
    "梦": ("现实与幻想的撕裂", "浮士德"),
    "醉": ("逃避现实的沉溺", "浮士德"),
    "归": ("对根源的渴望", "失乐园"),
    "别": ("失去连接的痛楚", "失乐园"),
    "老": ("时间碾压的虚无", "西西弗斯"),
    "古": ("时间碾压的虚无", "西西弗斯"),
    "空": ("存在主义的虚无", "西西弗斯"),
    "独": ("独处的丰盈", "纳西索斯"),
    "静": ("独处的丰盈", "纳西索斯"),
    "闲": ("独处的丰盈", "纳西索斯"),
    "笑": ("微小的确幸", "俄耳甫斯"),
    "乐": ("微小的确幸", "俄耳甫斯"),
    "喜": ("微小的确幸", "俄耳甫斯"),
    "豪": ("天地一粟的释然", "普罗米修斯"),
    "壮": ("天地一粟的释然", "普罗米修斯"),
    "志": ("理想主义燃烧", "普罗米修斯"),
    "勇": ("理想主义燃烧", "普罗米修斯"),
}


def _extract_imagery(text: str) -> list[str]:
    found = []
    for word in IMAGERY_WORDS:
        if word in text and word not in found:
            found.append(word)
    return found[:6]


def _detect_emotion(text: str) -> tuple[str, str]:
    scores: dict[str, int] = {}
    archetype_scores: dict[str, int] = {}
    for keyword, (emotion, archetype) in EMOTION_MAP.items():
        count = text.count(keyword)
        if count > 0:
            scores[emotion] = scores.get(emotion, 0) + count
            archetype_scores[archetype] = archetype_scores.get(archetype, 0) + count
    if not scores:
        return "恬淡的静默", "西西弗斯"
    top_emotion = max(scores, key=lambda k: scores[k])
    top_archetype = max(archetype_scores, key=lambda k: archetype_scores[k])
    return top_emotion, top_archetype


def _analyze_phonetic_rhythm(text: str) -> dict[str, str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {"韵脚": "未知", "声调起伏": "平缓", "节奏型": "自由", "押韵模式": "无"}
    
    # Detect line length pattern
    lengths = [len(ln) for ln in lines]
    avg_len = sum(lengths) / len(lengths)
    
    if avg_len <= 10:
        rhythm = "短句急促"
    elif avg_len <= 20:
        rhythm = "五言/七言顿挫"
    elif avg_len <= 35:
        rhythm = "长短句交错"
    else:
        rhythm = "长句舒缓"
    
    # Simple rhyme detection (last char of each line)
    last_chars = [ln[-1] for ln in lines if ln]
    rhyme_groups: dict[str, list[str]] = {}
    for ch in last_chars:
        # Group by simple rhyme family (naive approach)
        rhyme_key = ch
        rhyme_groups.setdefault(rhyme_key, []).append(ch)
    
    # Find most common ending
    if last_chars:
        from collections import Counter
        common = Counter(last_chars).most_common(1)[0]
        rhyme = f"以'{common[0]}'韵为主"
    else:
        rhyme = "无明显韵脚"
    
    return {
        "韵脚": rhyme,
        "声调起伏": "古汉语四声，平仄交替" if avg_len <= 20 else "现代自由声调",
        "节奏型": rhythm,
        "押韵模式": f"{len(lines)}句，末字押韵" if len(set(last_chars)) < len(last_chars) else "散韵",
    }


def _musical_traits_from_text(text: str) -> dict[str, str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    line_count = len(lines)
    avg_len = sum(len(ln) for ln in lines) / max(1, line_count)
    
    if line_count <= 4:
        density = "high"
    elif line_count <= 8:
        density = "medium"
    else:
        density = "low"
    
    if "？" in text or "！" in text:
        rhythm = "爆发型"
    elif avg_len <= 15:
        rhythm = "推进型"
    elif any(w in text for w in ["风", "云", "水", "月", "夜"]):
        rhythm = "消散型"
    else:
        rhythm = "循环型"
    
    if any(w in text for w in ["高", "飞", "上", "升", "登"]):
        register = "高亢"
    elif any(w in text for w in ["低", "沉", "落", "下", "深"]):
        register = "低沉"
    else:
        register = "起伏"
    
    if line_count > 8:
        texture = "多层交织"
    else:
        texture = "单层"
    
    if any(w in text for w in ["急", "快", "驰", "奔", "赶"]):
        tempo = "快板"
    elif any(w in text for w in ["慢", "迟", "缓", "闲", "悠"]):
        tempo = "慢板"
    else:
        tempo = "中板"
    
    if any(w in text for w in ["愁", "恨", "泪", "悲", "苦", "孤", "寂"]):
        harmony = "小调忧郁"
    elif any(w in text for w in ["喜", "笑", "乐", "欢", "明", "晴"]):
        harmony = "大调明亮"
    else:
        harmony = "调式混合"
    
    return {
        "留白密度": density,
        "节奏型": rhythm,
        "音域暗示": register,
        "织体": texture,
        "速度感": tempo,
        "和声色彩": harmony,
    }


def _generate_learn_point(text: str, title: str) -> str:
    emotion, archetype = _detect_emotion(text)
    imagery = _extract_imagery(text)
    if imagery:
        img_str = "、".join(imagery[:3])
        return f"以{img_str}等意象，营造{emotion}的情感氛围，适合{archetype}式旋律写作"
    return f"通过精炼的文字，传达{emotion}的核心情感"


def _quotability(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) <= 4 and all(len(ln) <= 20 for ln in lines):
        return "direct"
    elif any(len(ln) <= 15 for ln in lines):
        return "adapt"
    else:
        return "inspire"


def _lyric_strategies(text: str) -> list[dict[str, str]]:
    strategies = []
    
    # Strategy 1: direct quote if short
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    short_lines = [ln for ln in lines if len(ln) <= 20]
    if short_lines:
        strategies.append({
            "type": "意象直取",
            "description": "提取诗中精炼短句，直接作为歌词hook或副歌",
            "example": f"如：'{short_lines[0]}'",
        })
    
    # Strategy 2: imagery swap
    imagery = _extract_imagery(text)
    if imagery:
        strategies.append({
            "type": "意境转换",
            "description": "保留原诗视觉结构，将古典意象替换为现代场景",
            "example": f"将'{'、'.join(imagery[:2])}'转换为城市/科技意象",
        })
    
    # Strategy 3: emotional extraction
    emotion, _ = _detect_emotion(text)
    strategies.append({
        "type": "情感提纯",
        "description": f"提取'{emotion}'的情感曲线，完全重写为现代歌词",
        "example": "保留情感推进逻辑，更换所有具体意象",
    })
    
    return strategies


def enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    text = str(row.get("content", ""))
    title = str(row.get("title", ""))
    
    emotion, archetype = _detect_emotion(text)
    item = dict(row)
    item["emotion_core"] = emotion
    item["archetype"] = archetype
    item["musical_traits"] = _musical_traits_from_text(text)
    item["lyric_strategies"] = _lyric_strategies(text)
    item["core_imagery"] = _extract_imagery(text)
    item["phonetic_rhythm"] = _analyze_phonetic_rhythm(text)
    item["learn_point"] = _generate_learn_point(text, title)
    item["quotability"] = _quotability(text)
    
    # Remove do_not_copy for classical
    if "do_not_copy" in item:
        del item["do_not_copy"]
    
    return item


def main() -> int:
    parser = argparse.ArgumentParser(description="Rule-based enrich for classical poetry (fallback when LLM unavailable)")
    parser.add_argument("--input", default="corpus/_raw/new_classical_unenriched.json")
    parser.add_argument("--output", default="corpus/_raw/new_classical_rule_enriched.json")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("Input must be a JSON list")
    
    enriched = [enrich_row(row) for row in data if isinstance(row, dict)]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"Enriched {len(enriched)} rows -> {output_path}")
    
    # Show samples
    for row in enriched[:3]:
        print(f"\n--- {row.get('title')} ---")
        print(f"emotion_core: {row.get('emotion_core')}")
        print(f"archetype: {row.get('archetype')}")
        print(f"learn_point: {row.get('learn_point')}")
        print(f"phonetic_rhythm: {row.get('phonetic_rhythm')}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
