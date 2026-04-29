from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib import request

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.corpus_quality_lint import lint_corpus_row


GARBLED_RE = re.compile(r"�|\ufffd|��")
_SPACE_RE = re.compile(r"\s+")
_META_LINE_RE = re.compile(r"(?:^|\s)(?:作词|作曲|编曲|词|曲|编)(?:\s|$)|词[：:]|曲[：:]|编[：:]")
_BANNED_ANALYSIS_HINT_RE = re.compile(r"作词|作曲|编曲|林夕|方文山|歌手|专辑|发行")
_GENERIC_ANALYSIS_RE = re.compile(r"通过具体意象与动作细节推进情绪表达，避免直接结论句|并置，制造情绪张力")
_ZH_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,6}")
_QUOTE_CONTENT_RE = re.compile(r"“[^”]*”|「[^」]*」")
_GOLDEN_LYRICISTS_TARGETS = {
    "林夕": 40,
    "方文山": 30,
    "姚若龙": 20,
    "李宗盛": 20,
    "阿信": 10,
    "黄伟文": 10,
    "厉曼婷": 10,
    "许嵩": 10,
    "陈小奇": 10,
    "黄自": 10,
    "陈乐融": 10,
}


def _read_env_map(repo_root: Path) -> dict[str, str]:
    env_path = repo_root / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


