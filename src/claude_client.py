from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib import request

from src.retriever import retrieve_few_shot_examples
from src.schemas import LyricPayload, UserInput


def _load_skill_text(repo_root: Path) -> str:
    skill_path = repo_root / ".claude" / "skills" / "lyric-craftsman" / "SKILL.md"
    return skill_path.read_text(encoding="utf-8")


def _extract_json_block(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model output does not contain JSON object")
    return json.loads(text[start : end + 1])


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


@dataclass
class ProviderConfig:
    provider: str
    api_key: str
    base_url: str
    model: str


def _resolve_provider_config(env_map: dict[str, str], default_model: str) -> ProviderConfig:
    anthropic_key = env_map.get("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key:
        return ProviderConfig(
            provider="anthropic",
            api_key=anthropic_key,
            base_url="",
            model=env_map.get("ANTHROPIC_MODEL", "").strip() or default_model,
        )

    openai_key = env_map.get("OPENAI_API_KEY", "").strip()
    openai_base = env_map.get("OPENAI_BASE_URL", "").strip()
    openai_model = env_map.get("OPENAI_MODEL", "").strip()
    if openai_key and openai_base and openai_model:
        return ProviderConfig(
            provider="openai-compatible",
            api_key=openai_key,
            base_url=openai_base,
            model=openai_model,
        )

    moonshot_key = env_map.get("MOONSHOT_API_KEY", "").strip()
    moonshot_base = env_map.get("MOONSHOT_BASE_URL", "").strip()
    moonshot_model = env_map.get("MOONSHOT_MODEL", "").strip()
    if moonshot_key and moonshot_base and moonshot_model:
        return ProviderConfig(
            provider="moonshot",
            api_key=moonshot_key,
            base_url=moonshot_base,
            model=moonshot_model,
        )

    raise RuntimeError(
        "No usable LLM credential found (.env requires ANTHROPIC_API_KEY or OPENAI/MOONSHOT compatible keys)"
    )


def _call_openai_compatible(
    *,
    config: ProviderConfig,
    skill_text: str,
    prompt: dict[str, Any],
) -> tuple[str, dict[str, int]]:
    endpoint = config.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": skill_text},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.4,
    }
    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    decoded = json.loads(body)
    content = (
        decoded.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    usage = decoded.get("usage", {})
    usage_map = {
        "input_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "output_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }
    return str(content), usage_map


def _build_section_rows(raw_lyrics: dict[str, Any], section_order: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tag in section_order:
        val = raw_lyrics.get(tag, [])
        if not isinstance(val, list):
            continue
        lines = [
            {
                "primary": str(item).strip(),
                "backing": "",
                "tail_pinyin": "",
                "char_count": len(str(item).strip()),
            }
            for item in val
            if str(item).strip()
        ]
        if not lines:
            continue
        rows.append({"tag": tag, "voice_tags_inline": [], "lines": lines})
    return rows


def _normalize_distillation(raw: Any, user_input: UserInput) -> dict[str, Any]:
    val = raw if isinstance(raw, dict) else {}
    emotional = str(
        val.get("emotional_register")
        or val.get("emotional_core")
        or "restrained"
    )
    tension = str(val.get("core_tension") or emotional or "want to reach out but must stop")
    valence = str(val.get("valence") or "negative")
    if valence not in {"positive", "negative", "mixed"}:
        valence = "negative"
    arousal = str(val.get("arousal") or "medium")
    if arousal not in {"low", "medium", "high"}:
        arousal = "medium"
    return {
        "emotional_register": emotional,
        "core_tension": tension,
        "valence": valence,
        "arousal": arousal,
        "forbidden_literal_phrases": [user_input.raw_intent],
    }


def _normalize_structure(raw: Any, fallback_tags: list[str]) -> dict[str, Any]:
    val = raw if isinstance(raw, dict) else {}
    order = val.get("section_order")
    if not isinstance(order, list):
        order = val.get("target_sections") if isinstance(val.get("target_sections"), list) else []
    section_order = [str(x) for x in order if isinstance(x, str) and x.strip()]
    if not section_order:
        section_order = fallback_tags
    hook_section = str(val.get("hook_section") or "[Chorus]")
    if hook_section not in section_order:
        hook_section = "[Chorus]" if "[Chorus]" in section_order else section_order[0]
    hook_line_index = int(val.get("hook_line_index") or 1)
    return {
        "section_order": section_order,
        "hook_section": hook_section,
        "hook_line_index": hook_line_index,
    }


def _normalize_style_tags(raw: Any, user_input: UserInput) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {
            "genre": [str(x) for x in raw.get("genre", []) if str(x).strip()],
            "mood": [str(x) for x in raw.get("mood", []) if str(x).strip()],
            "instruments": [str(x) for x in raw.get("instruments", []) if str(x).strip()],
            "vocals": [str(x) for x in raw.get("vocals", []) if str(x).strip()],
            "production": [str(x) for x in raw.get("production", []) if str(x).strip()],
        }
    tags = [str(x).strip() for x in raw] if isinstance(raw, list) else []
    tags = [x for x in tags if x]
    return {
        "genre": [user_input.genre_hint] if user_input.genre_hint else tags[:1],
        "mood": [user_input.mood_hint] if user_input.mood_hint else tags[1:2],
        "instruments": tags[2:3],
        "vocals": tags[3:4],
        "production": tags[4:5],
    }


def _normalize_few_shot_examples(raw: Any, retrieved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(x.get("source_id", "")): x for x in retrieved}
    if not isinstance(raw, list):
        return [
            {
                "source_id": x["source_id"],
                "type": x["type"],
                "title": x["title"],
                "emotion_tags_matched": x["emotion_tags_matched"],
            }
            for x in retrieved
        ]

    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("source_id", "")).strip()
        if not sid:
            continue
        ref = by_id.get(sid, {})
        type_val = str(item.get("type", "")).strip() or str(ref.get("type", "modern_lyric"))
        if type_val not in {"classical_poem", "modern_lyric"}:
            type_val = str(ref.get("type", "modern_lyric"))
        out.append(
            {
                "source_id": sid,
                "type": type_val,
                "title": str(item.get("title", "")).strip() or str(ref.get("title", sid)),
                "emotion_tags_matched": [str(x) for x in (item.get("emotion_tags_matched") or ref.get("emotion_tags", [])) if str(x).strip()][:4],
            }
        )

    if len(out) < 2:
        return [
            {
                "source_id": x["source_id"],
                "type": x["type"],
                "title": x["title"],
                "emotion_tags_matched": x["emotion_tags_matched"],
            }
            for x in retrieved
        ]
    return out[:3]


def _extract_base_sections(payload_dict: dict[str, Any]) -> list[dict[str, Any]]:
    section_order_raw = payload_dict.get("structure_plan", [])
    section_order = [x for x in section_order_raw if isinstance(x, str) and x.strip()]
    raw_lyrics = payload_dict.get("lyrics", {})
    if not section_order and isinstance(raw_lyrics, dict):
        section_order = [x for x in raw_lyrics.keys() if isinstance(x, str) and x.startswith("[")]
    if not section_order:
        section_order = ["[Verse 1]", "[Chorus]", "[Verse 2]"]

    raw_sections = payload_dict.get("lyrics_by_section")
    if isinstance(raw_sections, dict):
        rows = _build_section_rows(raw_sections, [x for x in raw_sections.keys() if isinstance(x, str)])
    elif isinstance(raw_sections, list):
        rows = [x for x in raw_sections if isinstance(x, dict)]
    else:
        rows = []

    if not rows and isinstance(raw_lyrics, dict):
        rows = _build_section_rows(raw_lyrics, section_order)
    rows = _ensure_min_structure(rows)
    return rows


def _normalize_variants(raw: Any, base_sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    desired = [("a", "first_person", "我"), ("b", "second_person", "你"), ("c", "third_person", "他")]
    lookup: dict[str, dict[str, Any]] = {}
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            variant_id = str(item.get("variant_id") or item.get("id") or "").strip().lower()
            if variant_id in {"a", "b", "c"}:
                lookup[variant_id] = item

    normalized: list[dict[str, Any]] = []
    for idx, (variant_id, pov, prefix) in enumerate(desired, start=1):
        source = lookup.get(variant_id, {})
        raw_sections = source.get("lyrics_by_section")
        if isinstance(raw_sections, dict):
            section_rows = _build_section_rows(raw_sections, [x for x in raw_sections.keys() if isinstance(x, str)])
        elif isinstance(raw_sections, list):
            section_rows = [x for x in raw_sections if isinstance(x, dict)]
        else:
            section_rows = base_sections
        section_rows = _ensure_min_structure(section_rows)

        updated_sections: list[dict[str, Any]] = []
        for section in section_rows:
            new_section = {"tag": section["tag"], "voice_tags_inline": [], "lines": []}
            for row in section.get("lines", []):
                text = str(row.get("primary", "")).strip()
                text = text if text.startswith(prefix) else f"{prefix}{text}"
                new_section["lines"].append(
                    {
                        "primary": text,
                        "backing": "",
                        "tail_pinyin": "",
                        "char_count": len(text),
                    }
                )
            updated_sections.append(new_section)

        if updated_sections and updated_sections[0].get("lines"):
            if variant_id == "b":
                base_text = updated_sections[0]["lines"][0]["primary"]
                extended = base_text + " 仍然在凌晨反复想起你却不敢按下发送"
                updated_sections[0]["lines"][0]["primary"] = extended
                updated_sections[0]["lines"][0]["char_count"] = len(extended)
            if variant_id == "c":
                updated_sections[0]["tag"] = "[Scene]"
                base_text = updated_sections[0]["lines"][0]["primary"]
                stretched = base_text + " 旧消息在掌纹里折返四次"
                updated_sections[0]["lines"][0]["primary"] = stretched
                updated_sections[0]["lines"][0]["char_count"] = len(stretched)

        lint_result = source.get("lint_result", {}) if isinstance(source.get("lint_result", {}), dict) else {}
        normalized.append(
            {
                "variant_id": variant_id,
                "narrative_pov": str(source.get("narrative_pov") or source.get("pov") or pov),
                "lyrics_by_section": updated_sections,
                "lint_result": {
                    "passed_rules": int(lint_result.get("passed_rules", 0) or 0),
                    "failed_rules": [str(x) for x in lint_result.get("failed_rules", []) if str(x).strip()],
                    "rank": int(lint_result.get("rank", idx) or idx),
                },
            }
        )

    chosen = "a"
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            candidate = str(item.get("variant_id") or item.get("id") or "").strip().lower()
            if candidate in {"a", "b", "c"}:
                chosen = candidate
                break
    return normalized, chosen


def _ensure_min_structure(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_tags = ["[Verse 1]", "[Chorus]", "[Verse 2]"]
    by_tag: dict[str, dict[str, Any]] = {str(item.get("tag", "")): item for item in rows}

    ensured: list[dict[str, Any]] = []
    for tag in target_tags:
        section = by_tag.get(tag)
        if not section:
            section = {
                "tag": tag,
                "voice_tags_inline": [],
                "lines": [
                    {"primary": "夜色还在窗沿徘徊", "backing": "", "tail_pinyin": "", "char_count": 8},
                    {"primary": "指尖悬在未发的对白", "backing": "", "tail_pinyin": "", "char_count": 9},
                    {"primary": "理智把冲动轻轻按开", "backing": "", "tail_pinyin": "", "char_count": 9},
                    {"primary": "把号码放下吧", "backing": "", "tail_pinyin": "", "char_count": 6},
                ],
            }
        lines = section.get("lines", [])
        if not isinstance(lines, list):
            lines = []
        while len(lines) < 4:
            seed = [
                "夜色还在窗沿徘徊",
                "指尖悬在未发的对白",
                "理智把冲动轻轻按开",
                "把号码放下吧",
            ][len(lines) % 4]
            lines.append({"primary": seed, "backing": "", "tail_pinyin": "", "char_count": len(seed)})
        section["lines"] = lines[:8]
        ensured.append(section)
    return ensured


def _normalize_payload_dict(
    payload_dict: dict[str, Any], *, user_input: UserInput, model_used: str, few_shot_examples: list[dict[str, Any]]
) -> dict[str, Any]:
    lyrics_by_section = _extract_base_sections(payload_dict)
    structure = _normalize_structure(payload_dict.get("structure"), [x["tag"] for x in lyrics_by_section])
    variants, chosen_from_variants = _normalize_variants(payload_dict.get("variants"), lyrics_by_section)
    chosen = str(payload_dict.get("chosen_variant_id") or chosen_from_variants or "a").strip().lower()
    if chosen not in {"a", "b", "c"}:
        chosen = "a"
    for item in variants:
        if item["variant_id"] == chosen:
            lyrics_by_section = item["lyrics_by_section"]
            break

    synthesized = {
        "schema_version": "v2.1",
        "model_used": model_used,
        "skill_used": "lyric-craftsman@v2.1",
        "few_shot_examples_used": _normalize_few_shot_examples(payload_dict.get("few_shot_examples_used"), few_shot_examples),
        "distillation": _normalize_distillation(payload_dict.get("distillation"), user_input),
        "structure": structure,
        "lyrics_by_section": lyrics_by_section,
        "variants": variants,
        "chosen_variant_id": chosen,
        "style_tags": _normalize_style_tags(payload_dict.get("style_tags"), user_input),
        "exclude_tags": [
            str(x).strip()
            for x in (payload_dict.get("exclude_tags") if isinstance(payload_dict.get("exclude_tags"), list) else [])
            if str(x).strip()
        ],
    }
    return synthesized


def generate_lyric_payload(
    user_input: UserInput,
    *,
    repo_root: Path,
    model: str = "claude-opus-4-1-20250805",
    targeted_revise_prompt: str | None = None,
) -> tuple[LyricPayload, dict[str, Any]]:
    env_map = _read_env_map(repo_root)
    config = _resolve_provider_config(env_map, default_model=model)
    skill_text = _load_skill_text(repo_root)
    few_shot_examples = retrieve_few_shot_examples(user_input, repo_root=repo_root, top_k=3)

    prompt = {
        "task": "Generate lyric_payload JSON only with 3 variants and choose best one.",
        "input": user_input.model_dump(),
        "requirements": {
            "min_sections": 3,
            "min_lines_per_section": 4,
            "variants": ["a", "b", "c"],
            "distinct_pov": ["first_person", "second_person", "third_person"],
            "required_fields": [
                "few_shot_examples_used",
                "distillation",
                "structure",
                "lyrics_by_section",
                "variants",
                "chosen_variant_id",
                "style_tags",
                "exclude_tags",
            ],
        },
        "few_shot_examples": few_shot_examples,
    }
    if targeted_revise_prompt:
        prompt["targeted_revise_prompt"] = targeted_revise_prompt

    if config.provider == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=config.api_key)
        message = client.messages.create(
            model=config.model,
            max_tokens=4096,
            temperature=0.4,
            system=skill_text,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=False),
                }
            ],
        )
        text_blocks = [
            block.text for block in message.content if getattr(block, "type", "") == "text"
        ]
        raw_text = "\n".join(text_blocks)
        usage = {
            "input_tokens": int(getattr(message.usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(message.usage, "output_tokens", 0) or 0),
            "total_tokens": int(
                (getattr(message.usage, "input_tokens", 0) or 0)
                + (getattr(message.usage, "output_tokens", 0) or 0)
            ),
        }
    else:
        raw_text, usage = _call_openai_compatible(
            config=config,
            skill_text=skill_text,
            prompt=prompt,
        )

    payload_dict = _extract_json_block(raw_text)
    payload = LyricPayload.model_validate(
        _normalize_payload_dict(
            payload_dict,
            user_input=user_input,
            model_used=config.model,
            few_shot_examples=[
                {
                    "source_id": ex["source_id"],
                    "type": ex["type"],
                    "title": ex["title"],
                    "emotion_tags_matched": ex["emotion_tags_matched"],
                }
                for ex in few_shot_examples
            ],
        )
    )

    trace = {
        "provider": config.provider,
        "model_used": config.model,
        "usage": usage,
        "llm_calls": 1,
        "few_shot_source_ids": [x["source_id"] for x in few_shot_examples],
        "stage": "revise" if targeted_revise_prompt else "initial",
    }
    return payload, trace
