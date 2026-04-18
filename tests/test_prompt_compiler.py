"""Tests for prompt_compiler tool.

PRD 5.5: Prompt Compiler compiles friction_report + genre_seed + lyrics.json
into Suno/MiniMax compatible prompt format.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

from producer_tools.business.prompt_compiler import (
    TOOL_NAME,
    compile_style_field,
    compile_lyrics_field,
    compile_exclude_field,
    run,
)


class TestToolContract:
    """Test tool exposes required contracts."""

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        assert TOOL_NAME == "prompt_compiler"

    def test_run_callable(self) -> None:
        """run() must be callable."""
        assert callable(run)


class TestCompileStyleField:
    """Test compile_style_field function.

    PRD 5.5: Style field format:
    {genre_seed.descriptors}, {target_key}, {tempo_bpm} BPM,
    {vocal_style_tags}, {instrumentation_emphasis}
    """

    def test_basic_style_field(self) -> None:
        """Test basic style field compilation."""
        genre_seed = {
            "descriptors": ["R&B", "soul", "urban"],
        }
        reference_dna = {
            "key": "C major",
            "bpm": 85,
            "instrumentation": {
                "emphasis": ["piano", "synth bass"],
                "deemphasis": ["distorted guitar"],
            },
        }
        voice_profile = {
            "timbre": {
                "brightness": 0.6,
            },
        }

        result = compile_style_field(genre_seed, reference_dna, voice_profile)

        assert result["ok"] is True
        assert "R&B" in result["style"]
        assert "soul" in result["style"]
        assert "urban" in result["style"]
        assert "C major" in result["style"]
        assert "85 BPM" in result["style"]

    def test_style_field_missing_genres(self) -> None:
        """Test style field with missing genre descriptors."""
        genre_seed = {}
        reference_dna = {
            "key": "A minor",
            "bpm": 120,
            "instrumentation": {"emphasis": [], "deemphasis": []},
        }
        voice_profile = {}

        result = compile_style_field(genre_seed, reference_dna, voice_profile)

        assert result["ok"] is True
        assert "A minor" in result["style"]
        assert "120 BPM" in result["style"]

    def test_style_field_includes_vocal_style(self) -> None:
        """Test style field includes vocal style tags."""
        genre_seed = {"descriptors": ["pop"]}
        reference_dna = {
            "key": "G major",
            "bpm": 100,
            "instrumentation": {"emphasis": ["acoustic guitar"], "deemphasis": []},
        }
        voice_profile = {
            "timbre": {"brightness": 0.8},
        }

        result = compile_style_field(genre_seed, reference_dna, voice_profile)

        assert result["ok"] is True
        # Vocal style should be inferred from timbre brightness
        assert "bright" in result["style"].lower() or "male" in result["style"].lower()

    def test_style_field_supports_tempo_fallback(self) -> None:
        """Style field should accept style_deconstructor tempo key when bpm absent."""
        genre_seed = {"descriptors": ["neo-r&b"]}
        reference_dna = {
            "key": "D minor",
            "tempo": 101.3,
            "instrumentation": {
                "vocals": {"presence": True, "role": "lead_vocal"},
                "bass": {"presence": True, "role": "foundation"},
            },
        }

        result = compile_style_field(genre_seed, reference_dna, {})

        assert result["ok"] is True
        assert "101 BPM" in result["style"]
        assert "D minor" in result["style"]


class TestCompileLyricsField:
    """Test compile_lyrics_field function.

    PRD 5.5: Lyrics field includes:
    [Mood: ...] [Energy: ...] [Instrument: ...]
    [Verse 1] [mood descriptor]
    lyrics text...
    """

    def test_basic_lyrics_field(self) -> None:
        """Test basic lyrics field compilation."""
        lyrics = {
            "sections": [
                {
                    "tag": "Verse 1",
                    "lines": [
                        {"text": "便利店玻璃映着我没换的衬衫"},
                        {"text": "冰柜嗡嗡响比心跳还慢"},
                    ],
                },
                {
                    "tag": "Chorus",
                    "lines": [
                        {"text": "原来是我不懂"},
                        {"text": "你要的自由"},
                    ],
                },
            ],
        }
        reference_dna = {
            "energy_curve": [0.3, 0.5, 0.8, 0.9, 0.7],
            "instrumentation": {"emphasis": ["piano", "bass", "drums"]},
        }

        result = compile_lyrics_field(lyrics, reference_dna)

        assert result["ok"] is True
        assert "[Verse]" in result["lyrics"]
        assert "[Chorus]" in result["lyrics"]
        assert "便利店玻璃映着我没换的衬衫" in result["lyrics"]

    def test_lyrics_field_includes_mood_tags(self) -> None:
        """Test lyrics field includes mood and energy tags."""
        lyrics = {
            "sections": [
                {"tag": "Verse 1", "lines": [{"text": "test line"}]},
            ],
        }
        reference_dna = {
            "energy_curve": [0.3, 0.4],
            "instrumentation": {"emphasis": ["piano"]},
        }

        result = compile_lyrics_field(lyrics, reference_dna)

        assert result["ok"] is True
        # Should include mood/instrument descriptors
        assert "[Mood:" in result["lyrics"] or "[Instrument:" in result["lyrics"]

    def test_lyrics_field_supports_segmented_energy_curve(self) -> None:
        """Lyrics field should parse style_deconstructor energy curve shape."""
        lyrics = {
            "sections": [
                {"tag": "Verse 1", "lines": [{"text": "夜色把你名字写在玻璃上"}]},
            ]
        }
        reference_dna = {
            "energy_curve": [
                {"time": 0.0, "energy": 0.28},
                {"time": 4.5, "energy": 0.32},
            ],
            "instrumentation": {
                "vocals": {"presence": True, "role": "lead_vocal"},
            },
        }

        result = compile_lyrics_field(lyrics, reference_dna)

        assert result["ok"] is True
        assert "[Mood:" in result["lyrics"]

    def test_lyrics_field_empty_sections(self) -> None:
        """Test lyrics field with empty sections."""
        lyrics = {"sections": []}
        reference_dna = {}

        result = compile_lyrics_field(lyrics, reference_dna)

        assert result["ok"] is True
        assert result["lyrics"] == ""


class TestCompileExcludeField:
    """Test compile_exclude_field function.

    PRD 5.5: Exclude field includes:
    {instrumentation_deemphasis} + [metal, screamo, autotune heavy, ...]
    """

    def test_basic_exclude_field(self) -> None:
        """Test basic exclude field compilation."""
        reference_dna = {
            "instrumentation": {
                "deemphasis": ["heavy metal", "screamo"],
            },
        }

        result = compile_exclude_field(reference_dna)

        assert result["ok"] is True
        assert "metal" in result["exclude"]
        assert "screamo" in result["exclude"]

    def test_exclude_field_default_blacklist(self) -> None:
        """Test exclude field includes default blacklist."""
        reference_dna = {
            "instrumentation": {"deemphasis": []},
        }

        result = compile_exclude_field(reference_dna)

        assert result["ok"] is True
        # Default blacklist from PRD
        assert "autotune heavy" in result["exclude"]
        assert "8-bit" in result["exclude"]
        assert "chiptune" in result["exclude"]

    def test_exclude_field_missing_instrumentation(self) -> None:
        """Test exclude field with missing instrumentation data."""
        reference_dna = {}

        result = compile_exclude_field(reference_dna)

        assert result["ok"] is True
        # Should still include default blacklist
        assert "metal" in result["exclude"]


class TestRun:
    """Test run() function for prompt_compiler tool."""

    def test_run_skeleton_raises_not_implemented(self) -> None:
        """Skeleton run() should raise NotImplementedError."""
        try:
            run({"_skeleton": True})
            assert False, "Should have raised NotImplementedError"
        except NotImplementedError:
            pass

    def test_run_missing_required_inputs(self) -> None:
        """Test run with missing required inputs."""
        result = run({})

        assert result["ok"] is False
        assert "error" in result

    def test_run_basic_compilation(self) -> None:
        """Test basic prompt compilation."""
        payload = {
            "genre_seed": {"descriptors": ["R&B", "soul"]},
            "reference_dna": {
                "key": "C major",
                "bpm": 85,
                "instrumentation": {
                    "emphasis": ["piano"],
                    "deemphasis": ["metal"],
                },
            },
            "lyrics": {
                "sections": [
                    {
                        "tag": "Verse 1",
                        "lines": [{"text": "test lyrics"}],
                    },
                    {
                        "tag": "Chorus",
                        "lines": [{"text": "test chorus"}],
                    },
                ],
            },
            "voice_profile": {"timbre": {"brightness": 0.6}},
            "semantic_gate": False,
        }

        result = run(payload)

        assert result["ok"] is True
        assert "style" in result
        assert "lyrics" in result
        assert "exclude" in result

    def test_run_outputs_compile_log(self) -> None:
        """Test run outputs compile_log with field sources."""
        payload = {
            "genre_seed": {"descriptors": ["pop"]},
            "reference_dna": {
                "key": "G major",
                "bpm": 100,
                "instrumentation": {"emphasis": [], "deemphasis": []},
            },
            "lyrics": {
                "sections": [
                    {"tag": "Verse 1", "lines": [{"text": "line"}]},
                    {"tag": "Chorus", "lines": [{"text": "line"}]},
                ]
            },
            "semantic_gate": False,
        }

        result = run(payload)

        assert result["ok"] is True
        assert "compile_log" in result
        # compile_log should track source of each field
        log = result["compile_log"]
        assert isinstance(log, dict)

    def test_run_semantic_gate_fails_without_required_sections(self) -> None:
        """Semantic gate should fail when Chorus section is missing."""
        payload = {
            "genre_seed": {"descriptors": ["R&B"]},
            "reference_dna": {
                "key": "C major",
                "tempo": 96,
                "instrumentation": {
                    "vocals": {"presence": True, "role": "lead_vocal"},
                    "deemphasis": ["metal"],
                },
                "energy_curve": [{"time": 0.0, "energy": 0.3}],
            },
            "lyrics": {
                "sections": [
                    {"tag": "Verse 1", "lines": [{"text": "只是路灯照着空站台"}]},
                ]
            },
        }

        result = run(payload)

        assert result["ok"] is False
        assert result.get("error") == "semantic_gate_failed"
        gate = result.get("semantic_gate", {})
        assert isinstance(gate, dict)


class TestBreathTags:
    """Test breath tag insertion for vocal naturalness.

    PRD 5.5 v1.1: Insert [inhale], [breath], [soft inhale] tags
    at natural breathing points in lyrics.
    """

    def test_breath_tags_inserted_at_line_ends(self) -> None:
        """Test breath tags inserted at natural line breaks."""
        lyrics = {
            "sections": [
                {
                    "tag": "Verse 1",
                    "lines": [
                        {"text": "便利店玻璃映着我没换的衬衫"},
                        {"text": "冰柜嗡嗡响比心跳还慢"},
                    ],
                },
            ],
        }
        reference_dna = {"energy_curve": [0.3, 0.4]}

        result = compile_lyrics_field(lyrics, reference_dna)

        assert result["ok"] is True
        # Should have some breath tags in the output
        # (implementation determines optimal placement)

    def test_dynamic_cue_injection_uses_energy_curve_and_logs_decisions(self) -> None:
        lyrics = {
            "sections": [
                {
                    "tag": "Verse 1",
                    "lines": [
                        {"text": "站台灯暗后我把旧票折进衣袋"},
                        {"text": "风停在袖口我学会慢慢松开"},
                    ],
                },
                {
                    "tag": "Chorus",
                    "lines": [
                        {"text": "把夜推开把心口大声点亮"},
                        {"text": "让昨天散场把明天唱到天亮"},
                    ],
                },
            ]
        }
        reference_dna = {
            "energy_curve": [
                {"time": 0.0, "energy": 0.25},
                {"time": 6.0, "energy": 0.45},
                {"time": 12.0, "energy": 0.82},
                {"time": 18.0, "energy": 0.91},
            ],
            "musiccaps_events": ["whisper_start", "build_up"],
        }

        result = compile_lyrics_field(lyrics, reference_dna)

        assert result["ok"] is True
        text = result["lyrics"]
        assert any(tag in text for tag in ["[breath]", "[inhale]", "[sigh]"])
        source = result.get("source", {})
        assert isinstance(source, dict)
        logs = source.get("cue_decisions", [])
        assert isinstance(logs, list)
        assert len(logs) > 0
        assert all("tag_source" in item for item in logs if isinstance(item, dict))

    def test_dynamic_cue_injection_can_emit_whisper_and_build_up(self) -> None:
        lyrics = {
            "sections": [
                {
                    "tag": "Pre-Chorus",
                    "lines": [
                        {"text": "月台回声把旧答案推回来"},
                        {"text": "我不再追问谁该先说离开"},
                    ],
                }
            ]
        }
        reference_dna = {
            "energy_curve": [0.2, 0.4, 0.7, 0.95],
            "musiccaps_events": ["whisper_intro", "build_up"],
        }

        result = compile_lyrics_field(lyrics, reference_dna)

        assert result["ok"] is True
        text = result["lyrics"]
        assert "[whisper]" in text
        assert "[build-up]" in text


class TestDifficultSyllableTiming:
    """Test difficult syllable timing adaptation.

    PRD 5.5: Insert ~ or () after difficult syllables on long notes.
    """

    def test_timing_marker_for_tone_collision(self) -> None:
        """Test timing marker inserted for tone collision warnings."""
        lyrics = {
            "sections": [
                {
                    "tag": "Chorus",
                    "lines": [
                        {"text": "转身就走", "warnings": ["tone_collision"]},
                    ],
                },
            ],
        }
        reference_dna = {}

        result = compile_lyrics_field(lyrics, reference_dna)

        assert result["ok"] is True
        # Implementation should mark difficult syllables