def _clip(text: str, *, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _fallback_quotes(text: str, *, limit: int = 3) -> list[str]:
    chunks = [x.strip() for x in re.split(r"[\n，。！？；：、,.!?;:]+", text) if x.strip()]
    chunks.sort(key=lambda x: len(x), reverse=True)
    out: list[str] = []
    for chunk in chunks:
        if len(chunk) < 4:
            continue
        if len(chunk) > 48:
            continue
        if _META_LINE_RE.search(chunk):
            continue
        if chunk in out:
            continue
        out.append(chunk)
        if len(out) >= limit:
            break
    if not out and text.strip():
        first_line = text.strip().splitlines()[0].strip()
        if first_line:
            out = [first_line[:48]]
    return out


def _normalize_quote_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    phrases: list[str] = []
    for item in value:
        phrase = str(item).strip().strip("\"'")
        if not phrase:
            continue
        phrases.append(phrase)
    return phrases


def _filter_quotes_present_in_source(*, phrases: list[str], source_text: str, limit: int = 3) -> list[str]:
    out: list[str] = []
    for phrase in phrases:
        p = phrase.strip()
        if not p:
            continue
        if _META_LINE_RE.search(p):
            continue
        if len(p) > 48:
            continue
        if p in source_text and p not in out:
            out.append(p)
        if len(out) >= limit:
            break
    return out


def _compose_guidance_from_quotes(quotes: list[str]) -> str:
    cleaned = [q.strip() for q in quotes if q.strip()]
    if not cleaned:
        return ""
    return "｜".join([f"「{q}」" for q in cleaned])


def _pick_imagery_tokens(*, source_text: str, quotes: list[str], limit: int = 2) -> list[str]:
    pool = "\n".join(quotes) if quotes else source_text
    seen: set[str] = set()
    picked: list[str] = []
    for token in _ZH_TOKEN_RE.findall(pool):
        if token in seen:
            continue
        if _META_LINE_RE.search(token):
            continue
        seen.add(token)
        picked.append(token)
        if len(picked) >= limit:
            break
    return picked


def _analysis_fallback(*, source_text: str, quotes: list[str], for_learn: bool) -> str:
    tokens = _pick_imagery_tokens(source_text=source_text, quotes=quotes, limit=2)
    if len(tokens) >= 2:
        if for_learn:
            return f"把“{tokens[0]}”作为场景触发点，再让“{tokens[1]}”承接心理变化，能让情绪递进更可感。"
        return f"避免直接复写“{tokens[0]}”“{tokens[1]}”这组搭配，改写时需替换意象并重排句间关系。"
    if len(tokens) == 1:
        if for_learn:
            return f"围绕“{tokens[0]}”扩展动作与感官层次，比直接下结论更有表现力。"
        return f"不要重复套用“{tokens[0]}”原句，需在新场景中重建同类情绪功能。"
    return "通过场景细节与叙事节奏的联动来承载情绪，而不是直白陈述。" if for_learn else "避免复写高辨识度原句，改写后再用于新的语义环境。"


def _analysis_fallback_variant(*, source_text: str, quotes: list[str], source_id: str, for_learn: bool) -> str:
    tokens = _pick_imagery_tokens(source_text=source_text, quotes=quotes, limit=3)
    digest = hashlib.md5(source_id.encode("utf-8", errors="ignore")).hexdigest()
    bucket_seed = int(digest[:8], 16)
    if len(tokens) >= 2:
        a = tokens[0]
        b = tokens[1]
        if for_learn:
            variants = [
                f"学习把“{a}”与“{b}”放在同一段落形成反差，让情绪从叙述自然过渡到揭示。",
                f"学习围绕“{a}”铺陈，再以“{b}”收束，把抽象心境落到可感的画面层。",
                f"学习通过“{a}→{b}”的意象递进制造时间感，避免一句话把情绪直接说死。",
                f"学习借“{a}”“{b}”做双焦点叙事，让主观感受通过物象转移被看见。",
                f"可复用“{a}”先抑后扬、再落到“{b}”的写法，把情绪变化拆成可演唱的两步。",
                f"把“{a}”当作观察镜头，把“{b}”当作情绪落点，能让副歌更有抓手。",
                f"用“{a}”做外部场景、用“{b}”做内心回声，形成内外对照而非直白表态。",
                f"先写“{a}”的动作或状态，再转到“{b}”的结果感，可增强句间牵引力。",
                f"“{a}”与“{b}”组合适合做桥段转场，既保留画面感又能推进叙事时间。",
                f"围绕“{a}”“{b}”建立前后呼应，可把零散情绪组织成完整的情感弧线。",
                f"将“{a}”处理为触发点、“{b}”处理为回应点，能避免歌词只剩抽象判断。",
                f"以“{a}”开路、以“{b}”回钩的句法，有助于把记忆点固定在关键小节。",
            ]
        else:
            variants = [
                f"避免原样复写“{a}”“{b}”并列结构，需更换意象后重建同类情绪关系。",
                f"避免直接套用“{a}”到“{b}”的转场句法，改成新的时序与语义连接。",
                f"避免重复“{a}”“{b}”这组高辨识组合，防止生成结果出现来源痕迹。",
                f"避免沿用“{a}”与“{b}”的同位表达，可保留功能但必须改写词面与顺序。",
                f"“{a}”和“{b}”不应原封照搬，建议替换其中至少一个意象并改写句间逻辑。",
                f"不要复写“{a}→{b}”的推进链，需重建触发点与情绪回应的对应关系。",
                f"应规避“{a}”“{b}”的固定搭配，改为新的物象对照再表达同类主题。",
                f"避免把“{a}”“{b}”按原顺序复用，至少改动视角、语态与节奏落点。",
                f"“{a}”与“{b}”属于高识别片段，保留其功能时必须替换表层词汇。",
                f"原文“{a}”“{b}”的并置不可复刻，建议改写成不同场景下的同构关系。",
                f"避免沿袭“{a}”引出“{b}”的写法，改成新的因果或并置结构。",
                f"“{a}”“{b}”这组句法痕迹明显，使用时需打散重排并更换至少半数词面。",
            ]
        return variants[bucket_seed % len(variants)]
    return _analysis_fallback(source_text=source_text, quotes=quotes, for_learn=for_learn)


def _normalized_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    a_set = set(a)
    b_set = set(b)
    inter = len(a_set.intersection(b_set))
    union = len(a_set.union(b_set))
    if union == 0:
        return 0.0
    return inter / union


def _clean_analysis_text(text: Any) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    s = _SPACE_RE.sub(" ", s)
    if _BANNED_ANALYSIS_HINT_RE.search(s):
        return ""
    if _GENERIC_ANALYSIS_RE.search(s):
        return ""
    if len(s) < 18:
        return ""
    return _clip(s, max_len=160)


def _analysis_signature(text: str) -> str:
    s = str(text or "")
    s = re.sub(r"\s+", "", s)
    return s


def _bad_fragmented_phrase(text: str) -> bool:
    if not text:
        return True
    bad_parts = ["来一", "活了下", "被" , "与“", "“与"]
    return any(x in text for x in bad_parts)


def _call_kimi_for_anchor(
    *,
    api_key: str,
    base_url: str,
    model: str,
    title: str,
    source_text: str,
    source_family: str,
    row_type: str,
) -> dict[str, Any]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    system_prompt = (
        "你是中文歌词语料标注助手。必须只引用提供原文中真实出现的片段，不得虚构。"
    )
    user_prompt = {
        "task": "生成黄金锚点标注",
        "constraints": [
            "analysis字段必须用你自己的话总结创作手法，不允许只复制原文",
            "quotes字段中的每个短语必须100%来自原文逐字片段，仅作为佐证",
            "绝对禁止将作词人/作曲人/编曲人姓名、歌曲基础信息当作学习点或引用",
            "必须聚焦文学手法、视角切换、意象使用、叙事推进",
            "learn_point_analysis里必须点名1-2个原文意象词并解释其作用（例如时针/筵席）",
            "严禁输出万能套话：通过具体意象与动作细节推进情绪表达，避免直接结论句",
            "emotion_tags给3-5个，profile_tag和valence按文本语气判断",
        ],
        "title": title,
        "source_family": source_family,
        "row_type": row_type,
        "source_text": _clip(source_text, max_len=2400),
        "output_json_schema": {
            "emotion_tags": ["string"],
            "profile_tag": "string",
            "valence": "positive|negative|neutral|mixed",
            "learn_point_analysis": "string",
            "learn_point_quotes": ["string"],
            "do_not_copy_analysis": "string",
            "do_not_copy_quotes": ["string"],
        },
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    decoded = json.loads(body)
    content = decoded.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return parsed


def _call_kimi_refine_analysis(
    *,
    api_key: str,
    base_url: str,
    model: str,
    title: str,
    source_text: str,
    learn_quotes: list[str],
    dont_quotes: list[str],
    style_seed: str,
) -> dict[str, str]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是歌词技法分析器，禁止套话，禁止写作词/作曲/编曲/歌手等基础信息。",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": "根据原文与引语，生成两段不重复且具体的分析",
                        "title": title,
                        "source_text": _clip(source_text, max_len=1800),
                        "learn_quotes": learn_quotes,
                        "do_not_copy_quotes": dont_quotes,
                        "rules": [
                            "learn_point_analysis必须点名1-2个意象词并解释作用",
                            "do_not_copy_analysis必须说明应如何改写这些高辨识片段",
                            "禁止出现：作词/作曲/编曲/歌手/专辑/发行/林夕/方文山/姚若龙/李宗盛/阿信/黄伟文/厉曼婷",
                            "禁止套话：通过具体意象与动作细节推进情绪表达，避免直接结论句",
                            "两段分析都必须是自然完整句，严禁截断词语或病句",
                            "语气与句式需和style_seed对应，避免多条结果同模板",
                            "输出JSON对象，键为learn_point_analysis和do_not_copy_analysis",
                        ],
                        "style_seed": style_seed,
                    },
                    ensure_ascii=False,
                ),
            },
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
        },
        method="POST",
    )
    with request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    decoded = json.loads(body)
    content = decoded.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return {
        "learn_point_analysis": str(parsed.get("learn_point_analysis", "")).strip(),
        "do_not_copy_analysis": str(parsed.get("do_not_copy_analysis", "")).strip(),
    }


