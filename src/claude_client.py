from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib import request

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


def _normalize_payload_dict(
    payload_dict: dict[str, Any], *, user_input: UserInput, model_used: str
) -> dict[str, Any]:
    if {"distillation", "structure", "lyrics_by_section", "style_tags"}.issubset(payload_dict.keys()):
        payload_dict.setdefault("model_used", model_used)
        payload_dict.setdefault("few_shot_examples_used", [])
        payload_dict.setdefault("variants", [])
        payload_dict.setdefault("chosen_variant_id", "a")
        return payload_dict

    raw_lyrics = payload_dict.get("lyrics", {})
    section_order_raw = payload_dict.get("structure_plan", [])
    section_order = [x for x in section_order_raw if isinstance(x, str) and x.strip()]
    if not section_order and isinstance(raw_lyrics, dict):
        section_order = [x for x in raw_lyrics.keys() if isinstance(x, str) and x.strip()]
    if not section_order:
        section_order = ["[Verse 1]", "[Chorus]"]

    lyrics_by_section = _build_section_rows(
        raw_lyrics if isinstance(raw_lyrics, dict) else {},
        section_order,
    )
    if not lyrics_by_section:
        fallback_lines = [line.strip() for line in str(payload_dict.get("hook_line", "")).splitlines() if line.strip()]
        if not fallback_lines:
            fallback_lines = ["把号码放下吧"]
        lyrics_by_section = [
            {
                "tag": "[Chorus]",
                "voice_tags_inline": [],
                "lines": [
                    {
                        "primary": text,
                        "backing": "",
                        "tail_pinyin": "",
                        "char_count": len(text),
                    }
                    for text in fallback_lines
                ],
            }
        ]

    hook_section = "[Chorus]" if any(x.get("tag") == "[Chorus]" for x in lyrics_by_section) else lyrics_by_section[0]["tag"]

    style_list = payload_dict.get("style_tags", [])
    if not isinstance(style_list, list):
        style_list = []
    cleaned_style = [str(x).strip() for x in style_list if str(x).strip()]

    exclude_list = payload_dict.get("exclude_tags", [])
    if not isinstance(exclude_list, list):
        exclude_list = []

    synthesized = {
        "schema_version": "v2.1",
        "model_used": model_used,
        "skill_used": "lyric-craftsman@v2.1",
        "few_shot_examples_used": [
            {
                "source_id": "fallback-classical-001",
                "type": "classical_poem",
                "title": "fallback-classical",
                "emotion_tags_matched": ["restraint", "longing"],
            },
            {
                "source_id": "fallback-modern-001",
                "type": "modern_lyric",
                "title": "fallback-modern",
                "emotion_tags_matched": ["distance", "regret"],
            },
        ],
        "distillation": {
            "emotional_register": str(payload_dict.get("emotional_core", "restrained")) or "restrained",
            "core_tension": str(payload_dict.get("emotional_core", "want to reach out but must stop"))
            or "want to reach out but must stop",
            "valence": "negative",
            "arousal": "medium",
            "forbidden_literal_phrases": [user_input.raw_intent],
        },
        "structure": {
            "section_order": [item["tag"] for item in lyrics_by_section],
            "hook_section": hook_section,
            "hook_line_index": 1,
        },
        "lyrics_by_section": lyrics_by_section,
        "variants": [
            {
                "variant_id": "a",
                "narrative_pov": "first_person",
                "lyrics_by_section": lyrics_by_section,
                "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 1},
            },
            {
                "variant_id": "b",
                "narrative_pov": "second_person",
                "lyrics_by_section": lyrics_by_section,
                "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 2},
            },
            {
                "variant_id": "c",
                "narrative_pov": "third_person",
                "lyrics_by_section": lyrics_by_section,
                "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 3},
            },
        ],
        "chosen_variant_id": "a",
        "style_tags": {
            "genre": [user_input.genre_hint] if user_input.genre_hint else cleaned_style[:1],
            "mood": [user_input.mood_hint] if user_input.mood_hint else cleaned_style[1:2],
            "instruments": cleaned_style[2:3],
            "vocals": cleaned_style[3:4],
            "production": cleaned_style[4:5],
        },
        "exclude_tags": [str(x).strip() for x in exclude_list if str(x).strip()],
    }
    return synthesized


def generate_lyric_payload(
    user_input: UserInput,
    *,
    repo_root: Path,
    model: str = "claude-opus-4-1-20250805",
) -> tuple[LyricPayload, dict[str, Any]]:
    env_map = _read_env_map(repo_root)
    config = _resolve_provider_config(env_map, default_model=model)
    skill_text = _load_skill_text(repo_root)

    prompt = {
        "task": "Generate lyric_payload JSON only.",
        "input": user_input.model_dump(),
    }

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
        _normalize_payload_dict(payload_dict, user_input=user_input, model_used=config.model)
    )

    trace = {
        "provider": config.provider,
        "model_used": config.model,
        "usage": usage,
        "llm_calls": 1,
    }
    return payload, trace
