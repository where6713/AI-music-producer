from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib import request

from src.profile_router import resolve_active_profile
from src.retriever import retrieve_few_shot_examples
from src.schemas import LyricPayload, UserInput


PROFILE_IDS = {
    "urban_introspective",
    "uplift_pop",
    "club_dance",
    "ambient_meditation",
    "classical_restraint",
    "indie_groove",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _style_records_to_profile_vocab(records: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    out: dict[str, dict[str, list[str]]] = {}
    for row in records:
        profile = str(row.get("profile", "")).strip()
        if profile not in PROFILE_IDS:
            continue
        slot = out.setdefault(profile, {
            "genre": [], "mood": [], "instruments": [], "vocals": [], "production": [], "examples": []
        })
        mappings = {
            "genre": row.get("genre_tags", []),
            "mood": row.get("mood_tags", []),
            "instruments": row.get("instrument_tags", []),
            "production": row.get("production_tags", []),
            "vocals": list((row.get("meta_tags") or {}).get("vocal", [])) if isinstance(row.get("meta_tags"), dict) else [],
            "examples": row.get("example_style_lines", []),
        }
        for key, raw in mappings.items():
            if not isinstance(raw, list):
                continue
            for item in raw:
                text = str(item).strip()
                if text and text not in slot[key]:
                    slot[key].append(text)
    return out


def _load_style_knowledge(repo_root: Path) -> dict[str, Any]:
    knowledge_dir = repo_root / "corpus" / "_knowledge"
    suno = _load_json(knowledge_dir / "suno_style_vocab.json")
    minimax = _load_json(knowledge_dir / "minimax_style_vocab.json")

    def _extract_vocab(payload: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
        by_profile = payload.get("by_profile", {})
        if isinstance(by_profile, dict) and by_profile:
            normalized: dict[str, dict[str, list[str]]] = {}
            for profile, vals in by_profile.items():
                if str(profile).strip() not in PROFILE_IDS or not isinstance(vals, dict):
                    continue
                normalized[str(profile)] = {
                    "genre": [str(x).strip() for x in vals.get("genre", []) if str(x).strip()],
                    "mood": [str(x).strip() for x in vals.get("mood", []) if str(x).strip()],
                    "instruments": [str(x).strip() for x in vals.get("instruments", []) if str(x).strip()],
                    "vocals": [str(x).strip() for x in vals.get("vocal", vals.get("vocals", [])) if str(x).strip()],
                    "production": [str(x).strip() for x in vals.get("production", []) if str(x).strip()],
                    "examples": [str(x).strip() for x in vals.get("example_combos", vals.get("example_style_lines", [])) if str(x).strip()],
                }
            return normalized
        records = payload.get("records", [])
        if isinstance(records, list):
            return _style_records_to_profile_vocab([x for x in records if isinstance(x, dict)])
        return {}

    return {
        "primary": _extract_vocab(suno),
        "secondary": _extract_vocab(minimax),
    }


def _build_profile_style_examples(repo_root: Path, active_profile: str) -> list[str]:
    knowledge = _load_style_knowledge(repo_root)
    primary = knowledge.get("primary", {}).get(active_profile, {}) if active_profile else {}
    examples = [str(x).strip() for x in primary.get("examples", []) if str(x).strip()] if isinstance(primary, dict) else []
    selected = examples[:3]
    lines: list[str] = []
    for idx, ex in enumerate(selected, start=1):
        lines.append(
            f"{idx}. {ex} (source_repo=danlex/suno-lab|VRVirtuosos/awesome-suno-prompts, source_path=corpus/_knowledge/suno_style_vocab.json)"
        )
    return lines


def _load_profile_prosody(repo_root: Path, active_profile: str) -> dict[str, Any]:
    if not active_profile:
        return {}
    registry = _load_json(repo_root / "src" / "profiles" / "registry.json")
    profiles = registry.get("profiles", {})
    profile = profiles.get(active_profile, {}) if isinstance(profiles, dict) else {}
    prosody = profile.get("prosody", {}) if isinstance(profile, dict) else {}
    return prosody if isinstance(prosody, dict) else {}


def _inject_prompt_contract(skill_text: str, prosody: dict[str, Any], active_profile: str) -> str:
    replacements = {
        "{{bpm}}": str(prosody.get("bpm", "")),
        "{{syllable_budget_min}}": str(prosody.get("syllable_budget_min", "")),
        "{{syllable_budget_max}}": str(prosody.get("syllable_budget_max", "")),
        "{{active_profile}}": active_profile,
    }
    result = skill_text
    for key, val in replacements.items():
        if key in result:
            result = result.replace(key, val)
    if isinstance(prosody, dict) and prosody:
        verse_min = prosody.get("verse_line_min", "")
        verse_max = prosody.get("verse_line_max", "")
        chorus_min = prosody.get("chorus_line_min", "")
        chorus_max = prosody.get("chorus_line_max", "")
        bridge_min = prosody.get("bridge_line_min", "")
        bridge_max = prosody.get("bridge_line_max", "")
        contract_block = (
            "\n\n## Absolute Prosody Contract\n"
            "- 逐段执行行级字数范围，不得机械等长。\n"
            f"- Verse 行字数建议范围: {verse_min}-{verse_max}\n"
            f"- Chorus 行字数建议范围: {chorus_min}-{chorus_max}\n"
            f"- Bridge/Outro 行字数建议范围: {bridge_min}-{bridge_max}\n"
            "- 若某行触及下边界，必须在该段加 (Pause) 或 (Breathe)。\n"
            "- 若某行触及上边界，必须在该段加 [Fast Flow]。\n"
            "- 输出必须保留这些标签，禁止在后处理阶段移除。\n"
        )
        if "## Absolute Prosody Contract" not in result:
            result = result + contract_block
    return result


def _load_skill_text(repo_root: Path, *, active_profile: str = "") -> str:
    skill_root = repo_root / ".claude" / "skills" / "lyric-craftsman"
    core = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    if not active_profile:
        return core
    fragment_path = skill_root / "fragments" / f"{active_profile}.md"
    if not fragment_path.exists():
        return core
    fragment = fragment_path.read_text(encoding="utf-8")
    style_example_lines = _build_profile_style_examples(repo_root, active_profile)
    style_examples_block = ""
    if style_example_lines:
        style_examples_block = "\n\n## Profile Style Examples (Traceable)\n\n" + "\n".join(style_example_lines)
    skill_text = f"{core}\n\n# Active Profile Fragment\n\n{fragment}{style_examples_block}"
    prosody = _load_profile_prosody(repo_root, active_profile)
    return _inject_prompt_contract(skill_text, prosody, active_profile)


def _normalize_text(tag: str) -> str:
    return str(tag or "").strip().lower()


def _enforce_vocab_style_tags(style_tags: dict[str, Any], user_input: UserInput, repo_root: Path, active_profile: str) -> tuple[dict[str, Any], dict[str, Any]]:
    knowledge = _load_style_knowledge(repo_root)
    primary_profile = knowledge.get("primary", {}).get(active_profile, {}) if active_profile else {}
    secondary_profile = knowledge.get("secondary", {}).get(active_profile, {}) if active_profile else {}

    allowed_by_key: dict[str, list[str]] = {}
    for key in ("genre", "mood", "instruments", "vocals", "production"):
        p = primary_profile.get(key, []) if isinstance(primary_profile, dict) else []
        s = secondary_profile.get(key, []) if isinstance(secondary_profile, dict) else []
        allowed: list[str] = []
        for item in [*p, *s]:
            text = str(item).strip()
            if text and text not in allowed:
                allowed.append(text)
        allowed_by_key[key] = allowed

    fallback_hint = {
        "genre": user_input.genre_hint,
        "mood": user_input.mood_hint,
        "instruments": "",
        "vocals": "",
        "production": "",
    }
    out: dict[str, list[str]] = {}
    total = 0
    hit = 0
    oov = 0
    replacements = 0
    for key in ("genre", "mood", "instruments", "vocals", "production"):
        requested = [str(x).strip() for x in style_tags.get(key, []) if str(x).strip()]
        total += len(requested)
        allowed = allowed_by_key[key]
        allowed_norm = {_normalize_text(x): x for x in allowed}
        selected: list[str] = []
        for tag in requested:
            mapped = allowed_norm.get(_normalize_text(tag))
            if mapped:
                hit += 1
                if mapped not in selected:
                    selected.append(mapped)
            else:
                oov += 1
        if not selected:
            hinted = str(fallback_hint.get(key, "")).strip()
            mapped_hint = allowed_norm.get(_normalize_text(hinted)) if hinted else None
            if mapped_hint:
                selected = [mapped_hint]
                replacements += 1
            elif allowed:
                selected = [allowed[0]]
                replacements += 1
        out[key] = selected

    hit_rate = float(hit / total) if total else 1.0
    oov_ratio = float(oov / total) if total else 0.0
    metrics = {
        "active_profile": active_profile,
        "style_vocab_total_tags": total,
        "style_vocab_hits": hit,
        "style_vocab_oov": oov,
        "style_vocab_hit_rate": hit_rate,
        "style_oov_ratio": oov_ratio,
        "style_replacements": replacements,
        "primary_vocab_source": "corpus/_knowledge/suno_style_vocab.json",
        "secondary_vocab_source": "corpus/_knowledge/minimax_style_vocab.json",
        "injected_profile_examples": min(3, len(primary_profile.get("examples", []))) if isinstance(primary_profile, dict) else 0,
    }
    return out, metrics


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
        if anthropic_key.startswith("sk-kimi-"):
            raise RuntimeError(
                "Invalid ANTHROPIC_API_KEY: detected Kimi-style key. Use OPENAI/MOONSHOT variables for Kimi-compatible endpoints."
            )
        return ProviderConfig(
            provider="anthropic",
            api_key=anthropic_key,
            base_url="",
            model=env_map.get("ANTHROPIC_MODEL", "").strip() or default_model,
        )

    openai_key = env_map.get("OPENAI_API_KEY", "").strip()
    openai_base = env_map.get("OPENAI_BASE_URL", "").strip()
    openai_model = env_map.get("OPENAI_MODEL", "").strip()
    openai_fields = [openai_key, openai_base, openai_model]
    if any(openai_fields) and not all(openai_fields):
        raise RuntimeError(
            "Incomplete OPENAI configuration: OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL are all required."
        )
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
    moonshot_fields = [moonshot_key, moonshot_base, moonshot_model]
    if any(moonshot_fields) and not all(moonshot_fields):
        raise RuntimeError(
            "Incomplete MOONSHOT configuration: MOONSHOT_API_KEY, MOONSHOT_BASE_URL, and MOONSHOT_MODEL are all required."
        )
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
    temperature: float,
    force_json_object: bool = False,
) -> tuple[str, dict[str, int]]:
    endpoint = config.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": skill_text},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": temperature,
    }
    if force_json_object:
        payload["response_format"] = {"type": "json_object"}
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
    def _extract_inline_metatags(text: str) -> tuple[str, list[str]]:
        raw = str(text or "")
        found: list[str] = []
        for tag in ("(Pause)", "(Breathe)", "[Fast Flow]"):
            if tag in raw and tag not in found:
                found.append(tag)
                raw = raw.replace(tag, "")
        return raw.strip(), found

    def _normalize_tag(tag: str) -> str:
        clean = tag.strip()
        if clean.startswith("[") and clean.endswith("]"):
            return clean
        lower = clean.lower()
        if lower.startswith("pre-chorus"):
            return "[Pre-Chorus]"
        if lower.startswith("post-chorus"):
            return "[Post-Chorus]"
        if lower.startswith("final chorus"):
            return "[Final Chorus]"
        if lower.startswith("outro"):
            return "[Outro]"
        if lower.startswith("intro"):
            return "[Intro]"
        if lower.startswith("verse"):
            suffix = clean[len("verse") :].strip() or "1"
            return f"[Verse {suffix}]"
        if lower.startswith("chorus"):
            return "[Chorus]"
        if lower.startswith("bridge"):
            return "[Bridge]"
        return clean

    def _looks_like_section_key(tag: str) -> bool:
        clean = tag.strip()
        if not clean:
            return False
        if clean.startswith("[") and clean.endswith("]"):
            return True
        lower = clean.lower()
        return lower.startswith((
            "verse",
            "chorus",
            "pre-chorus",
            "post-chorus",
            "bridge",
            "outro",
            "intro",
            "hook",
            "drop",
            "build-up",
            "breakdown",
            "instrumental",
            "final chorus",
        ))

    rows: list[dict[str, Any]] = []
    for tag in section_order:
        if not _looks_like_section_key(tag):
            continue
        val = raw_lyrics.get(tag, [])
        if isinstance(val, str):
            val = [x for x in val.splitlines() if x.strip()]
        if not isinstance(val, list):
            continue
        lines: list[dict[str, Any]] = []
        voice_tags_inline: list[str] = []
        for item in val:
            if isinstance(item, str):
                text = item.strip()
                text, tags = _extract_inline_metatags(text)
                for t in tags:
                    if t not in voice_tags_inline:
                        voice_tags_inline.append(t)
                char_count = len(text)
            elif isinstance(item, dict):
                # nested section object, not line object
                if any(k in item for k in ("tag", "name", "section")):
                    continue
                text = str(item.get("primary") or item.get("text") or item.get("line") or "").strip()
                text, tags = _extract_inline_metatags(text)
                for t in tags:
                    if t not in voice_tags_inline:
                        voice_tags_inline.append(t)
                char_count = int(item.get("char_count", 0) or len(text))
            else:
                continue
            if not text:
                continue
            lines.append(
                {
                    "primary": text,
                    "backing": "",
                    "tail_pinyin": "",
                    "char_count": char_count,
                }
            )
        if not lines:
            continue
        rows.append({"tag": _normalize_tag(tag), "voice_tags_inline": voice_tags_inline, "lines": lines})
    return rows


def _normalize_section_tag(raw_tag: object) -> str:
    clean = str(raw_tag or "").strip()
    if not clean:
        return ""
    lower = clean.lower()
    if lower in {
        "pov",
        "narrative_pov",
        "lint_result",
        "variant_id",
        "id",
        "rank",
        "passed_rules",
        "failed_rules",
    }:
        return ""
    if clean.startswith("[") and clean.endswith("]"):
        return clean
    if lower.startswith("pre-chorus"):
        return "[Pre-Chorus]"
    if lower.startswith("post-chorus"):
        return "[Post-Chorus]"
    if lower.startswith("final chorus"):
        return "[Final Chorus]"
    if lower.startswith("outro"):
        return "[Outro]"
    if lower.startswith("intro"):
        return "[Intro]"
    if lower.startswith("verse"):
        suffix = clean[len("verse") :].strip() or "1"
        return f"[Verse {suffix}]"
    if lower.startswith("chorus"):
        return "[Chorus]"
    if lower.startswith("bridge"):
        return "[Bridge]"
    return clean


def _extract_inline_metatags(text: str) -> tuple[str, list[str]]:
    raw = str(text or "")
    found: list[str] = []
    for tag in ("(Pause)", "(Breathe)", "[Fast Flow]"):
        if tag in raw and tag not in found:
            found.append(tag)
            raw = raw.replace(tag, "")
    return raw.strip(), found


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
    normalized_order: list[str] = []
    for tag in section_order:
        clean = tag.strip()
        lower = clean.lower()
        if clean.startswith("[") and clean.endswith("]"):
            normalized_order.append(clean)
        elif lower.startswith("verse"):
            suffix = clean[len("verse") :].strip() or "1"
            normalized_order.append(f"[Verse {suffix}]")
        elif lower.startswith("chorus"):
            normalized_order.append("[Chorus]")
        elif lower.startswith("bridge"):
            normalized_order.append("[Bridge]")
        else:
            normalized_order.append(clean)
    section_order = [x for x in normalized_order if x]
    if not section_order:
        section_order = fallback_tags
    if not section_order:
        section_order = ["[Verse 1]", "[Chorus]"]
    hook_section = str(val.get("hook_section") or "[Chorus]")
    if hook_section not in section_order:
        hook_section = "[Chorus]" if "[Chorus]" in section_order else section_order[0]
    hook_idx_raw = val.get("hook_line_index", 1)
    try:
        hook_line_index = int(hook_idx_raw)
    except (TypeError, ValueError):
        hook_line_index = 1
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


def _validate_payload_shape(payload_dict: dict[str, Any]) -> dict[str, Any]:
    raw = payload_dict.get("lyrics_by_section")

    if isinstance(raw, list):
        return {
            "ok": True,
            "shape": "array<section>",
            "reason_code": "none",
        }

    if isinstance(raw, dict):
        keys = [str(k).strip().lower() for k in raw.keys()]
        if keys and all(k in {"a", "b", "c"} for k in keys):
            return {
                "ok": True,
                "shape": "object<variant_id,section_like>",
                "reason_code": "none",
            }
        return {
            "ok": False,
            "shape": "object<unknown>",
            "reason_code": "shape_lyrics_dict_not_variant_keyed",
        }

    return {
        "ok": False,
        "shape": "missing_or_invalid",
        "reason_code": "shape_missing_lyrics_by_section",
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
                "learn_point": str(x.get("learn_point", "")).strip(),
                "do_not_copy": str(x.get("do_not_copy", "")).strip(),
                "content_preview": str(x.get("content", "")).strip()[:30],
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
                "learn_point": str(item.get("learn_point", "")).strip() or str(ref.get("learn_point", "")).strip(),
                "do_not_copy": str(item.get("do_not_copy", "")).strip() or str(ref.get("do_not_copy", "")).strip(),
                "content_preview": str(ref.get("content", "")).strip()[:30],
            }
        )

    if len(out) < 2:
        return [
            {
                "source_id": x["source_id"],
                "type": x["type"],
                "title": x["title"],
                "emotion_tags_matched": x["emotion_tags_matched"],
                "learn_point": str(x.get("learn_point", "")).strip(),
                "do_not_copy": str(x.get("do_not_copy", "")).strip(),
                "content_preview": str(x.get("content", "")).strip()[:30],
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
        if not rows:
            chosen_variant = str(payload_dict.get("chosen_variant_id") or payload_dict.get("chosen_variant") or "").strip().lower()
            candidate_values: list[Any] = []
            if chosen_variant and isinstance(raw_sections.get(chosen_variant), (dict, list)):
                candidate_values.append(raw_sections.get(chosen_variant))
            for key in ("a", "b", "c"):
                val = raw_sections.get(key)
                if isinstance(val, (dict, list)) and val not in candidate_values:
                    candidate_values.append(val)
            for _, val in raw_sections.items():
                if isinstance(val, (dict, list)) and val not in candidate_values:
                    candidate_values.append(val)

            for candidate in candidate_values:
                if isinstance(candidate, dict):
                    candidate_rows = _build_section_rows(candidate, [x for x in candidate.keys() if isinstance(x, str)])
                elif isinstance(candidate, list):
                    candidate_rows = [x for x in candidate if isinstance(x, dict)]
                else:
                    candidate_rows = []
                if candidate_rows:
                    rows = candidate_rows
                    break
    elif isinstance(raw_sections, list):
        rows = [x for x in raw_sections if isinstance(x, dict)]
    else:
        rows = []

    if not rows and isinstance(raw_lyrics, dict):
        rows = _build_section_rows(raw_lyrics, section_order)

    normalized_rows: list[dict[str, Any]] = []
    for section in rows:
        tag = ""
        if isinstance(section, dict):
            tag = _normalize_section_tag(section.get("tag") or section.get("name") or section.get("section"))
        if not tag:
            continue
        lines_raw = section.get("lines", []) if isinstance(section, dict) else []
        if not isinstance(lines_raw, list):
            lines_raw = []
        section_voice_tags: list[str] = [
            str(x).strip()
            for x in (section.get("voice_tags_inline", []) if isinstance(section, dict) else [])
            if str(x).strip()
        ]
        lines: list[dict[str, Any]] = []
        for row in lines_raw:
            if isinstance(row, str):
                text = row.strip()
                text, tags = _extract_inline_metatags(text)
                for t in tags:
                    if t not in section_voice_tags:
                        section_voice_tags.append(t)
                row_obj: dict[str, Any] = {}
            elif isinstance(row, dict):
                text = str(row.get("primary") or row.get("text") or row.get("line") or "").strip()
                text, tags = _extract_inline_metatags(text)
                for t in tags:
                    if t not in section_voice_tags:
                        section_voice_tags.append(t)
                row_obj = row
            else:
                continue
            if not text:
                continue
            lines.append(
                {
                    "primary": text,
                    "backing": str(row_obj.get("backing", "")).strip(),
                    "tail_pinyin": str(row_obj.get("tail_pinyin", "")).strip(),
                    "char_count": int(row_obj.get("char_count", 0) or len(text)),
                }
            )
        if lines:
            normalized_rows.append({"tag": tag, "voice_tags_inline": section_voice_tags, "lines": lines})
    return normalized_rows


def _normalize_variants(raw: Any, base_sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    desired = [("a", "first_person"), ("b", "second_person"), ("c", "third_person")]
    lookup: dict[str, dict[str, Any]] = {}
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            variant_id = str(item.get("variant_id") or item.get("id") or "").strip().lower()
            if variant_id in {"a", "b", "c"}:
                lookup[variant_id] = item
    elif isinstance(raw, dict):
        # model returned variants as {"a": {...}, "b": {...}, "c": {...}}
        for key, val in raw.items():
            k = str(key).strip().lower()
            if k in {"a", "b", "c"} and isinstance(val, dict):
                lookup[k] = val

    normalized: list[dict[str, Any]] = []
    for idx, (variant_id, pov) in enumerate(desired, start=1):
        source = lookup.get(variant_id, {})
        raw_sections = source.get("lyrics_by_section")
        if raw_sections is None:
            raw_sections = source.get("lyrics")
        if isinstance(raw_sections, dict):
            sections_list = raw_sections.get("sections")
            if isinstance(sections_list, list):
                section_rows = [x for x in sections_list if isinstance(x, dict)]
            else:
                section_rows = _build_section_rows(raw_sections, [x for x in raw_sections.keys() if isinstance(x, str)])
        elif isinstance(raw_sections, list):
            section_rows = [x for x in raw_sections if isinstance(x, dict)]
        else:
            section_rows = base_sections

        updated_sections: list[dict[str, Any]] = []
        for section in section_rows:
            if not isinstance(section, dict):
                continue
            tag = _normalize_section_tag(section.get("tag") or section.get("name") or section.get("section"))
            if not tag:
                continue
            lines_raw = section.get("lines", [])
            if not isinstance(lines_raw, list):
                lines_raw = []

            section_voice_tags: list[str] = [
                str(x).strip()
                for x in (section.get("voice_tags_inline", []) if isinstance(section, dict) else [])
                if str(x).strip()
            ]
            new_section = {"tag": tag, "voice_tags_inline": section_voice_tags, "lines": []}
            for row in lines_raw:
                if isinstance(row, str):
                    text = row.strip()
                    text, tags = _extract_inline_metatags(text)
                    for t in tags:
                        if t not in new_section["voice_tags_inline"]:
                            new_section["voice_tags_inline"].append(t)
                elif isinstance(row, dict):
                    text = str(row.get("primary") or row.get("text") or row.get("line") or "").strip()
                    text, tags = _extract_inline_metatags(text)
                    for t in tags:
                        if t not in new_section["voice_tags_inline"]:
                            new_section["voice_tags_inline"].append(t)
                else:
                    continue
                if not text:
                    continue
                new_section["lines"].append(
                    {
                        "primary": text,
                        "backing": "",
                        "tail_pinyin": "",
                        "char_count": len(text),
                    }
                )
            if new_section["lines"]:
                updated_sections.append(new_section)

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
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                candidate = str(item.get("variant_id") or item.get("id") or "").strip().lower()
                if candidate in {"a", "b", "c"}:
                    chosen = candidate
                    break
    elif isinstance(raw, dict):
        # dict format: pick first key as a proxy (actual chosen comes from payload level)
        for k in ("a", "b", "c"):
            if k in raw:
                chosen = k
                break
    return normalized, chosen


def _normalize_payload_dict(
    payload_dict: dict[str, Any], *, user_input: UserInput, model_used: str, few_shot_examples: list[dict[str, Any]], repo_root: Path, active_profile: str
) -> dict[str, Any]:
    normalized, _ = _normalize_payload_dict_with_meta(
        payload_dict,
        user_input=user_input,
        model_used=model_used,
        few_shot_examples=few_shot_examples,
        repo_root=repo_root,
        active_profile=active_profile,
    )
    return normalized


def _normalize_payload_dict_with_meta(
    payload_dict: dict[str, Any], *, user_input: UserInput, model_used: str, few_shot_examples: list[dict[str, Any]], repo_root: Path, active_profile: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    lyrics_by_section = _extract_base_sections(payload_dict)
    structure = _normalize_structure(payload_dict.get("structure"), [x["tag"] for x in lyrics_by_section])
    variants, chosen_from_variants = _normalize_variants(payload_dict.get("variants"), lyrics_by_section)
    chosen_raw = str(
        payload_dict.get("chosen_variant_id") or payload_dict.get("chosen_variant") or ""
    ).strip().lower()
    chosen = chosen_raw if chosen_raw in {"a", "b", "c"} else "a"
    normalize_branch = "list_passthrough"
    chosen_variant_id_source = "raw"
    chosen_variant_id_resolved: str | None = chosen

    raw_lbs = payload_dict.get("lyrics_by_section")
    if isinstance(raw_lbs, dict):
        lowers = {str(k).strip().lower() for k in raw_lbs.keys()}
        variant_ids = {str(v.get("variant_id", "")).strip().lower() for v in variants if isinstance(v, dict)}
        variant_ids = {x for x in variant_ids if x}
        variant_keyed = bool(lowers) and (
            lowers.issubset({"a", "b", "c"})
            or (variant_ids and lowers.issubset(variant_ids))
        )
        if variant_keyed:
            candidate_key = chosen_raw if chosen_raw in {"a", "b", "c"} else ""
            candidate = raw_lbs.get(candidate_key) if candidate_key else None
            extracted = []
            if isinstance(candidate, dict):
                extracted = _build_section_rows(candidate, [x for x in candidate.keys() if isinstance(x, str)])
            elif isinstance(candidate, list):
                extracted = [x for x in candidate if isinstance(x, dict)]
            if extracted:
                lyrics_by_section = extracted
                normalize_branch = "variant_map_chosen"
                chosen = candidate_key
                chosen_variant_id_resolved = candidate_key
                chosen_variant_id_source = "raw"
            else:
                top1 = ""
                ranked = sorted(
                    [v for v in variants if isinstance(v, dict)],
                    key=lambda x: int((x.get("lint_result") or {}).get("rank", 99) or 99),
                )
                if ranked:
                    top1 = str(ranked[0].get("variant_id", "")).strip().lower()
                if top1:
                    candidate = raw_lbs.get(top1)
                    extracted = []
                    if isinstance(candidate, dict):
                        extracted = _build_section_rows(candidate, [x for x in candidate.keys() if isinstance(x, str)])
                    elif isinstance(candidate, list):
                        extracted = [x for x in candidate if isinstance(x, dict)]
                    if extracted:
                        lyrics_by_section = extracted
                        chosen = top1
                        normalize_branch = "variant_map_fallback_top1"
                        chosen_variant_id_resolved = top1
                        chosen_variant_id_source = "lint_top1"
                if not extracted:
                    for key in ("a", "b", "c"):
                        candidate = raw_lbs.get(key)
                        if isinstance(candidate, dict):
                            extracted = _build_section_rows(candidate, [x for x in candidate.keys() if isinstance(x, str)])
                        elif isinstance(candidate, list):
                            extracted = [x for x in candidate if isinstance(x, dict)]
                        else:
                            extracted = []
                        if extracted:
                            lyrics_by_section = extracted
                            chosen = key
                            normalize_branch = "variant_map_fallback_first_nonempty"
                            chosen_variant_id_resolved = key
                            chosen_variant_id_source = "first_nonempty"
                            break
    for item in variants:
        if item["variant_id"] == chosen:
            candidate_sections = item.get("lyrics_by_section", [])
            if isinstance(candidate_sections, list) and candidate_sections:
                lyrics_by_section = candidate_sections
            break
    if not lyrics_by_section:
        for item in variants:
            candidate_sections = item.get("lyrics_by_section", [])
            if isinstance(candidate_sections, list) and candidate_sections:
                lyrics_by_section = candidate_sections
                chosen = str(item.get("variant_id", chosen)).strip().lower() or chosen
                break

    normalized_style = _normalize_style_tags(payload_dict.get("style_tags"), user_input)
    constrained_style, style_metrics = _enforce_vocab_style_tags(normalized_style, user_input, repo_root, active_profile)

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
        "style_tags": constrained_style,
        "exclude_tags": [
            str(x).strip()
            for x in (payload_dict.get("exclude_tags") if isinstance(payload_dict.get("exclude_tags"), list) else [])
            if str(x).strip()
        ],
        "style_vocab_metrics": style_metrics,
    }
    prosody_contract = _load_profile_prosody(repo_root, active_profile)
    _apply_prosody_metatag_contract(synthesized, prosody_contract)
    return synthesized, {
        "normalize_branch": normalize_branch,
        "chosen_variant_id_resolved": chosen_variant_id_resolved,
        "chosen_variant_id_source": chosen_variant_id_source,
    }


def _needs_parser_repair(normalized_payload: dict[str, Any]) -> bool:
    rows = normalized_payload.get("lyrics_by_section", []) if isinstance(normalized_payload, dict) else []
    return not (isinstance(rows, list) and len(rows) > 0)


def _apply_prosody_metatag_contract(payload: dict[str, Any], prosody_contract: dict[str, Any]) -> None:
    if not isinstance(payload, dict) or not isinstance(prosody_contract, dict):
        return

    section_key_map: dict[str, tuple[str, str]] = {
        "[Verse]": ("verse_line_min", "verse_line_max"),
        "[Verse 1]": ("verse_line_min", "verse_line_max"),
        "[Verse 2]": ("verse_line_min", "verse_line_max"),
        "[Pre-Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Final Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Bridge]": ("bridge_line_min", "bridge_line_max"),
        "[Outro]": ("bridge_line_min", "bridge_line_max"),
    }

    def _bare_len(text: str) -> int:
        raw = str(text or "")
        for tag in ("(Pause)", "(Breathe)", "[Fast Flow]"):
            raw = raw.replace(tag, "")
        cleaned = "".join(c for c in raw.strip() if c.strip() and c not in "，。？！、；：""''《》【】…—～·")
        return len(cleaned)

    def _enforce_on_sections(sections: Any) -> None:
        if not isinstance(sections, list):
            return
        for section in sections:
            if not isinstance(section, dict):
                continue
            tag = str(section.get("tag", "")).strip()
            keys = section_key_map.get(tag)
            if keys is None:
                continue
            min_key, max_key = keys
            line_max = prosody_contract.get(max_key)
            if line_max is None:
                continue
            line_min = prosody_contract.get(min_key, max(1, int(line_max) - 3))
            try:
                line_min_i = int(line_min)
                line_max_i = int(line_max)
            except (TypeError, ValueError):
                continue

            lines = section.get("lines", [])
            if not isinstance(lines, list):
                continue
            lengths = [_bare_len(str((line or {}).get("primary", ""))) for line in lines if isinstance(line, dict)]
            if not lengths:
                continue

            tags = [str(x).strip() for x in section.get("voice_tags_inline", []) if str(x).strip()]
            if any(x <= line_min_i for x in lengths):
                if "(Pause)" not in tags and "(Breathe)" not in tags:
                    tags.append("(Pause)")
            if any(x >= line_max_i for x in lengths):
                if "[Fast Flow]" not in tags:
                    tags.append("[Fast Flow]")
            section["voice_tags_inline"] = tags

    _enforce_on_sections(payload.get("lyrics_by_section"))
    variants = payload.get("variants", [])
    if isinstance(variants, list):
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            _enforce_on_sections(variant.get("lyrics_by_section"))


def generate_lyric_payload(
    user_input: UserInput,
    *,
    repo_root: Path,
    model: str = "claude-opus-4-1-20250805",
    targeted_revise_prompt: str | None = None,
    temperature_override: float | None = None,
) -> tuple[LyricPayload, dict[str, Any]]:
    env_map = _read_env_map(repo_root)
    config = _resolve_provider_config(env_map, default_model=model)
    retrieval = retrieve_few_shot_examples(
        user_input,
        repo_root=repo_root,
        top_k=3,
        return_metadata=True,
    )
    if isinstance(retrieval, dict):
        few_shot_examples = [
            ex for ex in retrieval.get("samples", []) if isinstance(ex, dict)
        ]
        profile_vote = str(retrieval.get("profile_vote", ""))
        vote_confidence = float(retrieval.get("vote_confidence", 0.0) or 0.0)
        profile_vote_counts = retrieval.get("profile_vote_counts", {}) if isinstance(retrieval.get("profile_vote_counts", {}), dict) else {}
        corpus_balance = retrieval.get("corpus_balance", {}) if isinstance(retrieval.get("corpus_balance", {}), dict) else {}
        corpus_monoculture_risk = bool(retrieval.get("corpus_monoculture_risk", False))
        fallback_level = str(retrieval.get("fallback_level", "none") or "none")
    else:
        few_shot_examples = retrieval
        profile_vote = ""
        vote_confidence = 0.0
        profile_vote_counts = {}
        corpus_balance = {}
        corpus_monoculture_risk = False
        fallback_level = "none"

    active_profile, profile_source, profile_vote_confidence = resolve_active_profile(
        user_input,
        repo_root=repo_root,
        retrieval_vote=profile_vote,
        vote_confidence=vote_confidence,
    )
    skill_text = _load_skill_text(repo_root, active_profile=active_profile)

    prompt = {
        "task": "Generate lyric_payload JSON only with 3 variants and choose best one.",
        "input": user_input.model_dump(),
        "requirements": {
            "min_sections": 3,
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
        "few_shot_system_instruction": (
            "以下示例展示的是 craft 方法，不是模板。"
            "你需要学习它们的具象化手法、视角切换、留白节奏，"
            "严禁复写超过 4 字连续片段，严禁照抄结构。"
        ),
        "few_shot_examples": few_shot_examples,
        "active_profile": active_profile,
        "profile_source": profile_source,
    }
    if targeted_revise_prompt:
        prompt["targeted_revise_prompt"] = targeted_revise_prompt
    generation_temperature = 0.6 if targeted_revise_prompt else 0.8
    if isinstance(temperature_override, (int, float)):
        generation_temperature = float(temperature_override)

    parser_repair_call = False
    parser_repair_reason = ""

    if config.provider == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=config.api_key)
        message = client.messages.create(
            model=config.model,
            max_tokens=4096,
            temperature=generation_temperature,
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
            temperature=generation_temperature,
        )

    payload_dict = _extract_json_block(raw_text)
    # Unwrap if model enveloped the payload under a single key (e.g. {"lyric_payload": {...}})
    _LYRIC_KEYS = {"lyrics_by_section", "variants", "distillation", "structure"}
    if not any(k in payload_dict for k in _LYRIC_KEYS):
        for _v in payload_dict.values():
            if isinstance(_v, dict) and any(k in _v for k in _LYRIC_KEYS):
                payload_dict = _v
                break

    shape_validation_report = _validate_payload_shape(payload_dict)
    normalized_payload, normalize_meta = _normalize_payload_dict_with_meta(
        payload_dict,
        user_input=user_input,
        model_used=config.model,
        repo_root=repo_root,
        active_profile=active_profile,
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

    if _needs_parser_repair(normalized_payload):
        parser_repair_call = True
        parser_repair_reason = "R00_empty_after_normalize"
        repair_prompt = dict(prompt)
        repair_prompt["parser_repair_instruction"] = (
            "Return strict JSON object only (no markdown). Ensure lyrics_by_section uses non-empty variant-keyed sections (a/b/c), "
            "and chosen_variant_id points to a non-empty variant."
        )
        if config.provider == "anthropic":
            from anthropic import Anthropic

            client = Anthropic(api_key=config.api_key)
            message = client.messages.create(
                model=config.model,
                max_tokens=4096,
                temperature=generation_temperature,
                system=skill_text,
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(repair_prompt, ensure_ascii=False),
                    }
                ],
            )
            text_blocks = [
                block.text for block in message.content if getattr(block, "type", "") == "text"
            ]
            repaired_raw_text = "\n".join(text_blocks)
            repair_usage = {
                "input_tokens": int(getattr(message.usage, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(message.usage, "output_tokens", 0) or 0),
                "total_tokens": int(
                    (getattr(message.usage, "input_tokens", 0) or 0)
                    + (getattr(message.usage, "output_tokens", 0) or 0)
                ),
            }
        else:
            repaired_raw_text, repair_usage = _call_openai_compatible(
                config=config,
                skill_text=skill_text,
                prompt=repair_prompt,
                temperature=generation_temperature,
                force_json_object=True,
            )

        usage = {
            "input_tokens": int(usage.get("input_tokens", 0)) + int(repair_usage.get("input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)) + int(repair_usage.get("output_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)) + int(repair_usage.get("total_tokens", 0)),
        }

        payload_dict = _extract_json_block(repaired_raw_text)
        if not any(k in payload_dict for k in _LYRIC_KEYS):
            for _v in payload_dict.values():
                if isinstance(_v, dict) and any(k in _v for k in _LYRIC_KEYS):
                    payload_dict = _v
                    break

        shape_validation_report = _validate_payload_shape(payload_dict)
        normalized_payload, normalize_meta = _normalize_payload_dict_with_meta(
            payload_dict,
            user_input=user_input,
            model_used=config.model,
            repo_root=repo_root,
            active_profile=active_profile,
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
        raw_text = repaired_raw_text

    payload = LyricPayload.model_validate(normalized_payload)

    prosody_contract = _load_profile_prosody(repo_root, active_profile)
    trace = {
        "provider": config.provider,
        "model_used": config.model,
        "usage": usage,
        "llm_calls": 1,
        "few_shot_source_ids": [x["source_id"] for x in few_shot_examples],
        "few_shot_examples": [
            {
                "source_id": str(x.get("source_id", "")),
                "content_preview": str(x.get("content", "")).strip()[:30],
                "learn_point": str(x.get("learn_point", "")).strip(),
                "do_not_copy": str(x.get("do_not_copy", "")).strip(),
            }
            for x in few_shot_examples
        ],
        "retrieval_profile_vote": profile_vote,
        "retrieval_vote_confidence": vote_confidence,
        "retrieval_profile_vote_counts": profile_vote_counts,
        "fallback_level": fallback_level,
        "fallback_reason": str(retrieval.get("fallback_reason", "none") if isinstance(retrieval, dict) else "none"),
        "active_profile": active_profile,
        "profile_source": profile_source,
        "profile_vote_confidence": profile_vote_confidence,
        "corpus_balance": corpus_balance,
        "corpus_monoculture_risk": corpus_monoculture_risk,
        "audio_feature_vote": str(retrieval.get("audio_feature_vote", "") if isinstance(retrieval, dict) else ""),
        "audio_feature_vote_reason": str(retrieval.get("audio_feature_vote_reason", "") if isinstance(retrieval, dict) else ""),
        "audio_feature_vote_confidence": float(retrieval.get("audio_feature_vote_confidence", 0.0) if isinstance(retrieval, dict) else 0.0),
        "raw_model_output": raw_text,
        "normalized_payload": normalized_payload,
        "normalize_branch": normalize_meta.get("normalize_branch", "list_passthrough"),
        "chosen_variant_id_resolved": normalize_meta.get("chosen_variant_id_resolved"),
        "chosen_variant_id_source": normalize_meta.get("chosen_variant_id_source", "raw"),
        "parser_repair_call": parser_repair_call,
        "repair_reason": parser_repair_reason,
        "shape_validation_report": shape_validation_report,
        "stage": "revise" if targeted_revise_prompt else "initial",
        "style_vocab_metrics": normalized_payload.get("style_vocab_metrics", {}),
        "prosody_contract": prosody_contract,
        "prosody_matrix_aligned": False,
        "temperature": generation_temperature,
    }
    return payload, trace