def _build_style_seed(source_id: str) -> str:
    seeds = ["对照", "递进", "镜头", "叙事", "转场", "留白", "因果", "反问", "回环", "时间线"]
    digest = hashlib.md5(source_id.encode("utf-8", errors="ignore")).hexdigest()
    return seeds[int(digest[:4], 16) % len(seeds)]


def build_row(
    *,
    source_id: str,
    source_type: str,
    title: str,
    content: str,
    emotion_tags: list[str],
    profile_tag: str,
    valence: str,
    learn_point: str,
    do_not_copy: str,
    source_family: str = "",
    author: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source_id": source_id,
        "type": source_type,
        "title": title,
        "emotion_tags": [x for x in emotion_tags if str(x).strip()],
        "profile_tag": profile_tag,
        "valence": valence,
        "learn_point": learn_point,
        "do_not_copy": do_not_copy,
        "content": content,
    }
    if source_family:
        row["source_family"] = source_family
    if author:
        row["author"] = author
    return row


def extract_chengyu_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in payload.items():
        phrase = str(key).strip()
        if not phrase:
            continue
        if len(phrase) > 8:
            continue
        if GARBLED_RE.search(phrase):
            continue
        explain = str(value).strip() if value is not None else ""
        rows.append(
            build_row(
                source_id=f"idiom:auto:{phrase}",
                source_type="classical_poem",
                title=phrase,
                content=phrase,
                emotion_tags=["imagery", "compression"],
                profile_tag="classical_restraint",
                valence="mixed",
                learn_point="短句压缩意象并提供可复用的情绪锚点。",
                do_not_copy="禁止复写成语原句于整段关键句，需重组上下文。",
                source_family="chengyu",
                author=explain[:60],
            )
        )
    return rows


def parse_modern_lyric_lines(text: str, *, allowed_lyricists: set[str]) -> list[dict[str, str]]:
    blocks = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
    rows: list[dict[str, str]] = []
    for block in blocks:
        title_match = re.search(r"(?:歌名|标题)\s*[:：]\s*(.+)", block)
        lyricist_match = re.search(r"(?:作词|词作者)\s*[:：]\s*(.+)", block)
        lyrics_match = re.search(r"(?:歌词)\s*[:：]\s*([\s\S]+)", block)
        if not (title_match and lyricist_match and lyrics_match):
            continue
        lyricist = lyricist_match.group(1).strip()
        if lyricist not in allowed_lyricists:
            continue
        title = title_match.group(1).strip()
        lyrics = "\n".join([ln.strip() for ln in lyrics_match.group(1).splitlines() if ln.strip()])
        if len(lyrics) < 12:
            continue
        rows.append({"title": title, "lyricist": lyricist, "lyrics": lyrics})
    return rows


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _clone_or_refresh(owner: str, repo: str, target_root: Path) -> Path:
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / f"{owner}__{repo}"
    if not target.exists():
        subprocess.run(["git", "clone", "--depth", "1", f"https://github.com/{owner}/{repo}.git", str(target)], check=True)
        return target
    subprocess.run(["git", "fetch", "origin", "--depth", "1"], cwd=target, check=True)
    subprocess.run(["git", "reset", "--hard", "origin/HEAD"], cwd=target, check=True)
    return target


