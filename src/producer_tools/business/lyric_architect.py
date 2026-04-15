"""Skeleton for lyric_architect tool."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

from ..contracts import ToolPayload, ToolResult

TOOL_NAME = "lyric_architect"

REQUIRED_SECTION_SPECS: list[dict[str, object]] = [
    {
        "tag": "Verse 1",
        "source_label": "verse",
        "emotional_arc": "reflective",
        "word_count": 60,
    },
    {
        "tag": "Pre-Chorus",
        "source_label": "pre_chorus",
        "emotional_arc": "building",
        "word_count": 30,
    },
    {
        "tag": "Chorus",
        "source_label": "chorus",
        "emotional_arc": "emotional_peak",
        "word_count": 80,
    },
    {
        "tag": "Verse 2",
        "source_label": "verse",
        "emotional_arc": "narrative",
        "word_count": 60,
    },
    {
        "tag": "Bridge",
        "source_label": "bridge",
        "emotional_arc": "transitional",
        "word_count": 40,
    },
    {
        "tag": "Final Chorus",
        "source_label": "chorus",
        "emotional_arc": "resolution",
        "word_count": 80,
    },
]


def _emotional_arc_from_energy(energy: float) -> str:
    if energy > 0.7:
        return "emotional_peak"
    if energy > 0.5:
        return "building"
    if energy > 0.3:
        return "reflective"
    return "introductory"


def _energy_for_section(
    source_label: str,
    structure: list[dict[str, object]],
    section_index: int,
) -> float:
    # Prefer positional mapping first (retains rough reference dynamics)
    if section_index < len(structure):
        seg = structure[section_index]
        if isinstance(seg, dict):
            val = seg.get("energy", 0.5)
            if isinstance(val, (int, float)):
                return float(val)

    # Fallback to first matching source label
    for seg in structure:
        if not isinstance(seg, dict):
            continue
        label = str(seg.get("label", "")).strip().lower()
        if label == source_label:
            val = seg.get("energy", 0.5)
            if isinstance(val, (int, float)):
                return float(val)

    return 0.5


def plan_structure_grid(
    intent: str,
    structure: list[dict[str, object]],
) -> dict[str, object]:
    """Generate structure grid from user intent and reference structure.

    PRD 5.4.2 Step 1: Structure-grid planner.
    Maps reference structure to lyric sections with emotional arcs,
    keywords, and word counts.

    Args:
        intent: User's intent description (e.g., "失恋 R&B 碎碎念").
        structure: Reference DNA structure (list of segment dicts).

    Returns:
        dict with ok, grid{sections[{tag, emotional_arc, keywords, word_count}]}
    """
    _ = intent

    sections: list[dict[str, object]] = []
    for i, spec in enumerate(REQUIRED_SECTION_SPECS):
        src_label = str(spec.get("source_label", "verse"))
        energy = _energy_for_section(src_label, structure, i)
        default_arc = str(spec.get("emotional_arc", "reflective"))
        inferred_arc = _emotional_arc_from_energy(energy)
        word_count_raw = spec.get("word_count", 50)
        word_count = (
            int(word_count_raw) if isinstance(word_count_raw, (int, float)) else 50
        )

        # Keep PRD-specific semantic anchors for special sections
        if str(spec.get("tag", "")) in {"Bridge", "Final Chorus"}:
            emotional_arc = default_arc
        else:
            emotional_arc = inferred_arc

        sections.append(
            {
                "tag": str(spec.get("tag", f"Section {i + 1}")),
                "emotional_arc": emotional_arc,
                "keywords": [],
                "word_count": word_count,
            }
        )

    return {
        "ok": True,
        "grid": {"sections": sections},
    }


def _load_corpus_lines(
    corpus_sources: list[str],
    max_lines: int = 48,
) -> list[str]:
    """Load real corpus lines from configured local sources.

    Supported formats:
    - .txt (one line per lyric sentence)
    - .json (list[str] or {"lines": list[str]})
    - .jsonl ({"line": "..."} per line)
    """
    collected: list[str] = []

    for raw_path in corpus_sources:
        if len(collected) >= max_lines:
            break
        path = Path(raw_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            continue

        suffix = path.suffix.lower()
        try:
            if suffix == ".txt":
                for line in path.read_text(encoding="utf-8").splitlines():
                    text = line.strip()
                    if text:
                        collected.append(text)
                        if len(collected) >= max_lines:
                            break
            elif suffix == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, str) and item.strip():
                            collected.append(item.strip())
                            if len(collected) >= max_lines:
                                break
                elif isinstance(payload, dict):
                    lines = payload.get("lines", [])
                    if isinstance(lines, list):
                        for item in lines:
                            if isinstance(item, str) and item.strip():
                                collected.append(item.strip())
                                if len(collected) >= max_lines:
                                    break
                    sections = payload.get("sections", [])
                    if isinstance(sections, list):
                        for section in sections:
                            if len(collected) >= max_lines:
                                break
                            if not isinstance(section, dict):
                                continue
                            section_lines = section.get("lines", [])
                            if not isinstance(section_lines, list):
                                continue
                            for row in section_lines:
                                if len(collected) >= max_lines:
                                    break
                                if isinstance(row, str) and row.strip():
                                    collected.append(row.strip())
                                    continue
                                if isinstance(row, dict):
                                    text = row.get("text", "")
                                    if isinstance(text, str) and text.strip():
                                        collected.append(text.strip())
            elif suffix == ".jsonl":
                for row in path.read_text(encoding="utf-8").splitlines():
                    row_text = row.strip()
                    if not row_text:
                        continue
                    try:
                        parsed = json.loads(row_text)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, dict):
                        item = parsed.get("line", "")
                        if isinstance(item, str) and item.strip():
                            collected.append(item.strip())
                            if len(collected) >= max_lines:
                                break
        except OSError:
            continue
        except json.JSONDecodeError:
            continue

    return collected


def _build_template_binding(
    payload: ToolPayload,
    structure: list[dict[str, object]],
) -> dict[str, object]:
    """Build template binding from explicit template or reference structure."""
    template_val = payload.get("structure_template")
    if isinstance(template_val, dict):
        return template_val

    template_path_val = payload.get("structure_template_path")
    if isinstance(template_path_val, (str, Path)):
        template_path = Path(template_path_val).expanduser().resolve()
        if template_path.exists() and template_path.is_file():
            try:
                loaded = json.loads(template_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    return loaded
            except (OSError, json.JSONDecodeError):
                pass

    # Fallback to deterministic structure-derived template binding.
    planned = plan_structure_grid("template-bootstrap", structure)
    grid_raw = planned.get("grid", {}) if isinstance(planned, dict) else {}
    grid = grid_raw if isinstance(grid_raw, dict) else {}
    sections_raw = grid.get("sections", [])
    sections = sections_raw if isinstance(sections_raw, list) else []

    line_lengths: list[int] = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        wc_raw = sec.get("word_count", 40)
        wc = int(wc_raw) if isinstance(wc_raw, (int, float)) else 40
        line_lengths.append(max(6, min(16, wc // 4)))

    if not line_lengths:
        line_lengths = [8, 10, 12]

    return {
        "template_id": "reference_dna_derived_v1",
        "sections": sections,
        "line_length_distribution": line_lengths,
        "stress_anchor_policy": "preserve_section_energy",
    }


def generate_draft(
    grid: dict[str, object],
    intent: str,
    use_llm: bool = True,
    llm_adapter: object | None = None,
    forbidden_terms: set[str] | None = None,
    reference_constraints: dict[str, object] | None = None,
    template_binding: dict[str, object] | None = None,
    corpus_context: list[str] | None = None,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
) -> dict[str, object]:
    """Generate draft lyrics from structure grid.

    PRD 5.4.2 Step 2: Draft Writer.
    Generates lyrics per section with template-locked skeleton guidance.

    Args:
        grid: Structure grid from plan_structure_grid.
        intent: User's intent description.
        template_binding: Locked structure template metadata.
        corpus_context: Real corpus excerpts for lexical/style grounding.

    Returns:
        dict with ok, draft{sections[{tag, lines}]}
    """
    sections_raw = grid.get("sections") if isinstance(grid, dict) else None
    if not isinstance(sections_raw, list):
        return {
            "ok": False,
            "error": "invalid_grid",
            "draft": None,
        }

    template_meta = template_binding if isinstance(template_binding, dict) else {}
    corpus_lines = corpus_context if isinstance(corpus_context, list) else []

    adapter_callable = llm_adapter if callable(llm_adapter) else None
    if use_llm and adapter_callable is None:
        # Best effort OpenAI adapter from environment
        adapter_callable = _build_openai_adapter(
            api_key=llm_api_key,
            base_url=llm_base_url,
            model_name=llm_model,
        )
    if use_llm and adapter_callable is None:
        return {
            "ok": False,
            "error": "llm_not_configured",
            "draft": None,
        }

    # Generate draft sections
    draft_sections: list[dict[str, object]] = []

    for section in sections_raw:
        if not isinstance(section, dict):
            continue

        tag = str(section.get("tag", "Section"))
        word_count = int(section.get("word_count", 50))
        emotional_arc = str(section.get("emotional_arc", "neutral"))

        llm_result = _generate_section_lines_with_llm(
            adapter_callable=adapter_callable,
            tag=tag,
            word_count=word_count,
            emotional_arc=emotional_arc,
            intent=intent,
            template_meta=template_meta,
            corpus_lines=corpus_lines,
            forbidden_terms=forbidden_terms or set(),
            reference_constraints=reference_constraints or {},
        )
        if not llm_result.get("ok"):
            return {
                "ok": False,
                "error": "llm_generation_failed",
                "error_detail": str(llm_result.get("error", "")),
                "draft": None,
            }
        lines_val = llm_result.get("lines", [])
        lines: list[str] = (
            [str(x) for x in lines_val] if isinstance(lines_val, list) else []
        )

        draft_sections.append(
            {
                "tag": tag,
                "lines": lines,
            }
        )

    return {
        "ok": True,
        "draft": {"sections": draft_sections},
    }


def _build_openai_adapter(
    api_key: str | None = None,
    base_url: str | None = None,
    model_name: str | None = None,
) -> object | None:
    """Build OpenAI adapter from env when available."""
    resolved_api_key = (
        api_key.strip() if isinstance(api_key, str) and api_key.strip() else ""
    )
    if not resolved_api_key:
        resolved_api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not resolved_api_key:
        return None

    resolved_model = (
        model_name.strip() if isinstance(model_name, str) and model_name.strip() else ""
    )
    if not resolved_model:
        resolved_model = os.getenv("OPENAI_MODEL", "").strip()
    if not resolved_model:
        resolved_model = "gpt-4o-mini"

    resolved_base_url = (
        base_url.strip() if isinstance(base_url, str) and base_url.strip() else ""
    )
    if not resolved_base_url:
        resolved_base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if not resolved_base_url:
        resolved_base_url = os.getenv("OPENAI_API_BASE", "").strip()

    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except Exception:
        return None

    if resolved_base_url:
        client = OpenAI(api_key=resolved_api_key, base_url=resolved_base_url)
    else:
        client = OpenAI(api_key=resolved_api_key)

    def _adapter(prompt: dict[str, object]) -> dict[str, object]:
        prompt_text = str(prompt.get("prompt", ""))
        if not prompt_text:
            return {"lines": []}

        import json as json_mod

        # Primary path: Responses API
        responses_api = getattr(client, "responses", None)
        create_fn = getattr(responses_api, "create", None)
        if callable(create_fn):
            try:
                response = create_fn(
                    model=resolved_model,
                    input=prompt_text,
                    text={"format": {"type": "json_object"}},
                )
                text = getattr(response, "output_text", "")
                if isinstance(text, str) and text:
                    parsed: Any = json_mod.loads(text)
                    if isinstance(parsed, dict):
                        lines = parsed.get("lines", [])
                        if isinstance(lines, list):
                            return {
                                "lines": [
                                    str(x) for x in lines if isinstance(x, str) and x
                                ]
                            }
            except Exception:
                pass

        # Fallback path: Chat Completions API
        chat_api = getattr(client, "chat", None)
        completions_api = getattr(chat_api, "completions", None)
        chat_create_fn = getattr(completions_api, "create", None)
        if callable(chat_create_fn):
            resp = chat_create_fn(
                model=resolved_model,
                messages=[
                    {
                        "role": "system",
                        "content": 'Return JSON only: {"lines": ["..."]}',
                    },
                    {"role": "user", "content": prompt_text},
                ],
                response_format={"type": "json_object"},
            )
            choices = getattr(resp, "choices", [])
            if isinstance(choices, list) and choices:
                msg = getattr(choices[0], "message", None)
                content = getattr(msg, "content", "")
                if isinstance(content, str) and content:
                    parsed2: Any = json_mod.loads(content)
                    if isinstance(parsed2, dict):
                        lines2 = parsed2.get("lines", [])
                        if isinstance(lines2, list):
                            return {
                                "lines": [
                                    str(x) for x in lines2 if isinstance(x, str) and x
                                ]
                            }

        return {"lines": []}

    return _adapter


def _build_reference_hard_constraints(
    reference_dna: dict[str, object],
) -> dict[str, object]:
    """Build hard constraints from reference song features.

    Hard constraints are explicitly fed to LLM prompt:
    - sentence_length_distribution
    - pause_rhythm
    - chorus_hook
    """
    structure_raw = reference_dna.get("structure", [])
    structure = structure_raw if isinstance(structure_raw, list) else []
    energy_curve_raw = reference_dna.get("energy_curve", [])
    energy_curve = energy_curve_raw if isinstance(energy_curve_raw, list) else []

    # sentence length distribution (heuristic from section energy profile)
    sentence_lengths: list[int] = []
    for i, seg in enumerate(structure):
        energy = 0.5
        if isinstance(seg, dict):
            val = seg.get("energy", 0.5)
            if isinstance(val, (int, float)):
                energy = float(val)
        if energy >= 0.75:
            sentence_lengths.append(13)
        elif energy >= 0.55:
            sentence_lengths.append(11)
        elif energy >= 0.35:
            sentence_lengths.append(9)
        else:
            sentence_lengths.append(8)
        if i >= 7:
            break
    if not sentence_lengths:
        sentence_lengths = [8, 10, 12, 10]

    # pause rhythm from local energy deltas
    pauses: list[str] = []
    prev = None
    for point in energy_curve[:8]:
        e = None
        if isinstance(point, dict):
            val = point.get("energy")
            if isinstance(val, (int, float)):
                e = float(val)
        elif isinstance(point, (int, float)):
            e = float(point)
        if e is None:
            continue
        if prev is None:
            prev = e
            continue
        diff = e - prev
        if diff > 0.12:
            pauses.append("短停-推进")
        elif diff < -0.12:
            pauses.append("长停-回落")
        else:
            pauses.append("匀速连读")
        prev = e
    if not pauses:
        pauses = ["匀速连读", "短停-推进", "长停-回落"]

    # chorus hook from key/tempo and high-energy motif
    key = str(reference_dna.get("key", "C"))
    tempo_raw = reference_dna.get("tempo", 100.0)
    tempo = float(tempo_raw) if isinstance(tempo_raw, (int, float)) else 100.0
    hook = f"{key}@{int(tempo)}bpm_高能段重复意象2次"

    return {
        "sentence_length_distribution": sentence_lengths,
        "pause_rhythm": pauses,
        "chorus_hook": hook,
    }


def _generate_section_lines_with_llm(
    adapter_callable: object,
    tag: str,
    word_count: int,
    emotional_arc: str,
    intent: str,
    template_meta: dict[str, object],
    corpus_lines: list[str],
    forbidden_terms: set[str],
    reference_constraints: dict[str, object],
) -> dict[str, object]:
    """Generate section lines via adapter callable."""
    if not callable(adapter_callable):
        return {"ok": False, "lines": []}

    sentence_lengths = reference_constraints.get("sentence_length_distribution", [])
    pause_rhythm = reference_constraints.get("pause_rhythm", [])
    chorus_hook = str(reference_constraints.get("chorus_hook", "")).strip()
    chorus_required = "chorus" in tag.strip().lower()

    forbidden_terms_sorted = sorted(
        x for x in forbidden_terms if isinstance(x, str) and x
    )
    lexical_ban = "、".join(forbidden_terms_sorted)
    template_id = str(template_meta.get("template_id", "reference_dna_derived_v1"))
    template_sections = template_meta.get("sections", [])
    template_line_lengths = template_meta.get("line_length_distribution", [])
    corpus_preview = " | ".join(
        x for x in (str(line).strip() for line in corpus_lines[:5]) if x
    )

    prompt = {
        "prompt": (
            "你是中文流行歌词写作助手。"
            "请按给定段落写2-6行歌词，避免套话和重复，保证因果连贯与可唱性。"
            "语气现代、可带轻微古风，情绪是失恋但豁达。\n"
            f"段落: {tag}\n"
            f"情绪弧线: {emotional_arc}\n"
            f"目标字数(近似): {word_count}\n"
            f"用户意图: {intent}\n"
            f"模板ID(唯一事实源): {template_id}\n"
            f"模板章节骨架(只读): {template_sections}\n"
            f"模板句长分布(只读): {template_line_lengths}\n"
            f"语料片段参考(只读): {corpus_preview}\n"
            f"禁用词库-词级硬约束: {lexical_ban}\n"
            "禁用句式-句式级硬约束: 你像X我像Y、如果...就好了、把抽象词当主语、连续两行同模板。\n"
            "禁用语义-语义级硬约束: 不允许空泛鸡汤、命运论、无场景抒情、无因果跳跃。\n"
            f"句长分布硬约束: {sentence_lengths}\n"
            f"停连节奏硬约束: {pause_rhythm}\n"
            f"副歌钩子: {chorus_hook}\n"
            f"本段是否必须复现副歌钩子: {'是' if chorus_required else '否'}\n"
            "必须满足:\n"
            "1) 每行长度贴合 sentence_length_distribution；\n"
            "2) 行内停连遵循 pause_rhythm；\n"
            "3) 若本段是 Chorus/Final Chorus，则必须复现 chorus_hook（允许轻微变体但核心意象不变）；\n"
            "4) 禁止出现禁用词，禁止逻辑跳跃和乱比喻。\n"
            "5) 所有行必须是具体场景，不得只写抽象情绪词。\n"
            "6) 不允许新增/删除模板章节，不允许改写模板骨架与句长规则。\n"
            '输出JSON: {"lines": ["...", "..."]}'
        )
    }

    try:
        out = adapter_callable(prompt)
    except Exception as exc:
        return {"ok": False, "lines": [], "error": str(exc)}

    if isinstance(out, dict):
        lines = out.get("lines", [])
        if isinstance(lines, list):
            cleaned = [
                str(x).strip() for x in lines if isinstance(x, str) and str(x).strip()
            ]
            if cleaned:
                return {"ok": True, "lines": cleaned}

    if isinstance(out, list):
        cleaned = [str(x).strip() for x in out if isinstance(x, str) and str(x).strip()]
        if cleaned:
            return {"ok": True, "lines": cleaned}

    return {"ok": False, "lines": [], "error": "empty_or_invalid_llm_output"}


# Vowel classification for Chinese
OPEN_VOWELS = {"a", "o", "e", "ai", "ao", "an", "ang", "en", "eng", "ou"}
CLOSED_VOWELS = {"i", "u", "ü", "in", "ing", "un", "ong", "iu", "ui"}


def _get_final_vowel(char: str) -> str:
    """Get the final (韵母) of a Chinese character using pypinyin."""
    try:
        from pypinyin import pinyin, Style

        py = pinyin(char, style=Style.FINALS_TONE3)
        if py and py[0]:
            final = py[0][0]
            # Remove tone number
            return "".join(c for c in final if c.isalpha())
    except ImportError:
        pass
    except Exception:
        pass
    return ""


def check_vowel_openness(
    lyrics: list[str],
    peak_positions: list[int],
) -> dict[str, object]:
    """Check vowel openness at peak note positions.

    PRD 5.4.2 Step 3: Vowel Openness Check.
    Peak notes (high MIDI) must use open vowels for singability.

    Args:
        lyrics: List of lyric lines.
        peak_positions: Character indices (flattened) at peak notes.

    Returns:
        dict with ok, violations[], pass (bool).
    """
    if not lyrics:
        return {
            "ok": True,
            "violations": [],
            "pass": True,
        }

    # Flatten lyrics to character list with position tracking
    char_positions: list[tuple[int, int, str]] = []  # (line_idx, char_idx, char)
    for line_idx, line in enumerate(lyrics):
        for char_idx, char in enumerate(line):
            char_positions.append((line_idx, char_idx, char))

    violations: list[dict[str, object]] = []

    for peak_idx in peak_positions:
        if peak_idx < 0 or peak_idx >= len(char_positions):
            continue

        line_idx, char_idx, char = char_positions[peak_idx]
        vowel = _get_final_vowel(char)

        # Check if vowel is closed
        if vowel in CLOSED_VOWELS:
            violations.append(
                {
                    "line": line_idx,
                    "char": char_idx,
                    "character": char,
                    "vowel": vowel,
                    "severity": "critical",
                }
            )
        elif vowel not in OPEN_VOWELS:
            # Unknown vowel - mark as warning
            violations.append(
                {
                    "line": line_idx,
                    "char": char_idx,
                    "character": char,
                    "vowel": vowel,
                    "severity": "warning",
                }
            )

    return {
        "ok": True,
        "violations": violations,
        "pass": len([v for v in violations if v.get("severity") == "critical"]) == 0,
    }


# === P07.04: Tone Collision Interceptor ===


def _get_tone(char: str) -> int:
    """Get the tone number (1-4) of a Chinese character using pypinyin."""
    try:
        from pypinyin import pinyin, Style

        py = pinyin(char, style=Style.TONE3)
        if py and py[0]:
            tone_str = py[0][0]
            # Extract tone number from end
            for c in reversed(tone_str):
                if c.isdigit():
                    return int(c)
    except ImportError:
        pass
    except Exception:
        pass
    return 1  # Default to 1st tone


def check_tone_collision(
    lyrics: list[str],
    long_note_positions: list[int],
) -> dict[str, object]:
    """Check tone collision at long note positions.

    PRD 5.4.2 Step 4: Tone Collision Check.
    Long note characters should use flat tones (1st/2nd tone).
    3rd/4th tone = occlusion risk.

    Args:
        lyrics: List of lyric lines.
        long_note_positions: Character indices at long note positions.

    Returns:
        dict with ok, violations[], risk_percentage, pass.
    """
    if not lyrics:
        return {
            "ok": True,
            "violations": [],
            "risk_percentage": 0.0,
            "pass": True,
        }

    # Flatten lyrics to character list with position tracking
    char_positions: list[tuple[int, int, str]] = []
    for line_idx, line in enumerate(lyrics):
        for char_idx, char in enumerate(line):
            char_positions.append((line_idx, char_idx, char))

    violations: list[dict[str, object]] = []

    for pos_idx in long_note_positions:
        if pos_idx < 0 or pos_idx >= len(char_positions):
            continue

        line_idx, char_idx, char = char_positions[pos_idx]
        tone = _get_tone(char)

        # 3rd (3) and 4th (4) tones are risky on long notes
        if tone in (3, 4):
            violations.append(
                {
                    "line": line_idx,
                    "char": char_idx,
                    "character": char,
                    "tone": tone,
                    "severity": "medium" if tone == 3 else "high",
                }
            )

    total_long_notes = len(
        [p for p in long_note_positions if 0 <= p < len(char_positions)]
    )
    risk_pct = (
        (len(violations) / total_long_notes * 100.0) if total_long_notes > 0 else 0.0
    )

    return {
        "ok": True,
        "violations": violations,
        "risk_percentage": round(risk_pct, 2),
        "pass": risk_pct <= 15.0,
    }


# === P07.05: Anti-Cliché Interceptor ===

# Cliche blacklist based on PRD examples
CLICHE_BLACKLIST = {
    "星辰大海",
    "孤独灵魂",
    "孤独的黑夜",
    "追寻梦想",
    "时光沙漏",
    "梦想",
    "爱",
    "心碎",
}

# Anti-lexicon (user negative lexicon + product defaults)
DEFAULT_ANTI_LEXICON = {
    "霓虹",
    "破碎感",
    "宿命感",
    "支离破碎",
    "迷失自我",
}


def check_anti_cliche(
    lyrics: list[str],
    max_density_pct: float = 5.0,
    blacklist: set[str] | None = None,
) -> dict[str, object]:
    """Check for cliche phrases in lyrics.

    PRD 5.4.2 Step 5: Anti-Cliché Engine.
    jieba segmentation → count hits in blacklist.
    Density > max_density_pct (default 5%) → trigger rewrite.

    Args:
        lyrics: List of lyric lines.
        max_density_pct: Threshold percentage (default 5.0).

    Returns:
        dict with ok, violations[], density_pct, pass.
    """
    if not lyrics:
        return {
            "ok": True,
            "violations": [],
            "density_pct": 0.0,
            "pass": True,
        }

    # Combine all lines and segment
    full_text = "".join(lyrics)
    total_chars = len(full_text)

    if total_chars == 0:
        return {
            "ok": True,
            "violations": [],
            "density_pct": 0.0,
            "pass": True,
        }

    # Try jieba segmentation
    try:
        import jieba

        _ = list(jieba.cut(full_text))  # noqa: F841
    except ImportError:
        # Fallback: character-by-character check
        _ = list(full_text)  # noqa: F841
    except Exception:
        _ = list(full_text)  # noqa: F841

    violations: list[dict[str, object]] = []
    cliche_count = 0

    effective_blacklist = blacklist if isinstance(blacklist, set) else CLICHE_BLACKLIST

    # Check for cliche phrases
    for cliche in effective_blacklist:
        start = 0
        while True:
            pos = full_text.find(cliche, start)
            if pos == -1:
                break
            violations.append(
                {
                    "line": 0,
                    "position": pos,
                    "phrase": cliche,
                    "severity": "medium",
                }
            )
            cliche_count += 1
            start = pos + 1

    density_pct = (cliche_count / total_chars * 100.0) if total_chars > 0 else 0.0

    return {
        "ok": True,
        "violations": violations,
        "density_pct": round(density_pct, 2),
        "pass": density_pct <= max_density_pct,
    }


def check_anti_lexicon(
    lyrics: list[str],
    forbidden_terms: set[str],
) -> dict[str, object]:
    """Block disallowed lexicon regardless of cliche density."""
    if not lyrics:
        return {"ok": True, "hits": [], "pass": True}

    full_text = "\n".join(lyrics)
    hits: list[str] = []
    for term in forbidden_terms:
        if term and term in full_text:
            hits.append(term)

    return {
        "ok": True,
        "hits": sorted(set(hits)),
        "pass": len(hits) == 0,
    }


def run(payload: ToolPayload) -> ToolResult:
    """Execute the lyric_architect tool.

    PRD 5.4: Five-step pipeline:
    1. Plan structure grid from intent + reference_dna
    2. Generate draft lyrics
    3. Check vowel openness at peak notes
    4. Check tone collision at long notes
    5. Check anti-cliche density

    Args:
        payload: dict with intent, reference_dna, optional output_path

    Returns:
        dict with ok, lyrics (meta/sections/warnings/stats)
    """
    intent_val = payload.get("intent", "")
    intent = str(intent_val) if isinstance(intent_val, str) else ""
    reference_dna_val = payload.get("reference_dna", {})
    reference_dna: dict[str, object] = (
        reference_dna_val if isinstance(reference_dna_val, dict) else {}
    )
    output_path_raw = payload.get("output_path")
    output_path: str | None = (
        str(output_path_raw) if isinstance(output_path_raw, (str, Path)) else None
    )
    use_llm = bool(payload.get("use_llm", True))
    llm_adapter = payload.get("llm_adapter")
    llm_api_key_raw = payload.get("llm_api_key")
    llm_base_url_raw = payload.get("llm_base_url")
    llm_model_raw = payload.get("llm_model")
    llm_api_key = str(llm_api_key_raw) if isinstance(llm_api_key_raw, str) else None
    llm_base_url = str(llm_base_url_raw) if isinstance(llm_base_url_raw, str) else None
    llm_model = str(llm_model_raw) if isinstance(llm_model_raw, str) else None
    require_real_corpus = bool(payload.get("require_real_corpus", False))

    # LLM-only invariant: no offline fallback mode.
    if not use_llm:
        return {
            "ok": False,
            "error": "offline_lyrics_disabled",
            "lyrics": None,
        }

    # Step 1: Plan structure grid
    structure_raw = (
        reference_dna.get("structure", []) if isinstance(reference_dna, dict) else []
    )
    structure: list[dict[str, object]] = (
        structure_raw if isinstance(structure_raw, list) else []
    )
    grid_result = plan_structure_grid(intent, structure)
    if not grid_result.get("ok"):
        return {"ok": False, "error": "grid_planning_failed", "lyrics": None}

    # Step 2: Generate draft (with bounded rewrite loop)
    template_binding = _build_template_binding(payload, structure)
    corpus_sources_raw = payload.get("corpus_sources", [])
    corpus_sources: list[str] = []
    if isinstance(corpus_sources_raw, list):
        for item in corpus_sources_raw:
            if isinstance(item, (str, Path)):
                corpus_sources.append(str(item))

    corpus_registry_path_raw = payload.get("corpus_registry_path")
    if isinstance(corpus_registry_path_raw, (str, Path)):
        registry_path = Path(corpus_registry_path_raw).expanduser().resolve()
        if registry_path.exists() and registry_path.is_file():
            try:
                registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
                if isinstance(registry_data, dict):
                    sources_val = registry_data.get("sources", [])
                    if isinstance(sources_val, list):
                        for src in sources_val:
                            if isinstance(src, (str, Path)):
                                corpus_sources.append(str(src))
            except (OSError, json.JSONDecodeError):
                pass

    corpus_lines = _load_corpus_lines(corpus_sources)
    if require_real_corpus and not corpus_lines:
        return {
            "ok": False,
            "error": "corpus_not_configured",
            "lyrics": None,
        }

    grid_val = grid_result.get("grid", {})
    grid: dict[str, object] = grid_val if isinstance(grid_val, dict) else {}
    max_iter_val = payload.get("max_rewrite_iterations", 3)
    max_rewrite_iterations = (
        int(max_iter_val)
        if isinstance(max_iter_val, (int, float)) and int(max_iter_val) >= 0
        else 3
    )
    current_intent = intent
    draft_sections: list[dict[str, object]] = []
    all_lines: list[str] = []

    # Step 3/4/5 controls
    peak_positions_raw = payload.get("peak_positions", [])
    peak_positions: list[int] = (
        peak_positions_raw
        if isinstance(peak_positions_raw, list)
        and all(isinstance(x, int) for x in peak_positions_raw)
        else []
    )
    long_note_positions_raw = payload.get("long_note_positions", [])
    long_note_positions: list[int] = (
        long_note_positions_raw
        if isinstance(long_note_positions_raw, list)
        and all(isinstance(x, int) for x in long_note_positions_raw)
        else []
    )

    vowel_result: dict[str, object] = {"ok": True, "violations": [], "pass": True}
    tone_result: dict[str, object] = {
        "ok": True,
        "violations": [],
        "risk_percentage": 0.0,
        "pass": True,
    }
    cliche_result: dict[str, object] = {
        "ok": True,
        "violations": [],
        "density_pct": 0.0,
        "pass": True,
    }
    anti_lexicon_result: dict[str, object] = {"ok": True, "hits": [], "pass": True}

    negative_lexicon_raw = payload.get("negative_lexicon", [])
    negative_lexicon: set[str] = set(DEFAULT_ANTI_LEXICON)
    if isinstance(negative_lexicon_raw, list):
        for item in negative_lexicon_raw:
            if isinstance(item, str) and item.strip():
                negative_lexicon.add(item.strip())

    reference_constraints = _build_reference_hard_constraints(reference_dna)

    draft_iterations = 0
    vowel_fix_count = 0
    cliche_fix_count = 0

    for attempt in range(max_rewrite_iterations + 1):
        draft_iterations += 1

        draft_result = generate_draft(
            grid,
            current_intent,
            use_llm=use_llm,
            llm_adapter=llm_adapter,
            forbidden_terms=negative_lexicon,
            reference_constraints=reference_constraints,
            template_binding=template_binding,
            corpus_context=corpus_lines,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            llm_model=llm_model,
        )
        if not draft_result.get("ok"):
            return {
                "ok": False,
                "error": str(draft_result.get("error", "draft_generation_failed")),
                "error_detail": str(draft_result.get("error_detail", "")),
                "lyrics": None,
            }

        draft_val = draft_result.get("draft", {})
        draft_data = draft_val if isinstance(draft_val, dict) else {}
        draft_sections_raw = draft_data.get("sections", [])
        draft_sections = (
            draft_sections_raw if isinstance(draft_sections_raw, list) else []
        )
        all_lines = []
        for section in draft_sections:
            if not isinstance(section, dict):
                continue
            lines_val = section.get("lines", [])
            if isinstance(lines_val, list):
                all_lines.extend(str(line) for line in lines_val)

        vowel_result = check_vowel_openness(all_lines, peak_positions)
        tone_result = check_tone_collision(all_lines, long_note_positions)
        cliche_result = check_anti_cliche(all_lines)
        anti_lexicon_result = check_anti_lexicon(all_lines, negative_lexicon)

        needs_vowel_fix = (not bool(vowel_result.get("pass", True))) or (
            not bool(tone_result.get("pass", True))
        )
        needs_cliche_fix = not bool(cliche_result.get("pass", True))
        needs_anti_lexicon_fix = not bool(anti_lexicon_result.get("pass", True))

        if not (needs_vowel_fix or needs_cliche_fix or needs_anti_lexicon_fix):
            break
        if attempt >= max_rewrite_iterations:
            break

        if needs_vowel_fix:
            vowel_fix_count += 1
        if needs_cliche_fix:
            cliche_fix_count += 1
        if needs_anti_lexicon_fix:
            cliche_fix_count += 1

        current_intent = (
            intent
            + "\n[重写约束] 保留核心叙事与情绪。"
            + "\n- 避免烂梗与抽象空话，优先具象场景。"
            + "\n- 长音位置尽量使用更顺口字。"
            + "\n- 避免重复句式与重复关键词。"
            + "\n- 禁用词："
            + "、".join(sorted(negative_lexicon))
        )

    # Build warnings list
    warnings: list[dict[str, object]] = []
    vowel_violations = vowel_result.get("violations", [])
    if isinstance(vowel_violations, list):
        for v in vowel_violations:
            if isinstance(v, dict):
                warnings.append(
                    {
                        "line_index": v.get("line", 0),
                        "type": "vowel_openness",
                        "severity": v.get("severity", "medium"),
                        "human": f"'{v.get('character', '')}' (元音{v.get('vowel', '')}) 在高音位置不适合",
                    }
                )
    tone_violations = tone_result.get("violations", [])
    if isinstance(tone_violations, list):
        for v in tone_violations:
            if isinstance(v, dict):
                warnings.append(
                    {
                        "line_index": v.get("line", 0),
                        "type": "tone_collision",
                        "severity": v.get("severity", "medium"),
                        "human": f"'{v.get('character', '')}' (声调{v.get('tone', '')}) 在长音位置咬合",
                    }
                )

    anti_hits = anti_lexicon_result.get("hits", [])
    if isinstance(anti_hits, list) and anti_hits:
        warnings.append(
            {
                "line_index": 0,
                "type": "anti_lexicon",
                "severity": "high",
                "human": f"命中禁用词: {'、'.join(str(x) for x in anti_hits)}",
            }
        )

    # Build sections with line details
    sections: list[dict[str, object]] = []
    for section in draft_sections:
        section_tag = section.get("tag", "Unknown")
        lines_raw = section.get("lines", [])
        section_lines: list[str] = (
            [str(line) for line in lines_raw] if isinstance(lines_raw, list) else []
        )
        section_detail: list[dict[str, object]] = []
        for line_text in section_lines:
            section_detail.append(
                {
                    "text": line_text,
                    "pinyin": "",
                    "final_vowel": "",
                    "openness": "unknown",
                    "tone_pattern": "",
                    "cliche_hits": [],
                }
            )
        sections.append(
            {
                "tag": section_tag,
                "lines": section_detail,
            }
        )

    # Build lyrics output
    lyrics = {
        "meta": {
            "intent": intent,
            "structure_ref": "auto-generated",
            "iterations": {
                "draft": draft_iterations,
                "vowel_fix": vowel_fix_count,
                "cliche_fix": cliche_fix_count,
            },
        },
        "sections": sections,
        "warnings": warnings,
        "stats": {
            "vowel_openness_at_peak": "pass"
            if vowel_result.get("pass", True)
            else "fail",
            "cliche_density_pct": cliche_result.get("density_pct", 0.0),
            "tone_collision_pct": tone_result.get("risk_percentage", 0.0),
        },
    }

    # Optional: write to file
    if output_path:
        import json as json_mod

        output_path_obj = Path(output_path).expanduser().resolve()
        try:
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            _ = output_path_obj.write_text(
                json_mod.dumps(lyrics, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    quality_gate = {
        "pass": bool(vowel_result.get("pass", True))
        and bool(tone_result.get("pass", True))
        and bool(cliche_result.get("pass", True))
        and bool(anti_lexicon_result.get("pass", True)),
        "anti_lexicon_hits": anti_lexicon_result.get("hits", []),
    }

    if not bool(quality_gate.get("pass", False)):
        return {
            "ok": False,
            "error": "lyric_quality_gate_failed",
            "lyrics": lyrics,
            "quality_gate": quality_gate,
            "output_path": str(output_path) if output_path else "",
        }

    return {
        "ok": True,
        "lyrics": lyrics,
        "quality_gate": quality_gate,
        "output_path": str(output_path) if output_path else "",
    }
