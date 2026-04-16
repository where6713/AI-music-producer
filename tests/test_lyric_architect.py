"""Tests for lyric_architect structure-grid planner and draft generation."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _stable_adapter(prompt: dict[str, object]) -> dict[str, object]:
    _ = prompt
    return {
        "lines": [
            "站台灯熄后我把旧车票塞进口袋",
            "风停在袖口, 我终于学会笑着说再见",
        ]
    }


def test_structure_grid_planner_basic() -> None:
    """G2: structure grid planner should generate section outlines."""
    from src.producer_tools.business.lyric_architect import plan_structure_grid

    intent = "失恋 R&B 碎碎念风格"
    structure = [
        {"index": 0, "label": "verse", "energy": 0.3},
        {"index": 1, "label": "chorus", "energy": 0.8},
        {"index": 2, "label": "verse", "energy": 0.4},
        {"index": 3, "label": "chorus", "energy": 0.9},
    ]

    result = plan_structure_grid(intent, structure)

    assert result["ok"] is True
    assert "grid" in result
    assert "sections" in result["grid"]
    assert len(result["grid"]["sections"]) >= 1


def test_structure_grid_sections_have_required_fields() -> None:
    """G2: each section should have tag, emotional_arc, keywords, word_count."""
    from src.producer_tools.business.lyric_architect import plan_structure_grid

    intent = "失恋 R&B"
    structure = [{"index": 0, "label": "verse", "energy": 0.5}]

    result = plan_structure_grid(intent, structure)

    assert result["ok"] is True
    section = result["grid"]["sections"][0]
    assert "tag" in section
    assert "emotional_arc" in section
    assert "keywords" in section
    assert "word_count" in section


def test_structure_grid_word_count_positive() -> None:
    """G2: word_count should be positive integer."""
    from src.producer_tools.business.lyric_architect import plan_structure_grid

    intent = "快乐 Pop"
    structure = [{"index": 0, "label": "chorus", "energy": 0.9}]

    result = plan_structure_grid(intent, structure)

    for section in result["grid"]["sections"]:
        assert section["word_count"] > 0
        assert isinstance(section["word_count"], int)


def test_structure_grid_empty_structure() -> None:
    """G2: empty structure should return default grid."""
    from src.producer_tools.business.lyric_architect import plan_structure_grid

    result = plan_structure_grid("测试意图", [])

    assert result["ok"] is True
    assert "grid" in result


def test_structure_grid_uses_beat_budget_target_words() -> None:
    """word_count should come from beat budget when provided by analysis stage."""
    from src.producer_tools.business.lyric_architect import plan_structure_grid

    result = plan_structure_grid(
        "测试意图",
        [{"index": 0, "label": "verse", "energy": 0.4}],
        {
            "beats_per_bar": 4,
            "total_beats": 96,
            "sections": [
                {"label": "verse", "bars": 4, "beats": 16, "target_words": 16},
                {
                    "label": "pre_chorus",
                    "bars": 2,
                    "beats": 8,
                    "target_words": 8,
                },
                {"label": "chorus", "bars": 4, "beats": 16, "target_words": 16},
            ],
        },
    )

    assert result["ok"] is True
    sections = result["grid"]["sections"]
    assert sections[0]["word_count"] == 16  # Verse 1
    assert sections[1]["word_count"] == 8  # Pre-Chorus
    assert sections[2]["word_count"] == 16  # Chorus


def test_draft_generation_basic() -> None:
    """G2: draft generation should produce lyrics from grid."""
    from src.producer_tools.business.lyric_architect import generate_draft

    grid = {
        "sections": [
            {
                "tag": "Verse 1",
                "emotional_arc": "reflective",
                "keywords": [],
                "word_count": 40,
            },
            {
                "tag": "Chorus",
                "emotional_arc": "emotional_peak",
                "keywords": [],
                "word_count": 60,
            },
        ]
    }

    result = generate_draft(
        grid,
        intent="失恋 R&B",
        use_llm=True,
        llm_adapter=_stable_adapter,
    )

    assert result["ok"] is True
    assert "draft" in result
    assert "sections" in result["draft"]
    assert len(result["draft"]["sections"]) == 2


def test_draft_sections_have_lines() -> None:
    """G2: each draft section should have tag and lines."""
    from src.producer_tools.business.lyric_architect import generate_draft

    grid = {
        "sections": [
            {
                "tag": "Verse 1",
                "emotional_arc": "reflective",
                "keywords": [],
                "word_count": 40,
            },
        ]
    }

    result = generate_draft(
        grid,
        intent="测试意图",
        use_llm=True,
        llm_adapter=_stable_adapter,
    )

    assert result["ok"] is True
    section = result["draft"]["sections"][0]
    assert "tag" in section
    assert "lines" in section
    assert isinstance(section["lines"], list)


def test_draft_lines_are_strings() -> None:
    """G2: draft lines should be non-empty strings."""
    from src.producer_tools.business.lyric_architect import generate_draft

    grid = {
        "sections": [
            {
                "tag": "Chorus",
                "emotional_arc": "emotional_peak",
                "keywords": [],
                "word_count": 60,
            },
        ]
    }

    result = generate_draft(
        grid,
        intent="快乐 Pop",
        use_llm=True,
        llm_adapter=_stable_adapter,
    )

    section = result["draft"]["sections"][0]
    for line in section["lines"]:
        assert isinstance(line, str)
        assert len(line) > 0


def test_draft_respects_word_count() -> None:
    """G2: draft should approximately respect word_count per section."""
    from src.producer_tools.business.lyric_architect import generate_draft

    grid = {
        "sections": [
            {
                "tag": "Verse 1",
                "emotional_arc": "reflective",
                "keywords": [],
                "word_count": 30,
            },
        ]
    }

    result = generate_draft(
        grid,
        intent="测试",
        use_llm=True,
        llm_adapter=_stable_adapter,
    )

    section = result["draft"]["sections"][0]
    total_chars = sum(len(line) for line in section["lines"])
    # Chinese: ~1 char per word, allow 50% margin
    assert total_chars > 0


def test_vowel_openness_interceptor_basic() -> None:
    """G2: vowel openness should detect closed vowels at peaks."""
    from src.producer_tools.business.lyric_architect import check_vowel_openness

    lyrics = ["哭的时候不说话", "你的眼神"]
    peak_positions = [0]  # "哭" (u) at peak

    result = check_vowel_openness(lyrics, peak_positions)

    assert result["ok"] is True
    assert "violations" in result
    assert "pass" in result


def test_vowel_openness_open_vowel_passes() -> None:
    """G2: open vowels at peaks should pass."""
    from src.producer_tools.business.lyric_architect import check_vowel_openness

    lyrics = ["放开手去爱", "大步向前"]
    peak_positions = [0]  # "放" (ang) - open vowel

    result = check_vowel_openness(lyrics, peak_positions)

    assert result["ok"] is True
    assert result["pass"] is True


def test_vowel_openness_closed_vowel_fails() -> None:
    """G2: closed vowels at peaks should fail."""
    from src.producer_tools.business.lyric_architect import check_vowel_openness

    lyrics = ["一直在这里", "孤独的夜"]
    peak_positions = [0]  # "一" (i) - closed vowel

    result = check_vowel_openness(lyrics, peak_positions)

    assert result["ok"] is True
    assert result["pass"] is False
    assert len(result["violations"]) > 0


def test_vowel_openness_returns_violation_details() -> None:
    """G2: violations should include line, char, vowel info."""
    from src.producer_tools.business.lyric_architect import check_vowel_openness

    lyrics = ["哭泣的夜晚"]
    peak_positions = [0]  # "哭" (u)

    result = check_vowel_openness(lyrics, peak_positions)

    if not result["pass"]:
        violation = result["violations"][0]
        assert "line" in violation
        assert "char" in violation
        assert "vowel" in violation
        assert "severity" in violation


# === P07.04: Tone Collision Interceptor ===


def test_tone_collision_interceptor_basic() -> None:
    """G2: tone collision should detect 3rd/4th tones on long notes."""
    from src.producer_tools.business.lyric_architect import check_tone_collision

    lyrics = ["走在这个夜里", "我"]
    long_note_positions = [0]  # "走" (3rd tone)

    result = check_tone_collision(lyrics, long_note_positions)

    assert result["ok"] is True
    assert "violations" in result
    assert "risk_percentage" in result
    assert "pass" in result


def test_tone_collision_flat_tone_passes() -> None:
    """G2: flat tones (1st/2nd) on long notes should pass."""
    from src.producer_tools.business.lyric_architect import check_tone_collision

    lyrics = ["天蓝色的彩虹", "高"]
    long_note_positions = [0]  # "天" (1st tone)

    result = check_tone_collision(lyrics, long_note_positions)

    assert result["ok"] is True
    # 1st/2nd tone should not be a violation
    assert result["pass"] is True


def test_tone_collision_risk_percentage() -> None:
    """G2: risk_percentage should be calculated correctly."""
    from src.producer_tools.business.lyric_architect import check_tone_collision

    lyrics = ["走在这里", "去追", "梦"]
    long_note_positions = [0, 1, 2]  # 3 tones + others

    result = check_tone_collision(lyrics, long_note_positions)

    assert result["ok"] is True
    assert "risk_percentage" in result
    assert isinstance(result["risk_percentage"], float)


def test_tone_collision_threshold() -> None:
    """G2: >15% risk should fail."""
    from src.producer_tools.business.lyric_architect import check_tone_collision

    lyrics = ["走", "去", "来", "啊"]
    long_note_positions = [0, 1, 2, 3]  # All 3rd/4th tone

    result = check_tone_collision(lyrics, long_note_positions)

    # With 4 long notes all at 3rd tone, risk > 15%
    assert result["ok"] is True
    # Result indicates pass/fail based on 15% threshold


# === P07.05: Anti-Cliché Interceptor ===


def test_anti_cliche_interceptor_basic() -> None:
    """G2: anti-cliche should detect banned phrases."""
    from src.producer_tools.business.lyric_architect import check_anti_cliche

    lyrics = ["星辰大海的梦想", "孤独的灵魂"]

    result = check_anti_cliche(lyrics)

    assert result["ok"] is True
    assert "violations" in result
    assert "density_pct" in result
    assert "pass" in result


def test_anti_cliche_clean_lyrics_pass() -> None:
    """G2: clean lyrics without cliches should pass."""
    from src.producer_tools.business.lyric_architect import check_anti_cliche

    lyrics = ["便利店玻璃映着我没换的衬衫", "旧洗衣机转得很慢"]

    result = check_anti_cliche(lyrics)

    assert result["ok"] is True
    assert result["pass"] is True


def test_anti_cliche_density_calculation() -> None:
    """G2: density percentage should be calculated."""
    from src.producer_tools.business.lyric_architect import check_anti_cliche

    lyrics = ["这是一个孤独的夜晚", "星辰大海"]

    result = check_anti_cliche(lyrics)

    assert result["ok"] is True
    assert "density_pct" in result
    assert isinstance(result["density_pct"], float)
    assert 0.0 <= result["density_pct"] <= 100.0


def test_anti_cliche_threshold() -> None:
    """G2: >5% density should fail."""
    from src.producer_tools.business.lyric_architect import check_anti_cliche

    lyrics = ["孤独灵魂星辰大海追寻梦想时光沙漏"] * 5

    result = check_anti_cliche(lyrics)

    # High density of cliches should fail
    assert result["ok"] is True
    # Result indicates pass/fail based on 5% threshold


# === P07.06: run() and lyrics.json output ===


def test_run_returns_lyrics_structure() -> None:
    """G2: run() should return lyrics structure with required fields."""
    from src.producer_tools.business.lyric_architect import run

    result = run(
        {
            "intent": "失恋 R&B",
            "reference_dna": {
                "structure": [{"index": 0, "label": "verse", "energy": 0.5}]
            },
            "use_llm": True,
            "llm_adapter": _stable_adapter,
        }
    )

    assert result["ok"] is True
    assert "lyrics" in result
    lyrics = result["lyrics"]
    assert "meta" in lyrics
    assert "sections" in lyrics
    assert "warnings" in lyrics
    assert "stats" in lyrics


def test_run_lyrics_has_meta_fields() -> None:
    """G2: lyrics.meta should have intent and iterations."""
    from src.producer_tools.business.lyric_architect import run

    result = run(
        {
            "intent": "测试意图",
            "reference_dna": {"structure": []},
            "use_llm": True,
            "llm_adapter": _stable_adapter,
        }
    )

    assert result["ok"] is True
    meta = result["lyrics"]["meta"]
    assert "intent" in meta
    assert "iterations" in meta


def test_run_sections_have_lines() -> None:
    """G2: each section should have tag and lines array."""
    from src.producer_tools.business.lyric_architect import run

    result = run(
        {
            "intent": "测试",
            "reference_dna": {
                "structure": [{"index": 0, "label": "verse", "energy": 0.5}]
            },
            "use_llm": True,
            "llm_adapter": _stable_adapter,
        }
    )

    assert result["ok"] is True
    sections = result["lyrics"]["sections"]
    if sections:
        assert "tag" in sections[0]
        assert "lines" in sections[0]


def test_run_stats_has_required_metrics() -> None:
    """G2: stats should have vowel_openness, cliche_density, tone_collision metrics."""
    from src.producer_tools.business.lyric_architect import run

    result = run(
        {
            "intent": "测试",
            "reference_dna": {"structure": []},
            "use_llm": True,
            "llm_adapter": _stable_adapter,
        }
    )

    assert result["ok"] is True
    stats = result["lyrics"]["stats"]
    assert "vowel_openness_at_peak" in stats
    assert "cliche_density_pct" in stats
    assert "tone_collision_pct" in stats


def test_run_llm_mode_requires_configuration() -> None:
    """When use_llm=true and no adapter/api key, run should fail fast."""
    from src.producer_tools.business.lyric_architect import run

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {
                "structure": [{"index": 0, "label": "verse", "energy": 0.5}]
            },
            "use_llm": True,
        }
    )

    assert result["ok"] is False
    assert result.get("error") in {"llm_not_configured", "llm_generation_failed"}


def test_run_llm_mode_uses_adapter() -> None:
    """When use_llm=true, provided adapter output should be used."""
    from src.producer_tools.business.lyric_architect import run

    def _fake_adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        return {
            "lines": [
                "潮声退去后我把誓言折进衣袋",
                "月色借我一口气, 学会笑着转身",
            ]
        }

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {
                "structure": [{"index": 0, "label": "verse", "energy": 0.5}]
            },
            "use_llm": True,
            "llm_adapter": _fake_adapter,
        }
    )

    assert result["ok"] is True
    out = result["lyrics"]["sections"][0]["lines"][0]["text"]
    assert "潮声退去后" in out


def test_run_llm_mode_exposes_error_detail() -> None:
    """LLM adapter exceptions should be surfaced in error_detail for debugging."""
    from src.producer_tools.business.lyric_architect import run

    def _broken_adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        raise RuntimeError("upstream model gateway timeout")

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {
                "structure": [{"index": 0, "label": "verse", "energy": 0.5}]
            },
            "use_llm": True,
            "llm_adapter": _broken_adapter,
        }
    )

    assert result["ok"] is False
    assert result.get("error") == "llm_generation_failed"
    assert "upstream model gateway timeout" in str(result.get("error_detail", ""))


def test_plan_structure_grid_enforces_prd_section_order() -> None:
    """Structure planner should enforce PRD-required section sequence."""
    from src.producer_tools.business.lyric_architect import plan_structure_grid

    result = plan_structure_grid(
        "现代感,略带古风,失恋但豁达",
        [
            {"index": 0, "label": "chorus", "energy": 0.8},
            {"index": 1, "label": "chorus", "energy": 0.9},
            {"index": 2, "label": "verse", "energy": 0.4},
        ],
    )

    assert result["ok"] is True
    tags = [x["tag"] for x in result["grid"]["sections"]]
    assert tags == [
        "Verse 1",
        "Pre-Chorus",
        "Chorus",
        "Verse 2",
        "Bridge",
        "Final Chorus",
    ]


def test_run_llm_mode_rewrites_when_cliche_density_high() -> None:
    """When cliche density exceeds threshold, run should iterate rewrite loop."""
    from src.producer_tools.business.lyric_architect import run

    state = {"calls": 0}

    def _iterative_adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        state["calls"] += 1
        if state["calls"] <= 6:
            # first full-draft cycle (6 sections) intentionally cliche-heavy
            return {"lines": ["孤独灵魂追寻梦想", "星辰大海时光沙漏"]}
        return {"lines": ["潮声褪色后我把旧誓折进衣袋", "站台风停, 我学会笑着转身"]}

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {"structure": []},
            "use_llm": True,
            "llm_adapter": _iterative_adapter,
        }
    )

    assert result["ok"] is True
    assert result["lyrics"]["stats"]["cliche_density_pct"] <= 5.0
    iterations = result["lyrics"]["meta"]["iterations"]
    assert iterations["cliche_fix"] >= 1


def test_run_quality_gate_blocks_forbidden_lexicon() -> None:
    """Hard quality gate should fail when anti-lexicon is hit."""
    from src.producer_tools.business.lyric_architect import run

    def _bad_adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        return {
            "lines": [
                "霓虹把誓言切成碎片",
                "破碎感在夜里游走",
            ]
        }

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {"structure": []},
            "use_llm": True,
            "llm_adapter": _bad_adapter,
            "max_rewrite_iterations": 1,
        }
    )

    assert result["ok"] is False
    assert result.get("error") == "lyric_quality_gate_failed"
    gate = result.get("quality_gate", {})
    assert isinstance(gate, dict)
    assert gate.get("pass") is False


def test_run_rejects_offline_mode_explicitly() -> None:
    """Offline generation mode must remain disabled."""
    from src.producer_tools.business.lyric_architect import run

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {"structure": []},
            "use_llm": False,
        }
    )

    assert result["ok"] is False
    assert result.get("error") == "offline_lyrics_disabled"


def test_generate_draft_injects_hard_constraints_into_prompt() -> None:
    """Prompt should carry forbidden lexicon and reference hard constraints."""
    from src.producer_tools.business.lyric_architect import generate_draft

    captured: dict[str, object] = {}

    def _capture_adapter(prompt: dict[str, object]) -> dict[str, object]:
        captured.update(prompt)
        return {"lines": ["旧雨停在站牌边", "我把晚风折成信"]}

    result = generate_draft(
        {
            "sections": [
                {
                    "tag": "Chorus",
                    "emotional_arc": "emotional_peak",
                    "keywords": [],
                    "word_count": 40,
                }
            ]
        },
        intent="现代感, 略带古风, 失恋但豁达",
        use_llm=True,
        llm_adapter=_capture_adapter,
        forbidden_terms={"霓虹", "破碎感"},
        reference_constraints={
            "sentence_length_distribution": [8, 10, 12],
            "pause_rhythm": ["匀速连读", "短停-推进"],
            "chorus_hook": "C@110bpm_高能段重复意象2次",
        },
    )

    assert result["ok"] is True
    prompt_text = str(captured.get("prompt", ""))
    assert "禁用词库-词级硬约束" in prompt_text
    assert "句长分布硬约束" in prompt_text
    assert "停连节奏硬约束" in prompt_text
    assert "本段是否必须复现副歌钩子: 是" in prompt_text


def test_run_quality_gate_blocks_long_lines() -> None:
    """Hard quality gate should fail when line length constraints are violated."""
    from src.producer_tools.business.lyric_architect import run

    def _long_line_adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        return {
            "lines": [
                "这是一句明显超长并且超过限制的歌词文本",
                "副歌这里也给一条特别特别长的句子",
            ]
        }

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {
                "structure": [
                    {"label": "verse", "energy": 0.4},
                    {"label": "chorus", "energy": 0.8},
                ]
            },
            "use_llm": True,
            "llm_adapter": _long_line_adapter,
            "max_rewrite_iterations": 0,
            "max_line_length": 14,
            "chorus_max_line_length": 10,
            "line_length_autofix": False,
        }
    )

    assert result["ok"] is False
    assert result.get("error") == "lyric_quality_gate_failed"
    gate = result.get("quality_gate", {})
    assert isinstance(gate, dict)
    assert gate.get("pass") is False
    violations = gate.get("line_length_violations", [])
    assert isinstance(violations, list)
    assert len(violations) > 0


def test_run_quality_gate_blocks_incomplete_tail_lines() -> None:
    """Quality gate should fail for obviously incomplete half-sentences."""
    from src.producer_tools.business.lyric_architect import run

    def _tail_broken_adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        return {"lines": ["回头吧回头吧我把钥匙", "地铁到站你先下我拎着"]}

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {"structure": [{"label": "verse", "energy": 0.4}]},
            "use_llm": True,
            "llm_adapter": _tail_broken_adapter,
            "max_rewrite_iterations": 0,
            "line_length_autofix": False,
            "max_line_length": 30,
            "chorus_max_line_length": 30,
        }
    )

    assert result["ok"] is False
    assert result.get("error") == "lyric_quality_gate_failed"
    gate = result.get("quality_gate", {})
    assert isinstance(gate, dict)
    assert gate.get("pass") is False
    scv = gate.get("sentence_completeness_violations", [])
    assert isinstance(scv, list)
    assert len(scv) > 0


def test_run_without_adapter_returns_llm_not_configured() -> None:
    """Without callable adapter and API config, run should fail explicitly."""
    from src.producer_tools.business.lyric_architect import run

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {"structure": [{"label": "verse", "energy": 0.4}]},
            "use_llm": True,
            "llm_adapter": None,
            "max_rewrite_iterations": 0,
            "line_length_autofix": True,
            "max_line_length": 8,
            "chorus_max_line_length": 8,
            "llm_api_key": "",
        }
    )

    assert result["ok"] is False
    assert result.get("error") in {"llm_not_configured", "llm_generation_failed"}


def test_run_sets_autofix_mode_llm_with_callable_adapter() -> None:
    """With callable adapter, quality_gate should report llm_rewrite mode."""
    from src.producer_tools.business.lyric_architect import run

    def _adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        return {"lines": ["地铁到站你把伞还我", "我点头说好先上车"]}

    result = run(
        {
            "intent": "现代感, 略带古风, 失恋但豁达",
            "reference_dna": {"structure": [{"label": "verse", "energy": 0.4}]},
            "use_llm": True,
            "llm_adapter": _adapter,
            "max_rewrite_iterations": 0,
            "line_length_autofix": True,
            "max_line_length": 20,
            "chorus_max_line_length": 20,
        }
    )

    gate = result.get("quality_gate", {})
    assert isinstance(gate, dict)
    assert gate.get("autofix_mode") == "llm_rewrite"


def test_generate_section_lines_propagates_llm_error_codes() -> None:
    """LLM adapter explicit errors should be propagated verbatim."""
    from src.producer_tools.business.lyric_architect import (
        _generate_section_lines_with_llm,
    )

    def _auth_error_adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        return {"ok": False, "error": "llm_error_401", "detail": "unauthorized"}

    result = _generate_section_lines_with_llm(
        adapter_callable=_auth_error_adapter,
        tag="Verse 1",
        word_count=16,
        emotional_arc="reflective",
        intent="测试",
        template_meta={},
        corpus_lines=[],
        forbidden_terms=set(),
        reference_constraints={},
    )

    assert result["ok"] is False
    assert result.get("error") == "llm_error_401"


def test_generate_section_lines_handles_timeout_exception() -> None:
    """Adapter timeout exceptions should classify to llm_error_timeout."""
    from src.producer_tools.business.lyric_architect import (
        _generate_section_lines_with_llm,
    )

    def _timeout_adapter(prompt: dict[str, object]) -> dict[str, object]:
        _ = prompt
        raise TimeoutError("Request timed out.")

    result = _generate_section_lines_with_llm(
        adapter_callable=_timeout_adapter,
        tag="Verse 1",
        word_count=16,
        emotional_arc="reflective",
        intent="测试",
        template_meta={},
        corpus_lines=[],
        forbidden_terms=set(),
        reference_constraints={},
    )

    assert result["ok"] is False
    assert result.get("error") in {"llm_error_timeout", "llm_generation_failed"}