def _collect_classical_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    poetry_path = repo_root / "corpus" / "_raw" / "github" / "chinese-poetry__chinese-poetry" / "元曲" / "yuanqu.json"
    payload = _load_json(poetry_path)
    if isinstance(payload, list):
        for idx, item in enumerate(payload[:2000]):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            author = str(item.get("author") or "").strip()
            paragraphs = item.get("paragraphs")
            if not title or not isinstance(paragraphs, list):
                continue
            content = "\n".join([str(x).strip() for x in paragraphs if str(x).strip()])
            if len(content) < 12:
                continue
            rows.append(
                build_row(
                    source_id=f"github:chinese-poetry/chinese-poetry:元曲/yuanqu.json#{idx}",
                    source_type="classical_poem",
                    title=title,
                    content=content,
                    emotion_tags=["imagery", "restraint"],
                    profile_tag="classical_restraint",
                    valence="mixed",
                    learn_point="通过意象并置与留白转折完成情绪抬升。",
                    do_not_copy="禁止复写来源文本原句与句序。",
                    source_family="poetry_2000",
                    author=author,
                )
            )
    return rows


def _collect_zengguang_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = repo_root / "corpus" / "_raw" / "github" / "liuxiaoxiao666__zeng_guang_xian_wen" / "增广贤文.txt"
    if not path.exists():
        return rows

    idx = 0
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        content = str(raw_line).strip()
        content = content.replace("\u3000", " ").strip(" 　")
        if not content or len(content) < 8:
            continue
        rows.append(
            build_row(
                source_id=f"github:liuxiaoxiao666/zeng_guang_xian_wen:增广贤文.txt#{idx}",
                source_type="classical_poem",
                title="增广贤文",
                content=content,
                emotion_tags=["wisdom", "restraint"],
                profile_tag="classical_restraint",
                valence="mixed",
                learn_point="将格言式对照句转为副歌升华句的抽象支点。",
                do_not_copy="禁止复写来源文本原句，需以当代语境重述。",
                source_family="zengguangxianwen",
            )
        )
        idx += 1
        if idx >= 400:
            break
    return rows


