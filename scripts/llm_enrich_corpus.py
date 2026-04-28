from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from typing import Any
from urllib import request
from urllib import error

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Config loaded from environment variables


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_prompt(row: dict[str, Any], *, mode: str = "modern") -> dict[str, Any]:
    if mode == "classical_v2":
        return {
            "task": "将古典诗词翻译为音乐创作指令",
            "constraints": [
                "你是情感分析大师+作曲大师+产品经理的合体",
                "不要按文学题材分类，要按'这首歌的情感内核是什么'分类",
                "使用神话原型标签（失乐园/浮士德/西西弗斯/普罗米修斯/纳西索斯/俄耳甫斯）",
                "必须分析拼音押韵结构（韵脚、声调起伏、句内节奏型）",
                "必须分析音乐性映射（留白密度/节奏型/音域暗示/织体/速度感/和声色彩）",
                "提供至少2种歌词化用策略：意象直取/意境转换/情感提纯/节奏移植",
                "learn_point 必须是一句'作曲/作词可学点'，引用原文短句佐证",
                "严禁出现 do_not_copy 相关内容——古诗词就是用来引用化用的",
                "严禁出现作词/作曲/编曲/歌手/专辑/发行等基础信息",
                "严禁出现作者姓名",
                "输出必须是JSON对象",
            ],
            "input": {
                "source_id": str(row.get("source_id", "")),
                "title": str(row.get("title", "")),
                "content": str(row.get("content", "")),
                "author": str(row.get("author", "")),
            },
            "output_schema": {
                "emotion_core": "string",
                "archetype": "失乐园|浮士德|西西弗斯|普罗米修斯|纳西索斯|俄耳甫斯",
                "musical_traits": {
                    "留白密度": "high|medium|low",
                    "节奏型": "循环型|推进型|爆发型|消散型",
                    "音域暗示": "低沉|高亢|起伏|平稳",
                    "织体": "单层|多层交织|对位",
                    "速度感": "慢板|中板|快板|自由",
                    "和声色彩": "大调明亮|小调忧郁|调式混合|无调性",
                },
                "lyric_strategies": [
                    {
                        "type": "意象直取|意境转换|情感提纯|节奏移植",
                        "description": "string",
                        "example": "string",
                    }
                ],
                "core_imagery": ["string"],
                "phonetic_rhythm": {
                    "韵脚": "string",
                    "声调起伏": "string",
                    "节奏型": "string",
                    "押韵模式": "string",
                },
                "learn_point": "string",
                "quotability": "direct|adapt|inspire",
                "lyric_profile": "string",
                "valence": "positive|negative|neutral|mixed",
                "emotion_tags": ["string"],
            },
        }
    return {
        "task": "为单首歌词生成高质量学习锚点",
        "constraints": [
            "必须像资深乐评人一样写分析，不能套模板句",
            "learn_point_analysis与do_not_copy_analysis必须是两段完整自然句",
            "严禁出现作词/作曲/编曲/歌手/专辑/发行等基础信息",
            "严禁出现作者姓名：林夕、方文山、姚若龙、李宗盛、阿信、黄伟文、厉曼婷",
            "必须结合原文的具体语句来分析手法（隐喻、视角、动词、留白、叙事推进）",
            "learn_point_quotes/do_not_copy_quotes中的短句必须逐字来自原文",
            "输出必须是JSON对象",
        ],
        "input": {
            "source_id": str(row.get("source_id", "")),
            "title": str(row.get("title", "")),
            "content": str(row.get("content", "")),
        },
        "output_schema": {
            "learn_point_analysis": "string",
            "learn_point_quotes": ["string"],
            "do_not_copy_analysis": "string",
            "do_not_copy_quotes": ["string"],
            "emotion_tags": ["string"],
            "profile_tag": "string",
            "valence": "positive|negative|neutral|mixed",
        },
    }


def _call_openai_compatible_raw(*, base_url: str, api_key: str, model: str, prompt: dict[str, Any]) -> tuple[dict[str, Any], str]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是歌词语料提纯专家，专注文学手法分析，禁止模板化输出。",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "claude-code/0.1.0",
        },
        method="POST",
    )
    retries = 6
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=300) as resp:
                raw_body = resp.read().decode("utf-8", errors="replace")
            decoded = json.loads(raw_body)
            return decoded, raw_body
        except error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code in {429, 500, 502, 503, 504} and attempt < retries - 1:
                time.sleep(min(60, 2 ** attempt * 2))
                last_err = RuntimeError(f"HTTP {e.code}: {body[:300]}")
                continue
            raise RuntimeError(f"HTTP {e.code}: {body[:500]}")
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries - 1:
                time.sleep(min(60, 2 ** attempt * 2))
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("unknown request failure")


