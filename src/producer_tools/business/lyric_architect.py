"""Skeleton for lyric_architect tool."""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Any

from ..contracts import ToolPayload, ToolResult

TOOL_NAME = "lyric_architect"
logger = logging.getLogger(__name__)

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
    lyric_beat_budget: dict[str, object] | None = None,
) -> dict[str, object]:
    """Generate structure grid from user intent and reference structure.

    PRD 5.4.2 Step 1: Structure-grid planner.
    Maps reference structure to lyric sections with emotional arcs,
    keywords, and word counts.

    Args:
        intent: User's intent description (e.g., "失恋 R&B 碎碎念").
        structure: Reference DNA structure (list of segment dicts).
        lyric_beat_budget: Optional beat-derived word budget per section.

    Returns:
        dict with ok, grid{sections[{tag, emotional_arc, keywords, word_count}]}
    """
    _ = intent

    budget_sections_raw = (
        lyric_beat_budget.get("sections", [])
        if isinstance(lyric_beat_budget, dict)
        else []
    )
    budget_sections: list[dict[str, object]] = (
        budget_sections_raw if isinstance(budget_sections_raw, list) else []
    )

    def _word_count_from_budget(source_label: str, idx: int, default_wc: int) -> int:
        # Prefer positional mapping (same ordering as structure planner)
        if idx < len(budget_sections):
            item = budget_sections[idx]
            if isinstance(item, dict):
                tw = item.get("target_words")
                if isinstance(tw, (int, float)) and int(tw) > 0:
                    return int(tw)

        # Fallback to first matching section label
        for item in budget_sections:
            if not isinstance(item, dict):
                continue
            lbl = str(item.get("label", "")).strip().lower()
            if lbl == source_label:
                tw = item.get("target_words")
                if isinstance(tw, (int, float)) and int(tw) > 0:
                    return int(tw)

        return default_wc

    sections: list[dict[str, object]] = []
    for i, spec in enumerate(REQUIRED_SECTION_SPECS):
        src_label = str(spec.get("source_label", "verse"))
        energy = _energy_for_section(src_label, structure, i)
        default_arc = str(spec.get("emotional_arc", "reflective"))
        inferred_arc = _emotional_arc_from_energy(energy)
        word_count_raw = spec.get("word_count", 50)
        default_wc = (
            int(word_count_raw) if isinstance(word_count_raw, (int, float)) else 50
        )
        word_count = _word_count_from_budget(src_label, i, default_wc)

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
    reference_dna_raw = payload.get("reference_dna", {})
    reference_dna = reference_dna_raw if isinstance(reference_dna_raw, dict) else {}
    beat_budget_raw = reference_dna.get("lyric_beat_budget", [])
    beat_budget = beat_budget_raw if isinstance(beat_budget_raw, dict) else {}

    planned = plan_structure_grid("template-bootstrap", structure, beat_budget)
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
            llm_error = str(llm_result.get("error", ""))
            llm_detail = str(llm_result.get("detail", ""))
            merged_detail = llm_error
            if llm_detail:
                merged_detail = (
                    f"{llm_error}: {llm_detail}" if llm_error else llm_detail
                )
            return {
                "ok": False,
                "error": "llm_generation_failed",
                "error_detail": merged_detail,
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

    def _classify_openai_error(exc: Exception) -> tuple[str, str]:
        name = type(exc).__name__
        msg = str(exc)
        lowered = msg.lower()
        if (
            name == "AuthenticationError"
            or "401" in lowered
            or "unauthorized" in lowered
        ):
            return "llm_error_401", msg
        if name == "APITimeoutError" or "timeout" in lowered or "timed out" in lowered:
            return "llm_error_timeout", msg
        if name == "RateLimitError" or "rate limit" in lowered or "429" in lowered:
            return "llm_error_rate_limit", msg
        if name == "APIError":
            return "llm_api_error", msg
        return "llm_api_error", msg

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
                        if parsed.get("ok") is False and isinstance(
                            parsed.get("error"), str
                        ):
                            return {
                                "ok": False,
                                "error": str(parsed.get("error")),
                                "detail": str(parsed.get("detail", "")),
                                "lines": [],
                            }
                        lines = parsed.get("lines", [])
                        if isinstance(lines, list):
                            return {
                                "lines": [
                                    str(x) for x in lines if isinstance(x, str) and x
                                ]
                            }
            except Exception as exc:
                error_code, detail = _classify_openai_error(exc)
                return {
                    "ok": False,
                    "error": error_code,
                    "detail": detail,
                    "lines": [],
                }

        # Fallback path: Chat Completions API
        chat_api = getattr(client, "chat", None)
        completions_api = getattr(chat_api, "completions", None)
        chat_create_fn = getattr(completions_api, "create", None)
        if callable(chat_create_fn):
            try:
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
                            if parsed2.get("ok") is False and isinstance(
                                parsed2.get("error"), str
                            ):
                                return {
                                    "ok": False,
                                    "error": str(parsed2.get("error")),
                                    "detail": str(parsed2.get("detail", "")),
                                    "lines": [],
                                }
                            lines2 = parsed2.get("lines", [])
                            if isinstance(lines2, list):
                                return {
                                    "lines": [
                                        str(x)
                                        for x in lines2
                                        if isinstance(x, str) and x
                                    ]
                                }
            except Exception as exc:
                error_code, detail = _classify_openai_error(exc)
                return {
                    "ok": False,
                    "error": error_code,
                    "detail": detail,
                    "lines": [],
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


def _load_pop_grid(tag: str) -> list[int] | None:
    """Load a line-length grid from chinese_pop_grids.json for the given section tag."""
    import random

    grids_path = Path(__file__).parent.parent.parent.parent / "data" / "chinese_pop_grids.json"
    try:
        data = json.loads(grids_path.read_text(encoding="utf-8"))
        tag_map: dict[str, str] = data.get("tag_map", {})
        grids: dict[str, list[list[int]]] = data.get("grids", {})
        grid_key = tag_map.get(tag.strip().lower(), "")
        if not grid_key:
            # fallback by keyword
            tl = tag.strip().lower()
            if "chorus" in tl:
                grid_key = "chorus_hook"
            elif "bridge" in tl:
                grid_key = "bridge"
            elif "pre" in tl:
                grid_key = "prechorus"
            else:
                grid_key = "verse_reflective"
        options = grids.get(grid_key, [])
        if options:
            return random.choice(options)
    except Exception:
        pass
    return None


def _load_montage_nouns(n: int = 5) -> list[str]:
    """Sample n concrete nouns from visual_montage_nouns.json."""
    import random

    nouns_path = Path(__file__).parent.parent.parent.parent / "data" / "visual_montage_nouns.json"
    try:
        data = json.loads(nouns_path.read_text(encoding="utf-8"))
        categories: dict[str, list[str]] = data.get("categories", {})
        pool: list[str] = []
        for words in categories.values():
            pool.extend(words)
        if pool:
            return random.sample(pool, min(n, len(pool)))
    except Exception:
        pass
    return []


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
    tag_lower = tag.strip().lower()
    chorus_required = "chorus" in tag_lower
    is_verse = "verse" in tag_lower
    is_chorus = chorus_required

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

    # PROD-1: load rhythm grid — forces varied line lengths
    pop_grid = _load_pop_grid(tag)
    grid_str = str(pop_grid) if pop_grid else str(sentence_lengths)
    line_count = len(pop_grid) if pop_grid else max(3, min(6, word_count // 10))

    # PROD-2: section-specific writing rules
    if is_verse:
        montage_nouns = _load_montage_nouns(6)
        nouns_str = "、".join(montage_nouns) if montage_nouns else "地铁、便利店、手机屏、窗台、钥匙、外卖袋"
        section_rules = (
            "【主歌写法（Verse）】\n"
            f"  - 必须从以下具象名词中选取至少3个融入歌词: {nouns_str}\n"
            "  - 句子是观察性陈述，写行为和物件，不是直接抒情\n"
            "  - 禁止出现情绪形容词（失落/难过/释怀/心碎），只写看得见的动作和场景\n"
            "  - 语气口语化，像在自言自语\n"
        )
    elif is_chorus:
        section_rules = (
            "【副歌写法（Chorus）】\n"
            "  - 必须包含1句核心Hook，这句话是全曲最强记忆点，需在本段重复出现（允许轻微变体）\n"
            "  - 每行句尾最后一个字必须是开口音字，韵母含 a/ai/ao/an/ang，例如：花/来/跑/散/忘/开/找/站/烫\n"
            "  - 绝对禁止句尾以 了/啊/吗/呢/吧/啦 结尾\n"
            "  - 情绪是爆发与释放，不是叙述\n"
            "  - 句子比主歌更短、更有力、更易记\n"
        )
    else:
        section_rules = (
            "【过渡段写法】\n"
            "  - 字数必须出现明显变化，制造紧张或转折感\n"
            "  - 语气可以比主歌更急促或更克制\n"
        )

    prompt = {
        "prompt": (
            "你是中文流行歌词写作助手，专门为 AI 音乐引擎（Suno/MiniMax）生成可唱性强的歌词。\n"
            f"段落: {tag}\n"
            f"情绪弧线: {emotional_arc}\n"
            f"用户意图: {intent}\n"
            "\n"
            "【节奏律动约束 - 最高优先级】\n"
            f"  必须严格按照以下字数模板逐行输出，共 {line_count} 行，每行字数按顺序: {grid_str}\n"
            "  字数偏差不超过1字。绝对禁止相邻两行字数完全一致（排比句直接判失败）。\n"
            "  字数少的行（<=6字）是切分句，字数多的行（>=9字）是延伸句，两者必须交错出现。\n"
            "\n"
            + section_rules
            + "\n"
            f"停连节奏硬约束: {pause_rhythm}\n"
            f"副歌钩子: {chorus_hook}\n"
            f"本段是否必须复现副歌钩子: {'是' if chorus_required else '否'}\n"
            f"禁用词库: {lexical_ban}\n"
            "禁用句式: 你像X我像Y、如果...就好了、把抽象词当主语。\n"
            "禁用语义: 不允许空泛鸡汤、命运论、无场景抒情。\n"
            "所有行必须是具体场景，不得只写抽象情绪词。\n"
            f"语料参考(只读): {corpus_preview}\n"
            '输出JSON: {"lines": ["...", "..."]}'
        )
    }

    try:
        out = adapter_callable(prompt)
    except Exception as exc:
        msg = str(exc)
        lowered = msg.lower()
        if "timeout" in lowered or "timed out" in lowered:
            return {
                "ok": False,
                "lines": [],
                "error": "llm_error_timeout",
                "detail": msg,
            }
        if "401" in lowered or "unauthorized" in lowered:
            return {
                "ok": False,
                "lines": [],
                "error": "llm_error_401",
                "detail": msg,
            }
        return {"ok": False, "lines": [], "error": msg}

    if isinstance(out, dict):
        if out.get("ok") is False and isinstance(out.get("error"), str):
            return {
                "ok": False,
                "lines": [],
                "error": str(out.get("error")),
                "detail": str(out.get("detail", "")),
            }
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

    return {
        "ok": False,
        "lines": [],
        "error": "empty_or_invalid_llm_output",
        "detail": "adapter returned no usable lines",
    }


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


def derive_peak_positions_from_dna(
    reference_dna: dict[str, object],
    total_chars: int,
) -> list[int]:
    """Derive peak-note character positions from high-energy outliers."""
    if total_chars <= 0:
        return []

    curve_raw = reference_dna.get("energy_curve", [])
    curve = curve_raw if isinstance(curve_raw, list) else []
    values: list[float] = []
    for point in curve:
        if isinstance(point, dict):
            energy = point.get("energy")
            if isinstance(energy, (int, float)):
                values.append(float(energy))

    if not values:
        return []

    mean_val = sum(values) / len(values)
    variance = sum((x - mean_val) ** 2 for x in values) / len(values)
    std_val = variance**0.5
    threshold = mean_val + 1.5 * std_val

    n = len(values)
    out: list[int] = []
    for idx, val in enumerate(values):
        if val > threshold:
            mapped = int(round((idx / max(1, n - 1)) * max(0, total_chars - 1)))
            out.append(mapped)

    return sorted(set(x for x in out if 0 <= x < total_chars))


def derive_long_note_positions_from_dna(
    reference_dna: dict[str, object],
    total_chars: int,
) -> list[int]:
    """Derive long-note positions by selecting one minimum per 8-beat window."""
    if total_chars <= 0:
        return []

    curve_raw = reference_dna.get("energy_curve", [])
    curve = curve_raw if isinstance(curve_raw, list) else []
    values: list[float] = []
    for point in curve:
        if isinstance(point, dict):
            energy = point.get("energy")
            if isinstance(energy, (int, float)):
                values.append(float(energy))

    if len(values) < 1:
        return []

    n = len(values)
    out: list[int] = []

    beats_window = 8
    for start in range(0, n, beats_window):
        segment = values[start : start + beats_window]
        if not segment:
            continue
        local_min_idx = min(range(len(segment)), key=lambda i: segment[i])
        global_idx = start + local_min_idx
        mapped = int(round((global_idx / max(1, n - 1)) * max(0, total_chars - 1)))
        out.append(mapped)

    return sorted(set(x for x in out if 0 <= x < total_chars))


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


def _load_cliche_blacklist(path: Path | None = None) -> set[str]:
    """Load cliche blacklist from JSON file with safe fallback.

    Expected JSON shape: ["phrase1", "phrase2", ...]
    """
    target_path = path if isinstance(path, Path) else Path("data/cliche_blacklist.json")
    resolved = target_path.expanduser().resolve()

    if resolved.exists() and resolved.is_file():
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                loaded = {
                    str(x).strip()
                    for x in payload
                    if isinstance(x, str) and str(x).strip()
                }
                if loaded:
                    return loaded
        except (OSError, json.JSONDecodeError):
            logger.warning("failed to parse cliche blacklist json: %s", resolved)

    logger.warning(
        "cliche blacklist file unavailable, fallback to built-in set: %s", resolved
    )
    return set(CLICHE_BLACKLIST)


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


def check_line_length_constraints(
    sections: list[dict[str, object]],
    max_line_length: int,
    chorus_max_line_length: int,
) -> dict[str, object]:
    """Enforce hard line-length constraints for all generated lines."""
    violations: list[dict[str, object]] = []

    for section_idx, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        section_tag = str(section.get("tag", "")).strip().lower()
        is_chorus = section_tag in {"chorus", "final chorus"}
        section_limit = chorus_max_line_length if is_chorus else max_line_length

        lines_val = section.get("lines", [])
        lines = [str(x) for x in lines_val] if isinstance(lines_val, list) else []
        for line_idx, line in enumerate(lines):
            line_len = len(line)
            if line_len > section_limit:
                violations.append(
                    {
                        "section": section_idx,
                        "section_tag": section.get("tag", "Unknown"),
                        "line": line_idx,
                        "length": line_len,
                        "limit": section_limit,
                        "severity": "high",
                    }
                )

    return {
        "ok": True,
        "violations": violations,
        "pass": len(violations) == 0,
        "max_line_length": max_line_length,
        "chorus_max_line_length": chorus_max_line_length,
    }


def _shorten_line_to_limit(text: str, limit: int) -> str:
    """Best-effort deterministic shortening for overlong lines."""
    if len(text) <= limit:
        return text

    stripped = text.strip()
    for sep in ["，", "。", "！", "？", "；", "、", ",", ".", "!", "?", ";"]:
        if sep in stripped:
            chunks = [x.strip() for x in stripped.split(sep) if x.strip()]
            for chunk in chunks:
                if len(chunk) <= limit:
                    return chunk

    compact = stripped.replace(" ", "")
    if len(compact) <= limit:
        return compact

    return compact[:limit]


def _rewrite_line_to_limit_with_llm(
    adapter_callable: object,
    line: str,
    limit: int,
    section_tag: str,
    intent: str,
) -> str | None:
    """Ask LLM to rewrite a single overlong line under strict char limit."""
    if not callable(adapter_callable):
        return None

    prompt = {
        "prompt": (
            "你是中文流行歌词改写助手。"
            "把下面这句歌词改写成不超过给定字数的自然短句，保持原意与场景，不要截断残句。"
            '输出JSON: {"line": "..."}。\n'
            f"段落: {section_tag}\n"
            f"用户意图: {intent}\n"
            f"最大字数: {limit}\n"
            f"原句: {line}\n"
        )
    }

    try:
        out = adapter_callable(prompt)
    except Exception:
        return None

    candidate = None
    if isinstance(out, dict):
        line_val = out.get("line")
        if isinstance(line_val, str) and line_val.strip():
            candidate = line_val.strip()
        if candidate is None:
            lines_val = out.get("lines")
            if isinstance(lines_val, list) and lines_val:
                first = lines_val[0]
                if isinstance(first, str) and first.strip():
                    candidate = first.strip()
    elif isinstance(out, list) and out:
        first = out[0]
        if isinstance(first, str) and first.strip():
            candidate = first.strip()

    if candidate and len(candidate) <= limit:
        return candidate
    return None


def check_sentence_completeness(lyrics: list[str]) -> dict[str, object]:
    """Detect likely truncated/unfinished lyric lines.

    This is a heuristic quality gate to block obvious half-sentences,
    especially those produced by hard truncation.
    """
    if not lyrics:
        return {"ok": True, "violations": [], "pass": True}

    bad_suffixes = {
        "的",
        "着",
        "把",
        "被",
        "和",
        "跟",
        "与",
        "及",
        "就",
        "再",
        "还",
        "都",
        "又",
        "也",
        "在",
        "到",
        "向",
        "给",
        "对",
        "从",
        "把",
    }
    banned_end_bigrams = {
        "把钥匙",
        "我拎着",
        "点头说",
        "再锁好",
        "我把",
        "你把",
    }

    violations: list[dict[str, object]] = []
    for idx, line in enumerate(lyrics):
        text = str(line).strip()
        if not text:
            violations.append({"line": idx, "reason": "empty_line", "severity": "high"})
            continue

        if text[-1] in bad_suffixes:
            violations.append(
                {
                    "line": idx,
                    "reason": "bad_suffix",
                    "suffix": text[-1],
                    "severity": "high",
                }
            )

        for frag in banned_end_bigrams:
            if text.endswith(frag):
                violations.append(
                    {
                        "line": idx,
                        "reason": "truncated_phrase",
                        "phrase": frag,
                        "severity": "high",
                    }
                )
                break

    return {
        "ok": True,
        "violations": violations,
        "pass": len(violations) == 0,
    }


def apply_line_length_autofix(
    sections: list[dict[str, object]],
    max_line_length: int,
    chorus_max_line_length: int,
    adapter_callable: object,
    intent: str,
) -> tuple[list[dict[str, object]], int]:
    """Auto-fix overlong lines with deterministic shortening.

    Returns fixed sections and number of changed lines.
    """
    fixed: list[dict[str, object]] = []
    changed = 0

    for section in sections:
        if not isinstance(section, dict):
            continue
        tag = str(section.get("tag", "")).strip().lower()
        is_chorus = tag in {"chorus", "final chorus"}
        limit = chorus_max_line_length if is_chorus else max_line_length

        lines_val = section.get("lines", [])
        lines = [str(x) for x in lines_val] if isinstance(lines_val, list) else []
        new_lines: list[str] = []
        section_name = str(section.get("tag", "Unknown"))
        for line in lines:
            shortened = line
            if len(line) > limit:
                llm_rewritten = _rewrite_line_to_limit_with_llm(
                    adapter_callable=adapter_callable,
                    line=line,
                    limit=limit,
                    section_tag=section_name,
                    intent=intent,
                )
                if isinstance(llm_rewritten, str) and llm_rewritten:
                    shortened = llm_rewritten
                else:
                    # Do NOT hard-clip residual sentence fragments.
                    # Keep original overlong line and let quality_gate trigger rewrite/fail.
                    shortened = line
            if shortened != line:
                changed += 1
            new_lines.append(shortened)

        cloned = dict(section)
        cloned["lines"] = new_lines
        fixed.append(cloned)

    return fixed, changed


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
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        load_dotenv(override=False)
    except Exception:
        pass

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

    resolved_adapter = llm_adapter if callable(llm_adapter) else None
    if resolved_adapter is None:
        resolved_adapter = _build_openai_adapter(
            api_key=llm_api_key,
            base_url=llm_base_url,
            model_name=llm_model,
        )

    # Step 1: Plan structure grid
    structure_raw = (
        reference_dna.get("structure", []) if isinstance(reference_dna, dict) else []
    )
    structure: list[dict[str, object]] = (
        structure_raw if isinstance(structure_raw, list) else []
    )
    beat_budget_raw = (
        reference_dna.get("lyric_beat_budget", [])
        if isinstance(reference_dna, dict)
        else []
    )
    beat_budget = beat_budget_raw if isinstance(beat_budget_raw, dict) else {}

    grid_result = plan_structure_grid(intent, structure, beat_budget)
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
    completeness_result: dict[str, object] = {
        "ok": True,
        "violations": [],
        "pass": True,
    }
    has_line_length_limits = (
        "max_line_length" in payload or "chorus_max_line_length" in payload
    )
    max_line_length_raw = payload.get("max_line_length", 14)
    max_line_length = (
        int(max_line_length_raw)
        if isinstance(max_line_length_raw, (int, float))
        and int(max_line_length_raw) > 0
        else 14
    )
    chorus_max_line_length_raw = payload.get("chorus_max_line_length", 12)
    chorus_max_line_length = (
        int(chorus_max_line_length_raw)
        if isinstance(chorus_max_line_length_raw, (int, float))
        and int(chorus_max_line_length_raw) > 0
        else 12
    )
    line_length_result: dict[str, object] = {
        "ok": True,
        "violations": [],
        "pass": True,
        "max_line_length": max_line_length,
        "chorus_max_line_length": chorus_max_line_length,
    }
    line_length_autofix = bool(payload.get("line_length_autofix", True))

    negative_lexicon_raw = payload.get("negative_lexicon", [])
    negative_lexicon: set[str] = set(DEFAULT_ANTI_LEXICON)
    if isinstance(negative_lexicon_raw, list):
        for item in negative_lexicon_raw:
            if isinstance(item, str) and item.strip():
                negative_lexicon.add(item.strip())

    reference_constraints = _build_reference_hard_constraints(reference_dna)

    cliche_blacklist_path_raw = payload.get("cliche_blacklist_path")
    cliche_blacklist_path: Path | None = None
    if isinstance(cliche_blacklist_path_raw, (str, Path)):
        cliche_blacklist_path = Path(cliche_blacklist_path_raw)
    cliche_blacklist = _load_cliche_blacklist(cliche_blacklist_path)

    draft_iterations = 0
    vowel_fix_count = 0
    cliche_fix_count = 0
    line_length_fix_count = 0
    line_length_autofix_count = 0

    for attempt in range(max_rewrite_iterations + 1):
        draft_iterations += 1

        draft_result = generate_draft(
            grid,
            current_intent,
            use_llm=use_llm,
            llm_adapter=resolved_adapter,
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
        if has_line_length_limits and line_length_autofix:
            draft_sections, changed = apply_line_length_autofix(
                draft_sections,
                max_line_length=max_line_length,
                chorus_max_line_length=chorus_max_line_length,
                adapter_callable=resolved_adapter,
                intent=current_intent,
            )
            line_length_autofix_count += changed
        all_lines = []
        for section in draft_sections:
            if not isinstance(section, dict):
                continue
            lines_val = section.get("lines", [])
            if isinstance(lines_val, list):
                all_lines.extend(str(line) for line in lines_val)

        total_chars = sum(len(line) for line in all_lines)
        effective_peak_positions = (
            peak_positions
            if peak_positions
            else derive_peak_positions_from_dna(reference_dna, total_chars)
        )
        effective_long_note_positions = (
            long_note_positions
            if long_note_positions
            else derive_long_note_positions_from_dna(reference_dna, total_chars)
        )

        vowel_result = check_vowel_openness(all_lines, effective_peak_positions)
        tone_result = check_tone_collision(all_lines, effective_long_note_positions)
        cliche_result = check_anti_cliche(all_lines, blacklist=cliche_blacklist)
        anti_lexicon_result = check_anti_lexicon(all_lines, negative_lexicon)
        completeness_result = check_sentence_completeness(all_lines)
        if has_line_length_limits:
            line_length_result = check_line_length_constraints(
                draft_sections,
                max_line_length=max_line_length,
                chorus_max_line_length=chorus_max_line_length,
            )
        else:
            line_length_result = {
                "ok": True,
                "violations": [],
                "pass": True,
                "max_line_length": max_line_length,
                "chorus_max_line_length": chorus_max_line_length,
            }

        needs_vowel_fix = (not bool(vowel_result.get("pass", True))) or (
            not bool(tone_result.get("pass", True))
        )
        needs_cliche_fix = not bool(cliche_result.get("pass", True))
        needs_anti_lexicon_fix = not bool(anti_lexicon_result.get("pass", True))
        needs_completeness_fix = not bool(completeness_result.get("pass", True))
        needs_line_length_fix = has_line_length_limits and not bool(
            line_length_result.get("pass", True)
        )

        # PROD-4: check groove within loop so monotone output triggers rewrite
        import statistics as _stats_loop

        _monotone_now: list[str] = []
        for _s in draft_sections:
            if not isinstance(_s, dict):
                continue
            _sl = [
                str(l.get("text", "") if isinstance(l, dict) else l)
                for l in _s.get("lines", [])
            ]
            _ll = [len(t) for t in _sl if t]
            if len(_ll) >= 3 and _stats_loop.variance(_ll) < 1.0:
                _monotone_now.append(str(_s.get("tag", "")))
        needs_groove_fix = len(_monotone_now) > 0

        if not (
            needs_vowel_fix
            or needs_cliche_fix
            or needs_anti_lexicon_fix
            or needs_completeness_fix
            or needs_line_length_fix
            or needs_groove_fix
        ):
            break
        if attempt >= max_rewrite_iterations:
            break

        if needs_vowel_fix:
            vowel_fix_count += 1
        if needs_cliche_fix:
            cliche_fix_count += 1
        if needs_anti_lexicon_fix:
            cliche_fix_count += 1
        if needs_line_length_fix:
            line_length_fix_count += 1

        current_intent = (
            intent
            + "\n[重写约束] 保留核心叙事与情绪。"
            + "\n- 避免烂梗与抽象空话，优先具象场景。"
            + "\n- 长音位置尽量使用更顺口字。"
            + "\n- 避免重复句式与重复关键词。"
            + "\n- 句子必须完整，禁止半截句、禁止以虚词或介词收尾。"
            + (
                "\n- 严格短句：普通段落每行不超过"
                + str(max_line_length)
                + "字；副歌每行不超过"
                + str(chorus_max_line_length)
                + "字。"
                if has_line_length_limits
                else ""
            )
            + "\n- 禁用词："
            + "、".join(sorted(negative_lexicon))
            + (
                "\n- 上次产出字数过于均一（排比句），本次必须严格按字数模板生成长短句，"
                "相邻行字数差必须 >=2，整段方差必须 >4。"
                if needs_groove_fix
                else ""
            )
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

    completeness_violations = completeness_result.get("violations", [])
    if isinstance(completeness_violations, list):
        for v in completeness_violations:
            if isinstance(v, dict):
                reason = str(v.get("reason", "incomplete_line"))
                warnings.append(
                    {
                        "line_index": v.get("line", 0),
                        "type": "sentence_completeness",
                        "severity": "high",
                        "human": f"句子不完整: {reason}",
                    }
                )

    length_violations = line_length_result.get("violations", [])
    if isinstance(length_violations, list):
        for v in length_violations:
            if isinstance(v, dict):
                warnings.append(
                    {
                        "line_index": v.get("line", 0),
                        "type": "line_length",
                        "severity": "high",
                        "human": (
                            f"{v.get('section_tag', 'Unknown')} 第{int(v.get('line', 0)) + 1}行"
                            f"长度{v.get('length', 0)}超限{v.get('limit', 0)}"
                        ),
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
                "line_length_fix": line_length_fix_count,
                "line_length_autofix": line_length_autofix_count,
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
            "line_length_violation_count": len(length_violations)
            if isinstance(length_violations, list)
            else 0,
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

    # PROD-4: sentence length variance gate — reject monotone/排比 output
    import statistics as _stats

    monotone_sections: list[str] = []
    for _sec in draft_sections:
        if not isinstance(_sec, dict):
            continue
        _sec_lines = [
            str(l.get("text", "") if isinstance(l, dict) else l)
            for l in _sec.get("lines", [])
        ]
        _lens = [len(t) for t in _sec_lines if t]
        if len(_lens) >= 3 and _stats.variance(_lens) < 1.0:
            monotone_sections.append(str(_sec.get("tag", "")))

    groove_gate_pass = len(monotone_sections) == 0

    quality_gate = {
        "pass": bool(vowel_result.get("pass", True))
        and bool(tone_result.get("pass", True))
        and bool(cliche_result.get("pass", True))
        and bool(anti_lexicon_result.get("pass", True))
        and bool(completeness_result.get("pass", True))
        and bool(line_length_result.get("pass", True))
        and groove_gate_pass,
        "anti_lexicon_hits": anti_lexicon_result.get("hits", []),
        "sentence_completeness_violations": completeness_violations,
        "line_length_violations": length_violations,
        "max_line_length": max_line_length,
        "chorus_max_line_length": chorus_max_line_length,
        "autofix_mode": "llm_rewrite"
        if callable(resolved_adapter)
        else "deterministic_clip",
        "groove_gate_pass": groove_gate_pass,
        "monotone_sections": monotone_sections,
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