def _collect_caigentan_rows(raw_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = raw_root / "hanzhaodeng__chinese-ancient-text" / "菜根谭.json"
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return rows

    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        return rows

    idx = 0
    for article in articles:
        if not isinstance(article, dict):
            continue
        title = str(article.get("title") or "菜根谭").strip() or "菜根谭"
        content_list = article.get("content", [])
        if not isinstance(content_list, list):
            continue
        for line in content_list:
            sentence = str(line).strip()
            if len(sentence) < 8:
                continue
            rows.append(
                build_row(
                    source_id=f"github:hanzhaodeng/chinese-ancient-text:菜根谭.json#{idx}",
                    source_type="classical_poem",
                    title=title,
                    content=sentence,
                    emotion_tags=["wisdom", "equanimity"],
                    profile_tag="classical_restraint",
                    valence="mixed",
                    learn_point="使用反向对照句承接前文意象并完成哲学落点。",
                    do_not_copy="禁止复写来源文本原句，需在歌词中改写为情绪回应。",
                    source_family="caigentan",
                )
            )
            idx += 1
    return rows


def _collect_lyricist_rows_from_zip(*, zip_path: Path, target_by_lyricist: dict[str, int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counts = {k: 0 for k in target_by_lyricist.keys()}

    lyricist_patterns = {
        lyricist: re.compile(rf"(?:作词|詞|词)\s*[:：]?\s*{re.escape(lyricist)}")
        for lyricist in target_by_lyricist.keys()
    }

    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".txt"):
                continue
            if all(counts[k] >= target_by_lyricist[k] for k in counts):
                break

            raw = zf.read(info)
            text = ""
            for enc in ("utf-8", "gb18030", "gbk"):
                try:
                    text = raw.decode(enc)
                    break
                except Exception:
                    continue
            if not text.strip():
                continue

            matched_lyricist = ""
            for lyricist, pattern in lyricist_patterns.items():
                if counts[lyricist] >= target_by_lyricist[lyricist]:
                    continue
                if pattern.search(text):
                    matched_lyricist = lyricist
                    break
            if not matched_lyricist:
                continue

            lines = [_SPACE_RE.sub(" ", ln).strip() for ln in text.splitlines() if ln.strip()]
            lyric_lines = [ln for ln in lines if len(ln) >= 6 and not ln.startswith(("作词", "作曲", "歌手", "专辑", "发行"))]
            content = "\n".join(lyric_lines[:8])
            if len(content) < 30:
                continue

            source_id = f"github:gaussic/Chinese-Lyric-Corpus:{info.filename}#{matched_lyricist}"
            rows.append(
                build_row(
                    source_id=source_id,
                    source_type="modern_lyric",
                    title=Path(info.filename).stem,
                    content=content,
                    emotion_tags=["nostalgia", "imagery", "narrative"],
                    profile_tag="urban_introspective",
                    valence="mixed",
                    learn_point="",
                    do_not_copy="",
                    source_family="golden_lyricist",
                    author=matched_lyricist,
                )
            )
            counts[matched_lyricist] += 1
    return rows


def _collect_modern_candidate_rows(*, modern_path: Path, target_count: int) -> list[dict[str, Any]]:
    payload = _load_json(modern_path)
    if not isinstance(payload, list):
        return []
    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in payload:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip()
        content = str(row.get("content", "")).strip()
        if not source_id or not content:
            continue
        if source_id in seen_ids:
            continue
        if len(content) < 40:
            continue
        lines = [x for x in content.splitlines() if x.strip()]
        if len(lines) < 4:
            continue
        if "golden_lyricist" == str(row.get("source_family", "")).strip():
            continue
        item = dict(row)
        item["source_family"] = "golden_lyricist"
        seen_ids.add(source_id)
        candidates.append(item)
        if len(candidates) >= target_count:
            break
    return candidates


def _collect_existing_golden_rows(*, modern_path: Path) -> list[dict[str, Any]]:
    payload = _load_json(modern_path)
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        if str(item.get("source_family", "")).strip() != "golden_lyricist":
            continue
        source_id = str(item.get("source_id", "")).strip()
        content = str(item.get("content", "")).strip()
        if not source_id or not content or source_id in seen:
            continue
        rows.append(dict(item))
        seen.add(source_id)
    return rows


def _enrich_rows_with_kimi(
    *,
    rows: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
    sleep_seconds: float = 0.2,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        try:
            parsed = _call_kimi_for_anchor(
                api_key=api_key,
                base_url=base_url,
                model=model,
                title=str(item.get("title", "")).strip(),
                source_text=content,
                source_family=str(item.get("source_family", "")).strip(),
                row_type=str(item.get("type", "")).strip(),
            )
        except Exception:
            parsed = {}

        learn_quotes = _normalize_quote_list(parsed.get("learn_point_quotes"))
        dont_quotes = _normalize_quote_list(parsed.get("do_not_copy_quotes"))
        learn_quotes = _filter_quotes_present_in_source(phrases=learn_quotes, source_text=content)
        dont_quotes = _filter_quotes_present_in_source(phrases=dont_quotes, source_text=content)

        if not learn_quotes:
            learn_quotes = _fallback_quotes(content, limit=3)
        if not dont_quotes:
            dont_quotes = _fallback_quotes(content, limit=2)

        learn_analysis = _clean_analysis_text(parsed.get("learn_point_analysis"))
        dont_analysis = _clean_analysis_text(parsed.get("do_not_copy_analysis"))
        if not learn_analysis:
            learn_analysis = _analysis_fallback(source_text=content, quotes=learn_quotes, for_learn=True)
        if not dont_analysis:
            dont_analysis = _analysis_fallback(source_text=content, quotes=dont_quotes, for_learn=False)

        if _GENERIC_ANALYSIS_RE.search(learn_analysis):
            learn_analysis = _analysis_fallback(source_text=content, quotes=learn_quotes, for_learn=True)
        if _GENERIC_ANALYSIS_RE.search(dont_analysis):
            dont_analysis = _analysis_fallback(source_text=content, quotes=dont_quotes, for_learn=False)

        learn_quote_text = _compose_guidance_from_quotes(learn_quotes)
        dont_quote_text = _compose_guidance_from_quotes(dont_quotes)
        item["learn_point"] = f"【分析】：{learn_analysis}【原文佐证】：{learn_quote_text}"
        item["do_not_copy"] = f"【分析】：{dont_analysis}【原文佐证】：{dont_quote_text}"

        tags = parsed.get("emotion_tags")
        if isinstance(tags, list):
            normalized_tags = [str(x).strip() for x in tags if str(x).strip()]
            if normalized_tags:
                item["emotion_tags"] = normalized_tags[:5]

        profile_tag = str(parsed.get("profile_tag", "")).strip()
        if profile_tag:
            item["profile_tag"] = profile_tag

        valence = str(parsed.get("valence", "")).strip()
        if valence in {"positive", "negative", "neutral", "mixed"}:
            item["valence"] = valence

        enriched.append(item)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return enriched


def _validate_analysis_diversity(rows: list[dict[str, Any]], *, window: int = 5, threshold: float = 0.5) -> tuple[bool, dict[str, Any]]:
    analyses: list[str] = []
    for row in rows:
        if str(row.get("source_family", "")).strip() != "golden_lyricist":
            continue
        learn_point = str(row.get("learn_point", "")).strip()
        analysis = learn_point
        if "【分析】：" in learn_point and "【原文佐证】：" in learn_point:
            analysis = learn_point.split("【原文佐证】：", 1)[0]
            analysis = analysis.replace("【分析】：", "").strip()
        analyses.append(_analysis_signature(analysis))

    if len(analyses) < window:
        return True, {"windows_checked": 0, "max_similarity": 0.0}

    max_repeat_ratio = 0.0
    worst_window = -1
    for i in range(0, len(analyses) - window + 1):
        chunk = analyses[i : i + window]
        identical = len(chunk) - len(set(chunk))
        repeat_ratio = identical / max(1, window)
        if repeat_ratio > max_repeat_ratio:
            max_repeat_ratio = repeat_ratio
            worst_window = i
    passed = max_repeat_ratio <= threshold
    return passed, {
        "windows_checked": len(analyses) - window + 1,
        "max_repeat_ratio": round(max_repeat_ratio, 4),
        "worst_window_start": worst_window,
    }


def _dedupe_analysis_text(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    signature_seen: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if str(item.get("source_family", "")).strip() != "golden_lyricist":
            out.append(item)
            continue
        source_id = str(item.get("source_id", "")).strip()
        content = str(item.get("content", "")).strip()
        lp = str(item.get("learn_point", "")).strip()
        dn = str(item.get("do_not_copy", "")).strip()
        lp_analysis = lp
        lp_quote = ""
        if "【分析】：" in lp and "【原文佐证】：" in lp:
            lp_analysis = lp.split("【原文佐证】：", 1)[0].replace("【分析】：", "").strip()
            lp_quote = lp.split("【原文佐证】：", 1)[1].strip()
        dn_analysis = dn
        dn_quote = ""
        if "【分析】：" in dn and "【原文佐证】：" in dn:
            dn_analysis = dn.split("【原文佐证】：", 1)[0].replace("【分析】：", "").strip()
            dn_quote = dn.split("【原文佐证】：", 1)[1].strip()

        signature = _analysis_signature(lp_analysis)
        count = seen.get(lp_analysis, 0)
        signature_count = signature_seen.get(signature, 0)
        if count > 0 or signature_count > 0 or _GENERIC_ANALYSIS_RE.search(lp_analysis):
            quote_phrases = re.findall(r"「([^」]+)」", lp_quote)
            attempt = 0
            while True:
                lp_analysis = _analysis_fallback_variant(
                    source_text=content,
                    quotes=quote_phrases,
                    source_id=f"{source_id}:lp:{attempt}",
                    for_learn=True,
                )
                if _analysis_signature(lp_analysis) not in signature_seen:
                    break
                attempt += 1
                if attempt > 20:
                    break
        seen[lp_analysis] = seen.get(lp_analysis, 0) + 1
        signature_seen[_analysis_signature(lp_analysis)] = signature_seen.get(_analysis_signature(lp_analysis), 0) + 1

        dn_count = seen.get("DN:" + dn_analysis, 0)
        if dn_count > 0 or _GENERIC_ANALYSIS_RE.search(dn_analysis):
            quote_phrases = re.findall(r"「([^」]+)」", dn_quote)
            attempt = 0
            while True:
                dn_analysis = _analysis_fallback_variant(
                    source_text=content,
                    quotes=quote_phrases,
                    source_id=f"{source_id}:dn:{attempt}",
                    for_learn=False,
                )
                if _analysis_signature("DN:" + dn_analysis) not in signature_seen:
                    break
                attempt += 1
                if attempt > 20:
                    break
        seen["DN:" + dn_analysis] = seen.get("DN:" + dn_analysis, 0) + 1

        item["learn_point"] = f"【分析】：{lp_analysis}【原文佐证】：{lp_quote}"
        item["do_not_copy"] = f"【分析】：{dn_analysis}【原文佐证】：{dn_quote}"
        out.append(item)
    return out


def _refine_duplicate_golden_analyses(
    *,
    rows: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        item = dict(row)
        if str(item.get("source_family", "")).strip() != "golden_lyricist":
            out.append(item)
            continue
        lp = str(item.get("learn_point", ""))
        if "【分析】：" not in lp or "【原文佐证】：" not in lp:
            out.append(item)
            continue
        analysis = lp.split("【原文佐证】：", 1)[0].replace("【分析】：", "").strip()
        if analysis not in seen:
            seen.add(analysis)
            out.append(item)
            continue

        content = str(item.get("content", "")).strip()
        title = str(item.get("title", "")).strip()
        lp_quote_text = lp.split("【原文佐证】：", 1)[1].strip()
        dn = str(item.get("do_not_copy", ""))
        dn_quote_text = ""
        if "【原文佐证】：" in dn:
            dn_quote_text = dn.split("【原文佐证】：", 1)[1].strip()
        learn_quotes = re.findall(r"「([^」]+)」", lp_quote_text)
        dont_quotes = re.findall(r"「([^」]+)」", dn_quote_text)

        try:
            refined = _call_kimi_refine_analysis(
                api_key=api_key,
                base_url=base_url,
                model=model,
                title=title,
                source_text=content,
                learn_quotes=learn_quotes,
                dont_quotes=dont_quotes,
            )
        except Exception:
            refined = {"learn_point_analysis": "", "do_not_copy_analysis": ""}

        new_lp_analysis = _clean_analysis_text(refined.get("learn_point_analysis", ""))
        if not new_lp_analysis:
            new_lp_analysis = _analysis_fallback_variant(
                source_text=content,
                quotes=learn_quotes,
                source_id=str(item.get("source_id", "")) + ":refine",
                for_learn=True,
            )
        new_dn_analysis = _clean_analysis_text(refined.get("do_not_copy_analysis", ""))
        if not new_dn_analysis:
            new_dn_analysis = _analysis_fallback_variant(
                source_text=content,
                quotes=dont_quotes,
                source_id=str(item.get("source_id", "")) + ":refine:dn",
                for_learn=False,
            )
        item["learn_point"] = f"【分析】：{new_lp_analysis}【原文佐证】：{lp_quote_text}"
        item["do_not_copy"] = f"【分析】：{new_dn_analysis}【原文佐证】：{dn_quote_text}"
        seen.add(new_lp_analysis)
        out.append(item)
    return out


def _lint_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    passed: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        report = lint_corpus_row(row)
        if report.passed:
            passed.append(dict(row))
        else:
            marked = dict(row)
            marked["_rejected_rules"] = list(report.failed_rules)
            marked["_rejected_reasons"] = list(report.reasons)
            rejected.append(marked)
    return passed, rejected


def _collect_idiom_rows(repo_root: Path, *, target_count: int = 3000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    idiom_path = repo_root / "corpus" / "_raw" / "github" / "Li1Fan__chinese-idiom" / "data" / "idiom.json"
    payload = _load_json(idiom_path)
    if not isinstance(payload, list):
        return rows

    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            continue
        text = str(item.get("word") or "").strip()
        if len(text) > 8 or len(text) < 2:
            continue
        if GARBLED_RE.search(text):
            continue
        if text in seen:
            continue
        seen.add(text)
        explanation = str(item.get("explanation") or "").strip()
        rows.append(
            build_row(
                source_id=f"github:Li1Fan/chinese-idiom:data/idiom.json#{idx}",
                source_type="classical_poem",
                title=text,
                content=text,
                emotion_tags=["imagery", "compression"],
                profile_tag="classical_restraint",
                valence="mixed",
                learn_point="短语锚点用于副歌收束时的高压缩表达。",
                do_not_copy="禁止整句复写成语语境，必须重组上下文。",
                source_family="chengyu",
                author=explanation[:60],
            )
        )
        if len(rows) >= target_count:
            return rows
    return rows


def _backfill_source_family(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if str(item.get("source_family", "")).strip():
            patched.append(item)
            continue

        source_id = str(item.get("source_id", "")).lower()
        if "github:chinese-poetry/chinese-poetry:" in source_id:
            item["source_family"] = "poetry_2000"
        elif "github:li1fan/chinese-idiom:data/idiom.json#" in source_id or source_id.startswith("idiom:auto:"):
            item["source_family"] = "chengyu"
        elif "github:liuxiaoxiao666/zeng_guang_xian_wen:" in source_id:
            item["source_family"] = "zengguangxianwen"
        elif "github:hanzhaodeng/chinese-ancient-text:菜根谭.json#" in source_id:
            item["source_family"] = "caigentan"
        patched.append(item)
    return patched


def _merge_rows_by_source_id(base: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index_by_source_id: dict[str, int] = {}

    def upsert(row: dict[str, Any]) -> None:
        item = dict(row)
        source_id = str(item.get("source_id", "")).strip()
        if not source_id:
            merged.append(item)
            return
        if source_id in index_by_source_id:
            merged[index_by_source_id[source_id]] = item
            return
        index_by_source_id[source_id] = len(merged)
        merged.append(item)

    for row in base:
        if isinstance(row, dict):
            upsert(row)
    for row in incoming:
        if isinstance(row, dict):
            upsert(row)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="auto tag golden anchors and run ingestion")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--raw-root", default="corpus/_raw/github")
    parser.add_argument("--target-modern-golden", type=int, default=300)
    parser.add_argument("--target-classical-llm", type=int, default=240)
    parser.add_argument("--golden-only", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    raw_root = (repo_root / args.raw_root).resolve()

    # refresh required source repos (best effort)
    try:
        _clone_or_refresh("liuxiaoxiao666", "zeng_guang_xian_wen", raw_root)
    except Exception:
        pass
    try:
        _clone_or_refresh("hanzhaodeng", "chinese-ancient-text", raw_root)
    except Exception:
        pass

    classical_poetry_rows = _collect_classical_rows(repo_root)
    zengguang_rows = _collect_zengguang_rows(repo_root)
    caigentan_rows = _collect_caigentan_rows(raw_root)
    classical_rows = list(classical_poetry_rows) + list(zengguang_rows) + list(caigentan_rows)

    zip_path = raw_root / "gaussic__Chinese-Lyric-Corpus" / "Chinese_Lyrics.zip"
    lyricist_rows: list[dict[str, Any]] = []
    if zip_path.exists():
        lyricist_rows = _collect_lyricist_rows_from_zip(
            zip_path=zip_path,
            target_by_lyricist=_GOLDEN_LYRICISTS_TARGETS,
        )

    idiom_rows: list[dict[str, Any]] = _collect_idiom_rows(repo_root, target_count=3000)

    modern_main_path = repo_root / "corpus" / "lyrics_modern_zh.json"
    modern_candidate_rows = _collect_modern_candidate_rows(
        modern_path=modern_main_path,
        target_count=int(args.target_modern_golden),
    )
    existing_golden_rows = _collect_existing_golden_rows(modern_path=modern_main_path)

    env_map = _read_env_map(repo_root)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or env_map.get("OPENAI_API_KEY", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or env_map.get("OPENAI_BASE_URL", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip() or env_map.get("OPENAI_MODEL", "").strip()

    if not (api_key and base_url and model):
        raise RuntimeError("OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL are required for Kimi enrichment")

    enriched_llm_classical_scope: list[dict[str, Any]] = []
    if args.golden_only:
        enriched_classical = []
    else:
        llm_classical_scope = (zengguang_rows + caigentan_rows)[: int(args.target_classical_llm)]
        enriched_llm_classical_scope = _enrich_rows_with_kimi(
            rows=llm_classical_scope,
            api_key=api_key,
            base_url=base_url,
            model=model,
            sleep_seconds=0,
        )
        llm_classical_by_id = {
            str(row.get("source_id", "")).strip(): row
            for row in enriched_llm_classical_scope
            if str(row.get("source_id", "")).strip()
        }
        classical_plus_idiom_rows = classical_rows + idiom_rows
        enriched_classical = [
            dict(llm_classical_by_id.get(str(row.get("source_id", "")).strip(), row))
            for row in classical_plus_idiom_rows
        ]
    modern_scope = _merge_rows_by_source_id(existing_golden_rows, lyricist_rows + modern_candidate_rows)
    enriched_modern = _enrich_rows_with_kimi(
        rows=modern_scope,
        api_key=api_key,
        base_url=base_url,
        model=model,
        sleep_seconds=0,
    )
    enriched_modern = _dedupe_analysis_text(enriched_modern)
    enriched_modern = _refine_duplicate_golden_analyses(
        rows=enriched_modern,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    diversity_ok, diversity_stats = _validate_analysis_diversity(enriched_modern, window=5, threshold=0.5)
    if not diversity_ok:
        raise RuntimeError(f"golden learn_point diversity check failed: {json.dumps(diversity_stats, ensure_ascii=False)}")

    classical_passed, classical_rejected = _lint_rows(enriched_classical)
    modern_passed, modern_rejected = _lint_rows(enriched_modern)

    raw_output_root = repo_root / "corpus" / "_raw"
    raw_output_root.mkdir(parents=True, exist_ok=True)
    if not args.golden_only:
        (raw_output_root / "golden_anchors_classical.json").write_text(
            json.dumps(classical_passed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (raw_output_root / "golden_anchors_modern.json").write_text(
        json.dumps(modern_passed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not args.golden_only:
        (raw_output_root / "golden_anchors_rejected_classical.json").write_text(
            json.dumps(classical_rejected, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (raw_output_root / "golden_anchors_rejected_modern.json").write_text(
        json.dumps(modern_rejected, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    subprocess.run([sys.executable, "scripts/merge_raw_to_corpus.py", "--repo-root", str(repo_root)], check=True, cwd=repo_root)
    subprocess.run([sys.executable, "scripts/run_corpus_ingestion.py", "--strict"], check=True, cwd=repo_root)

    poetry_main = _load_json(repo_root / "corpus" / "poetry_classical.json")
    modern_main = _load_json(repo_root / "corpus" / "lyrics_modern_zh.json")
    poetry_total = len(poetry_main) if isinstance(poetry_main, list) else 0
    modern_total = len(modern_main) if isinstance(modern_main, list) else 0

    print(
        json.dumps(
            {
                "status": "ok",
                "classical_rows_candidate": len(classical_rows) + len(idiom_rows),
                "classical_rows_llm_enriched": len(enriched_llm_classical_scope),
                "classical_rows_passed": len(classical_passed),
                "classical_rows_rejected": len(classical_rejected),
                "modern_rows_candidate": len(modern_scope),
                "golden_lyricist_rows_passed": len(modern_passed),
                "golden_lyricist_rows_rejected": len(modern_rejected),
                "golden_diversity": diversity_stats,
                "poetry_classical_total": poetry_total,
                "lyrics_modern_total": modern_total,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