def _compose_fields(parsed: dict[str, Any], *, mode: str = "modern") -> tuple[str, str]:
    if mode == "classical_v2":
        learn_point = str(parsed.get("learn_point", "")).strip()
        do_not_copy = ""
        return learn_point, do_not_copy
    learn_analysis = str(parsed.get("learn_point_analysis", "")).strip()
    dont_analysis = str(parsed.get("do_not_copy_analysis", "")).strip()
    learn_quotes = [str(x).strip() for x in parsed.get("learn_point_quotes", []) if str(x).strip()]
    dont_quotes = [str(x).strip() for x in parsed.get("do_not_copy_quotes", []) if str(x).strip()]
    learn_quote_text = "｜".join([f"「{q}」" for q in learn_quotes])
    dont_quote_text = "｜".join([f"「{q}」" for q in dont_quotes])
    learn_point = f"【分析】：{learn_analysis}【原文佐证】：{learn_quote_text}"
    do_not_copy = f"【分析】：{dont_analysis}【原文佐证】：{dont_quote_text}"
    return learn_point, do_not_copy


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM enrich rows with real API calls")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--input", default="corpus/lyrics_modern_zh.json")
    parser.add_argument("--output", default="corpus/_raw/golden_anchors_modern_llm_enriched.json")
    parser.add_argument("--raw-log", default="corpus/_raw/llm_api_raw_response.json")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--family", default="golden_lyricist")
    parser.add_argument("--mode", choices=["modern", "classical_v2"], default="modern")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    input_path = (repo_root / args.input).resolve()
    output_path = (repo_root / args.output).resolve()
    raw_log_path = (repo_root / args.raw_log).resolve()

    import os
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    if not (base_url and api_key and model):
        raise RuntimeError("OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL environment variables are required")

    rows = _load_rows(input_path)
    if args.mode == "classical_v2":
        target_rows_all = [r for r in rows if str(r.get("content", "")).strip()]
    else:
        target_rows_all = [
            row
            for row in rows
            if str(row.get("source_family", "")).strip() == args.family and str(row.get("content", "")).strip()
        ]
    start = max(0, int(args.offset))
    end = start + max(1, int(args.limit))
    target_rows = target_rows_all[start:end]

    enriched: list[dict[str, Any]] = _load_rows(output_path)
    done_ids = {str(x.get("source_id", "")).strip() for x in enriched}
    raw_log_payload: dict[str, Any] = {}

    for idx, row in enumerate(target_rows):
        source_id = str(row.get("source_id", "")).strip()
        if source_id in done_ids:
            continue
        prompt = _build_prompt(row, mode=args.mode)
        decoded, raw_body = _call_openai_compatible_raw(
            base_url=base_url,
            api_key=api_key,
            model=model,
            prompt=prompt,
        )

        content = decoded.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}

        item = dict(row)
        learn_point, do_not_copy = _compose_fields(parsed, mode=args.mode)
        item["learn_point"] = learn_point
        if do_not_copy:
            item["do_not_copy"] = do_not_copy
        elif "do_not_copy" in item and args.mode == "classical_v2":
            del item["do_not_copy"]
        if isinstance(parsed.get("emotion_tags"), list):
            item["emotion_tags"] = [str(x).strip() for x in parsed["emotion_tags"] if str(x).strip()][:5]
        profile_tag = str(parsed.get("profile_tag", "")).strip() or str(parsed.get("lyric_profile", "")).strip()
        if profile_tag:
            item["profile_tag"] = profile_tag
        valence = str(parsed.get("valence", "")).strip()
        if valence in {"positive", "negative", "neutral", "mixed"}:
            item["valence"] = valence
        if args.mode == "classical_v2":
            for key in ["emotion_core", "archetype", "musical_traits", "lyric_strategies", "core_imagery", "phonetic_rhythm", "quotability"]:
                if key in parsed:
                    item[key] = parsed[key]
        enriched.append(item)
        done_ids.add(source_id)

        if (idx + 1) % 5 == 0:
            _write_json(output_path, enriched)

        if idx == 0:
            raw_log_payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_id": str(row.get("source_id", "")),
                "prompt": prompt,
                "raw_response": raw_body,
            }

    _write_json(output_path, enriched)
    _write_json(raw_log_path, raw_log_payload)

    print(
        json.dumps(
            {
                "status": "ok",
                "provider": "kimi-for-coding",
                "model": model,
                "mode": args.mode,
                "rows_enriched": len(enriched),
                "output": str(output_path),
                "raw_log": str(raw_log_path),
            },
            ensure_ascii=False,
        )
    )
    for sample in enriched[:3]:
        lp = str(sample.get("learn_point", "")).split("【原文佐证】：", 1)[0].replace("【分析】：", "").strip()
        dn = str(sample.get("do_not_copy", "")).split("【原文佐证】：", 1)[0].replace("【分析】：", "").strip()
        line = json.dumps({"source_id": sample.get("source_id"), "learn_point_analysis": lp, "do_not_copy_analysis": dn}, ensure_ascii=False)
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("unicode_escape").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
